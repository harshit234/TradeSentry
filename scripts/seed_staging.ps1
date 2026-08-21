param(
  [string]$Profile = "tradesentry-dev",
  [string]$Region = "ap-south-1"
)
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true
$cluster = (terraform -chdir=infra/aws output -raw ecs_cluster_name).Trim()
$service = (terraform -chdir=infra/aws output -raw ecs_api_service).Trim()
$description = aws ecs describe-services --profile $Profile --region $Region `
  --cluster $cluster --services $service | ConvertFrom-Json
$network = $description.services[0].networkConfiguration.awsvpcConfiguration
$taskDefinition = $description.services[0].taskDefinition
$subnets = ($network.subnets -join ',')
$groups = ($network.securityGroups -join ',')
$overrides = '{"containerOverrides":[{"name":"api","command":["python","scripts/seed_demo.py"]}]}'
$task = aws ecs run-task --profile $Profile --region $Region --cluster $cluster `
  --launch-type FARGATE --task-definition $taskDefinition `
  --network-configuration "awsvpcConfiguration={subnets=[$subnets],securityGroups=[$groups],assignPublicIp=ENABLED}" `
  --overrides $overrides | ConvertFrom-Json
if (-not $task.tasks) { throw "Demo seed task did not start" }
$taskArn = $task.tasks[0].taskArn
aws ecs wait tasks-stopped --profile $Profile --region $Region --cluster $cluster --tasks $taskArn
$finished = aws ecs describe-tasks --profile $Profile --region $Region `
  --cluster $cluster --tasks $taskArn | ConvertFrom-Json
$container = $finished.tasks[0].containers | Where-Object name -eq "api"
if ($container.exitCode -ne 0) { throw "Demo seed failed: $($container.reason)" }
Write-Output "Four demo scenarios reset successfully"
