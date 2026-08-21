data "aws_caller_identity" "current" {}

resource "aws_kms_key" "documents" {
  description             = "TradeSentry document envelope encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true
}

resource "aws_s3_bucket" "documents" { bucket_prefix = "tradesentry-documents-" }
resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id
  versioning_configuration { status = "Enabled" }
}
resource "aws_s3_bucket_public_access_block" "documents" {
  bucket = aws_s3_bucket.documents.id
  block_public_acls = true
  block_public_policy = true
  ignore_public_acls = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id
  rule { apply_server_side_encryption_by_default { kms_master_key_id = aws_kms_key.documents.arn; sse_algorithm = "aws:kms" } }
}

resource "aws_ecr_repository" "api" { name = "tradesentry-api"; image_scanning_configuration { scan_on_push = true } }
resource "aws_ecr_repository" "web" { name = "tradesentry-web"; image_scanning_configuration { scan_on_push = true } }
resource "aws_ecs_cluster" "main" { name = "tradesentry-${var.environment}" }
resource "aws_ecs_task_definition" "api" {
  family = "tradesentry-api"; network_mode = "awsvpc"; requires_compatibilities = ["FARGATE"]
  cpu = 256; memory = 512; task_role_arn = aws_iam_role.ecs_task.arn
  container_definitions = jsonencode([{ name = "api", image = "${aws_ecr_repository.api.repository_url}:latest", essential = true, portMappings = [{ containerPort = 8000, protocol = "tcp" }], logConfiguration = { logDriver = "awslogs", options = { "awslogs-group" = aws_cloudwatch_log_group.api.name, "awslogs-region" = var.aws_region, "awslogs-stream-prefix" = "ecs" } } }])
}
resource "aws_ecs_task_definition" "web" {
  family = "tradesentry-web"; network_mode = "awsvpc"; requires_compatibilities = ["FARGATE"]
  cpu = 256; memory = 512; task_role_arn = aws_iam_role.ecs_task.arn
  container_definitions = jsonencode([{ name = "web", image = "${aws_ecr_repository.web.repository_url}:latest", essential = true, portMappings = [{ containerPort = 3000, protocol = "tcp" }], logConfiguration = { logDriver = "awslogs", options = { "awslogs-group" = aws_cloudwatch_log_group.web.name, "awslogs-region" = var.aws_region, "awslogs-stream-prefix" = "ecs" } } }])
}
resource "aws_cloudwatch_log_group" "api" { name = "/ecs/tradesentry/api"; retention_in_days = 30 }
resource "aws_cloudwatch_log_group" "web" { name = "/ecs/tradesentry/web"; retention_in_days = 30 }

resource "aws_security_group" "data" { name = "tradesentry-data"; vpc_id = var.vpc_id }
resource "aws_db_subnet_group" "main" { name = "tradesentry"; subnet_ids = var.private_subnet_ids }
resource "aws_db_instance" "postgres" {
  identifier = "tradesentry-${var.environment}"
  engine = "postgres"; engine_version = "16"; instance_class = "db.t4g.micro"
  allocated_storage = 20; storage_encrypted = true; kms_key_id = aws_kms_key.documents.arn
  db_name = "tradesentry"; username = "tradesentry_admin"; manage_master_user_password = true
  db_subnet_group_name = aws_db_subnet_group.main.name; vpc_security_group_ids = [aws_security_group.data.id]
  publicly_accessible = false; backup_retention_period = 7; skip_final_snapshot = true
}

resource "aws_elasticache_subnet_group" "main" { name = "tradesentry"; subnet_ids = var.private_subnet_ids }
resource "aws_elasticache_replication_group" "redis" {
  replication_group_id = "tradesentry-${var.environment}"; description = "TradeSentry session cache"
  node_type = "cache.t4g.micro"; num_cache_clusters = 1; port = 6379
  subnet_group_name = aws_elasticache_subnet_group.main.name; security_group_ids = [aws_security_group.data.id]
  transit_encryption_enabled = true; at_rest_encryption_enabled = true
}

resource "aws_secretsmanager_secret" "application" { name = "/tradesentry/${var.environment}/application"; kms_key_id = aws_kms_key.documents.arn }

resource "aws_iam_role" "ecs_task" {
  name = "tradesentry-${var.environment}-ecs-task"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Service = "ecs-tasks.amazonaws.com" }, Action = "sts:AssumeRole" }] })
}
resource "aws_iam_role_policy" "ecs_task" {
  role = aws_iam_role.ecs_task.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"], Resource = "${aws_s3_bucket.documents.arn}/*" },
    { Effect = "Allow", Action = ["textract:AnalyzeDocument", "textract:StartDocumentAnalysis", "textract:GetDocumentAnalysis"], Resource = "*" },
    { Effect = "Allow", Action = ["bedrock:InvokeModel"], Resource = "arn:aws:bedrock:${var.aws_region}::foundation-model/*" },
    { Effect = "Allow", Action = ["kms:Decrypt", "kms:GenerateDataKey"], Resource = aws_kms_key.documents.arn },
    { Effect = "Allow", Action = ["secretsmanager:GetSecretValue"], Resource = aws_secretsmanager_secret.application.arn }
  ] })
}
