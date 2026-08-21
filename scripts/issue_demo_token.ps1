param(
  [string]$Profile = "tradesentry-dev",
  [string]$Region = "ap-south-1",
  [ValidateSet("IBU-A", "IBU-B", "IBU-C")][string]$IbuId = "IBU-A"
)
$ErrorActionPreference = "Stop"
$credentials = aws configure export-credentials --profile $Profile --format process | ConvertFrom-Json
$env:AWS_ACCESS_KEY_ID = $credentials.AccessKeyId
$env:AWS_SECRET_ACCESS_KEY = $credentials.SecretAccessKey
$env:AWS_SESSION_TOKEN = $credentials.SessionToken
$env:AWS_REGION = $Region
$secret = terraform -chdir=infra/aws output -raw application_secret_arn
& .venv/Scripts/python.exe scripts/issue_demo_token.py --region $Region `
  --secret-id $secret --ibu-id $IbuId
