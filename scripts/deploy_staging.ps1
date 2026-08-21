param(
  [string]$Profile = "tradesentry-dev",
  [string]$Region = "ap-south-1"
)
$ErrorActionPreference = "Stop"
foreach ($command in @("aws", "docker", "terraform")) {
  if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
    throw "$command is required for staging deployment"
  }
}
$gitSha = (git rev-parse --short=12 HEAD).Trim()
$credentials = aws configure export-credentials --profile $Profile --format process | ConvertFrom-Json
$env:AWS_ACCESS_KEY_ID = $credentials.AccessKeyId
$env:AWS_SECRET_ACCESS_KEY = $credentials.SecretAccessKey
$env:AWS_SESSION_TOKEN = $credentials.SessionToken
$env:AWS_REGION = $Region
terraform -chdir=infra/aws init -input=false
terraform -chdir=infra/aws apply -auto-approve -input=false `
  -var "aws_region=$Region" `
  -var "image_tag=$gitSha" -var "service_desired_count=0"

$apiRepository = (terraform -chdir=infra/aws output -raw api_repository_url).Trim()
$webRepository = (terraform -chdir=infra/aws output -raw web_repository_url).Trim()
$registry = $apiRepository.Substring(0, $apiRepository.LastIndexOf('/'))
aws ecr get-login-password --profile $Profile --region $Region |
  docker login --username AWS --password-stdin $registry

docker build -f apps/api/Dockerfile -t "${apiRepository}:$gitSha" -t "${apiRepository}:latest" .
docker build -f apps/web/Dockerfile --build-arg NEXT_PUBLIC_API_URL= `
  -t "${webRepository}:$gitSha" -t "${webRepository}:latest" .
docker push "${apiRepository}:$gitSha"
docker push "${apiRepository}:latest"
docker push "${webRepository}:$gitSha"
docker push "${webRepository}:latest"

$python = if (Test-Path ".venv/Scripts/python.exe") { ".venv/Scripts/python.exe" } else { "python" }
& $python scripts/configure_staging_secret.py `
  --region $Region `
  --application-secret-arn (terraform -chdir=infra/aws output -raw application_secret_arn) `
  --rds-master-secret-arn (terraform -chdir=infra/aws output -raw rds_master_secret_arn) `
  --rds-endpoint (terraform -chdir=infra/aws output -raw rds_endpoint) `
  --redis-endpoint (terraform -chdir=infra/aws output -raw redis_endpoint)

terraform -chdir=infra/aws apply -auto-approve -input=false `
  -var "aws_region=$Region" `
  -var "image_tag=$gitSha" -var "service_desired_count=1"
$cluster = (terraform -chdir=infra/aws output -raw ecs_cluster_name).Trim()
$apiService = (terraform -chdir=infra/aws output -raw ecs_api_service).Trim()
$webService = (terraform -chdir=infra/aws output -raw ecs_web_service).Trim()
aws ecs wait services-stable --profile $Profile --region $Region `
  --cluster $cluster --services $apiService $webService
& scripts/health_check_staging.ps1 -Profile $Profile -Region $Region
