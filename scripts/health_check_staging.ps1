param(
  [string]$Profile = "tradesentry-dev",
  [string]$Region = "ap-south-1"
)
$ErrorActionPreference = "Stop"
$stagingUrl = terraform -chdir=infra/aws output -raw staging_url
$health = Invoke-RestMethod -Uri "$stagingUrl/health" -TimeoutSec 20
$required = @("db", "redis", "s3", "textract", "dynamodb")
if ($health.status -ne "ok") { throw "Staging health is $($health.status)" }
foreach ($component in $required) {
  if ($health.$component -ne "ok") { throw "$component is $($health.$component)" }
}
$health | ConvertTo-Json -Depth 5
