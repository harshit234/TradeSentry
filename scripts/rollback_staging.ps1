param(
  [string]$Profile = "tradesentry-dev",
  [string]$Region = "ap-south-1"
)
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true
$cluster = (terraform -chdir=infra/aws output -raw ecs_cluster_name).Trim()
foreach ($service in @("tradesentry-api", "tradesentry-web")) {
  $family = $service
  $definitions = aws ecs list-task-definitions --profile $Profile --region $Region `
    --family-prefix $family --sort DESC --status ACTIVE | ConvertFrom-Json
  if ($definitions.taskDefinitionArns.Count -lt 2) {
    throw "No prior active task definition exists for $family"
  }
  $previous = $definitions.taskDefinitionArns[1]
  aws ecs update-service --profile $Profile --region $Region --cluster $cluster `
    --service $service --task-definition $previous --force-new-deployment | Out-Null
  Write-Output "$service rolling back to $previous"
}
aws ecs wait services-stable --profile $Profile --region $Region --cluster $cluster `
  --services tradesentry-api tradesentry-web
& scripts/health_check_staging.ps1 -Profile $Profile -Region $Region
