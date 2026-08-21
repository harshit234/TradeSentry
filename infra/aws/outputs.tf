output "document_bucket" { value = aws_s3_bucket.documents.id }
output "api_repository_url" { value = aws_ecr_repository.api.repository_url }
output "web_repository_url" { value = aws_ecr_repository.web.repository_url }
output "ecs_cluster_name" { value = aws_ecs_cluster.main.name }
output "cross_ibu_registry_table" { value = aws_dynamodb_table.trade_finance_registry.name }
