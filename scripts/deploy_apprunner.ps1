# TradeSentry Frontend Deployment to AWS App Runner (PowerShell)
# Usage: .\scripts\deploy_apprunner.ps1 -Region us-east-1

param (
    [string]$Region = "us-east-1",
    [string]$ServiceName = "tradesentry-web",
    [string]$RepoName = "tradesentry-web"
)

$ErrorActionPreference = "Continue"
$PSNativeCommandUseErrorActionPreference = $false

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host " TradeSentry Frontend Deployment (AWS App Runner)" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# 1. Check AWS identity
Write-Host "`n[1/6] Checking AWS Caller Identity..." -ForegroundColor Yellow
$callerJson = aws sts get-caller-identity --output json 2>$null | ConvertFrom-Json
if (-not $callerJson -or -not $callerJson.Account) {
    Write-Error "Failed to get AWS caller identity. Please configure AWS credentials with 'aws configure'."
    exit 1
}
$accountId = $callerJson.Account
Write-Host "Authenticated as AWS Account: $accountId (Region: $Region)" -ForegroundColor Green

$ecrUri = "$accountId.dkr.ecr.$Region.amazonaws.com/$RepoName"

# 2. Ensure ECR Repository exists
Write-Host "`n[2/6] Verifying ECR Repository '$RepoName'..." -ForegroundColor Yellow
$repoCheck = aws ecr describe-repositories --repository-names $RepoName --region $Region 2>$null
if (-not $repoCheck) {
    Write-Host "Creating ECR repository '$RepoName'..." -ForegroundColor Cyan
    aws ecr create-repository --repository-name $RepoName --region $Region --image-scanning-configuration scanOnPush=true | Out-Null
}
Write-Host "ECR repository ready at: $ecrUri" -ForegroundColor Green

# 3. Authenticate Docker & Build/Push Image
Write-Host "`n[3/6] Authenticating Docker & Building Container..." -ForegroundColor Yellow
aws ecr get-login-password --region $Region | docker login --username AWS --password-stdin "$accountId.dkr.ecr.$Region.amazonaws.com"

Write-Host "Building Docker image (Linux/AMD64)..." -ForegroundColor Cyan
docker build --provenance=false --platform linux/amd64 -f apps/web/Dockerfile -t "${RepoName}:latest" .

Write-Host "Pushing Docker image to ECR..." -ForegroundColor Cyan
docker tag "${RepoName}:latest" "${ecrUri}:latest"
docker push "${ecrUri}:latest"
Write-Host "Image successfully pushed: ${ecrUri}:latest" -ForegroundColor Green

# 4. Create / Verify IAM Roles
Write-Host "`n[4/6] Setting up App Runner IAM Roles..." -ForegroundColor Yellow

$tempDir = Join-Path $env:TEMP "tradesentry_iam"
if (-not (Test-Path $tempDir)) { New-Item -ItemType Directory -Path $tempDir | Out-Null }

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

# ECR Access Role
$ecrTrustPolicy = @'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Service": "build.apprunner.amazonaws.com" },
      "Action": "sts:AssumeRole"
    }
  ]
}
'@
$ecrTrustFile = Join-Path $tempDir "apprunner-ecr-trust.json"
[System.IO.File]::WriteAllText($ecrTrustFile, $ecrTrustPolicy, $utf8NoBom)

$ecrRoleCheck = aws iam get-role --role-name AppRunnerECRAccessRole 2>$null
if (-not $ecrRoleCheck) {
    Write-Host "Creating AppRunnerECRAccessRole..." -ForegroundColor Cyan
    aws iam create-role --role-name AppRunnerECRAccessRole --assume-role-policy-document "file://$ecrTrustFile" | Out-Null
    aws iam attach-role-policy --role-name AppRunnerECRAccessRole --policy-arn "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess" | Out-Null
}
$ecrRoleArn = (aws iam get-role --role-name AppRunnerECRAccessRole --query "Role.Arn" --output text 2>$null).Trim()

# Instance Role for Bedrock
$instanceTrustPolicy = @'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Service": "tasks.apprunner.amazonaws.com" },
      "Action": "sts:AssumeRole"
    }
  ]
}
'@
$instanceTrustFile = Join-Path $tempDir "apprunner-instance-trust.json"
[System.IO.File]::WriteAllText($instanceTrustFile, $instanceTrustPolicy, $utf8NoBom)

$instanceRoleCheck = aws iam get-role --role-name AppRunnerTradeSentryInstanceRole 2>$null
if (-not $instanceRoleCheck) {
    Write-Host "Creating AppRunnerTradeSentryInstanceRole..." -ForegroundColor Cyan
    aws iam create-role --role-name AppRunnerTradeSentryInstanceRole --assume-role-policy-document "file://$instanceTrustFile" | Out-Null
}

$bedrockPolicy = @'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "*"
    }
  ]
}
'@
$bedrockPolicyFile = Join-Path $tempDir "bedrock-policy.json"
[System.IO.File]::WriteAllText($bedrockPolicyFile, $bedrockPolicy, $utf8NoBom)
aws iam put-role-policy --role-name AppRunnerTradeSentryInstanceRole --policy-name AppRunnerBedrockAccess --policy-document "file://$bedrockPolicyFile" | Out-Null

$instanceRoleArn = (aws iam get-role --role-name AppRunnerTradeSentryInstanceRole --query "Role.Arn" --output text 2>$null).Trim()
Write-Host "IAM Roles configured:`n  ECR Access: $ecrRoleArn`n  Instance Role: $instanceRoleArn" -ForegroundColor Green

# 5. Create or Update App Runner Service
Write-Host "`n[5/6] Deploying AWS App Runner Service..." -ForegroundColor Yellow

$serviceCheck = aws apprunner list-services --region $Region --output json | ConvertFrom-Json
$existingService = $serviceCheck.ServiceSummaryList | Where-Object { $_.ServiceName -eq $ServiceName }

if ($existingService -and $existingService.Status -eq "CREATE_FAILED") {
    Write-Host "Previous service creation failed. Deleting failed service $($existingService.ServiceArn)..." -ForegroundColor Yellow
    aws apprunner delete-service --service-arn $existingService.ServiceArn --region $Region | Out-Null
    Start-Sleep -Seconds 10
    $existingService = $null
}

if ($existingService) {
    $serviceArn = $existingService.ServiceArn
    if ($existingService.Status -eq "RUNNING") {
        Write-Host "Existing running service found ($serviceArn). Triggering deployment update..." -ForegroundColor Cyan
        aws apprunner start-deployment --service-arn $serviceArn --region $Region | Out-Null
    } else {
        Write-Host "Service already exists ($serviceArn) with status '$($existingService.Status)'." -ForegroundColor Cyan
        Write-Host "Auto-deployment is actively rolling out the new image." -ForegroundColor Cyan
    }
} else {
    Write-Host "Creating new App Runner service '$ServiceName'..." -ForegroundColor Cyan
    
    $imageIdentifier = "${ecrUri}:latest"
    $sourceConfig = @"
{
  "AuthenticationConfiguration": {
    "AccessRoleArn": "$ecrRoleArn"
  },
  "AutoDeploymentsEnabled": true,
  "ImageRepository": {
    "ImageIdentifier": "$imageIdentifier",
    "ImageRepositoryType": "ECR",
    "ImageConfiguration": {
      "Port": "3000",
      "RuntimeEnvironmentVariables": {
        "NODE_ENV": "production",
        "AWS_REGION": "$Region",
        "BEDROCK_MODEL_ID": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "PORT": "3000",
        "HOSTNAME": "0.0.0.0"
      }
    }
  }
}
"@
    $sourceConfigFile = Join-Path $tempDir "source-config.json"
    [System.IO.File]::WriteAllText($sourceConfigFile, $sourceConfig, $utf8NoBom)

    $instanceConfig = @"
{
  "Cpu": "1 vCPU",
  "Memory": "2 GB",
  "InstanceRoleArn": "$instanceRoleArn"
}
"@
    $instanceConfigFile = Join-Path $tempDir "instance-config.json"
    [System.IO.File]::WriteAllText($instanceConfigFile, $instanceConfig, $utf8NoBom)

    $createOutput = aws apprunner create-service `
        --service-name $ServiceName `
        --source-configuration "file://$sourceConfigFile" `
        --instance-configuration "file://$instanceConfigFile" `
        --region $Region `
        --output json | ConvertFrom-Json

    $serviceArn = $createOutput.Service.ServiceArn
}

# 6. Monitor Status
Write-Host "`n[6/6] Checking Deployment Status..." -ForegroundColor Yellow
$serviceDetails = aws apprunner describe-service --service-arn $serviceArn --region $Region --output json | ConvertFrom-Json
$serviceUrl = "https://" + $serviceDetails.Service.ServiceUrl
$status = $serviceDetails.Service.Status

Write-Host "`n=========================================" -ForegroundColor Cyan
Write-Host " Service Name   : $ServiceName" -ForegroundColor White
Write-Host " Service Status : $status" -ForegroundColor White
Write-Host " Service URL    : $serviceUrl" -ForegroundColor Green
Write-Host " Service ARN    : $serviceArn" -ForegroundColor Gray
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Note: App Runner provisioning takes ~3-5 minutes on initial creation." -ForegroundColor Yellow
