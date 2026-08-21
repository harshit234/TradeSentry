data "aws_caller_identity" "current" {}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

locals {
  name       = "tradesentry-${var.environment}"
  vpc_id     = coalesce(var.vpc_id, data.aws_vpc.default.id)
  subnet_ids = length(var.subnet_ids) > 0 ? var.subnet_ids : data.aws_subnets.default.ids
  vpc_cidr   = coalesce(var.vpc_cidr, data.aws_vpc.default.cidr_block)
  registry_gsi_arns = [
    "${aws_dynamodb_table.trade_finance_registry.arn}/index/gsi_bl_number",
    "${aws_dynamodb_table.trade_finance_registry.arn}/index/gsi_vessel_date",
    "${aws_dynamodb_table.trade_finance_registry.arn}/index/gsi_exporter",
  ]
}

data "aws_iam_policy_document" "kms" {
  statement {
    sid       = "EnableAccountIAM"
    effect    = "Allow"
    actions   = ["kms:*"]
    resources = ["*"]
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }
  }
  statement {
    sid    = "AllowCloudWatchLogs"
    effect = "Allow"
    actions = [
      "kms:Encrypt", "kms:Decrypt", "kms:ReEncrypt*", "kms:GenerateDataKey*", "kms:DescribeKey"
    ]
    resources = ["*"]
    principals {
      type        = "Service"
      identifiers = ["logs.${var.aws_region}.amazonaws.com"]
    }
    condition {
      test     = "ArnLike"
      variable = "kms:EncryptionContext:aws:logs:arn"
      values   = ["arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/ecs/tradesentry/*"]
    }
  }
}

resource "aws_kms_key" "documents" {
  description             = "TradeSentry document and data envelope encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  policy                  = data.aws_iam_policy_document.kms.json
}

resource "aws_kms_alias" "documents" {
  name          = "alias/${local.name}-data"
  target_key_id = aws_kms_key.documents.key_id
}

# S3: private, versioned, BucketOwnerEnforced, and KMS-only writes.
resource "aws_s3_bucket" "documents" { bucket_prefix = "tradesentry-documents-" }

resource "aws_s3_bucket_ownership_controls" "documents" {
  bucket = aws_s3_bucket.documents.id
  rule { object_ownership = "BucketOwnerEnforced" }
}

resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_public_access_block" "documents" {
  bucket                  = aws_s3_bucket.documents.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id
  rule {
    bucket_key_enabled = true
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.documents.arn
      sse_algorithm     = "aws:kms"
    }
  }
}

data "aws_iam_policy_document" "documents_bucket" {
  statement {
    sid       = "DenyUnencryptedObjectWrites"
    effect    = "Deny"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.documents.arn}/*"]
    principals {
      type        = "AWS"
      identifiers = ["*"]
    }
    condition {
      test     = "StringNotEquals"
      variable = "s3:x-amz-server-side-encryption"
      values   = ["aws:kms"]
    }
  }
  statement {
    sid       = "DenyWrongKmsKey"
    effect    = "Deny"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.documents.arn}/*"]
    principals {
      type        = "AWS"
      identifiers = ["*"]
    }
    condition {
      test     = "StringNotEquals"
      variable = "s3:x-amz-server-side-encryption-aws-kms-key-id"
      values   = [aws_kms_key.documents.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "documents" {
  bucket = aws_s3_bucket.documents.id
  policy = data.aws_iam_policy_document.documents_bucket.json
}

# Private data-plane security groups: only ECS may reach PostgreSQL or Redis.
resource "aws_security_group" "ecs" {
  name   = "${local.name}-ecs"
  vpc_id = local.vpc_id
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [local.vpc_cidr]
  }
  egress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = [local.vpc_cidr]
  }
  egress {
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = [local.vpc_cidr]
  }
  egress {
    from_port   = 53
    to_port     = 53
    protocol    = "tcp"
    cidr_blocks = [local.vpc_cidr]
  }
}

resource "aws_security_group" "alb" {
  name   = "${local.name}-alb"
  vpc_id = local.vpc_id
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.allowed_ingress_cidrs
  }
}

resource "aws_vpc_security_group_ingress_rule" "ecs_api_from_alb" {
  security_group_id            = aws_security_group.ecs.id
  referenced_security_group_id = aws_security_group.alb.id
  from_port                    = 8000
  to_port                      = 8000
  ip_protocol                  = "tcp"
}
resource "aws_vpc_security_group_ingress_rule" "ecs_web_from_alb" {
  security_group_id            = aws_security_group.ecs.id
  referenced_security_group_id = aws_security_group.alb.id
  from_port                    = 3000
  to_port                      = 3000
  ip_protocol                  = "tcp"
}
resource "aws_vpc_security_group_egress_rule" "alb_to_api" {
  security_group_id            = aws_security_group.alb.id
  referenced_security_group_id = aws_security_group.ecs.id
  from_port                    = 8000
  to_port                      = 8000
  ip_protocol                  = "tcp"
}
resource "aws_vpc_security_group_egress_rule" "alb_to_web" {
  security_group_id            = aws_security_group.alb.id
  referenced_security_group_id = aws_security_group.ecs.id
  from_port                    = 3000
  to_port                      = 3000
  ip_protocol                  = "tcp"
}

resource "aws_security_group" "rds" {
  name   = "${local.name}-rds"
  vpc_id = local.vpc_id
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }
}

resource "aws_security_group" "redis" {
  name   = "${local.name}-redis"
  vpc_id = local.vpc_id
  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }
}

resource "aws_db_subnet_group" "main" {
  name       = local.name
  subnet_ids = local.subnet_ids
}

resource "aws_db_parameter_group" "postgres_ssl" {
  name   = "${local.name}-postgres-ssl"
  family = "postgres16"
  parameter {
    name         = "rds.force_ssl"
    value        = "1"
    apply_method = "immediate"
  }
}

resource "aws_db_instance" "postgres" {
  identifier                  = local.name
  engine                      = "postgres"
  engine_version              = "16"
  instance_class              = "db.t4g.micro"
  allocated_storage           = 20
  storage_encrypted           = true
  kms_key_id                  = aws_kms_key.documents.arn
  db_name                     = "tradesentry"
  username                    = "tradesentry_admin"
  manage_master_user_password = true
  db_subnet_group_name        = aws_db_subnet_group.main.name
  parameter_group_name        = aws_db_parameter_group.postgres_ssl.name
  vpc_security_group_ids      = [aws_security_group.rds.id]
  publicly_accessible         = false
  backup_retention_period     = 7
  deletion_protection         = true
  skip_final_snapshot         = false
  final_snapshot_identifier   = "${local.name}-final"
}

resource "aws_elasticache_subnet_group" "main" {
  name       = local.name
  subnet_ids = local.subnet_ids
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id       = local.name
  description                = "TradeSentry private TLS cache"
  node_type                  = "cache.t4g.micro"
  num_cache_clusters         = 1
  port                       = 6379
  subnet_group_name          = aws_elasticache_subnet_group.main.name
  security_group_ids         = [aws_security_group.redis.id]
  transit_encryption_enabled = true
  at_rest_encryption_enabled = true
}

resource "aws_secretsmanager_secret" "application" {
  name       = "/tradesentry/${var.environment}/application"
  kms_key_id = aws_kms_key.documents.arn
}

resource "aws_dynamodb_table" "trade_finance_registry" {
  name         = "TradeFinanceRegistry"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  range_key    = "SK"

  attribute {
    name = "PK"
    type = "S"
  }
  attribute {
    name = "SK"
    type = "S"
  }
  attribute {
    name = "bl_number_normalized"
    type = "S"
  }
  attribute {
    name = "registered_at"
    type = "S"
  }
  attribute {
    name = "vessel_normalized"
    type = "S"
  }
  attribute {
    name = "shipment_date_iso"
    type = "S"
  }
  attribute {
    name = "exporter_normalized"
    type = "S"
  }

  global_secondary_index {
    name            = "gsi_bl_number"
    hash_key        = "bl_number_normalized"
    range_key       = "registered_at"
    projection_type = "ALL"
  }
  global_secondary_index {
    name            = "gsi_vessel_date"
    hash_key        = "vessel_normalized"
    range_key       = "shipment_date_iso"
    projection_type = "ALL"
  }
  global_secondary_index {
    name            = "gsi_exporter"
    hash_key        = "exporter_normalized"
    range_key       = "registered_at"
    projection_type = "ALL"
  }
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
  point_in_time_recovery { enabled = true }
  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.documents.arn
  }
}

# Task role: no wildcard actions and only the named bucket, table/GSIs, secret and key.
resource "aws_iam_role" "ecs_task" {
  name = "${local.name}-ecs-task"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect = "Allow", Principal = { Service = "ecs-tasks.amazonaws.com" },
    Action = "sts:AssumeRole"
  }] })
}

resource "aws_iam_role_policy" "ecs_task" {
  role = aws_iam_role.ecs_task.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    {
      Sid      = "DocumentObjects", Effect = "Allow",
      Action   = ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"],
      Resource = ["${aws_s3_bucket.documents.arn}/*"]
    },
    {
      Sid    = "DocumentBucketVersioning", Effect = "Allow",
      Action = ["s3:GetBucketVersioning"], Resource = [aws_s3_bucket.documents.arn]
    },
    {
      # Textract does not support resource-level IAM permissions.
      Sid      = "RegionalTextract", Effect = "Allow",
      Action   = ["textract:AnalyzeDocument", "textract:StartDocumentAnalysis", "textract:GetDocumentAnalysis"],
      Resource = ["*"]
    },
    {
      Sid      = "RegistryOnly", Effect = "Allow",
      Action   = ["dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:Query", "dynamodb:UpdateItem", "dynamodb:DescribeTable"],
      Resource = concat([aws_dynamodb_table.trade_finance_registry.arn], local.registry_gsi_arns)
    },
    {
      Sid    = "DataKeyOnly", Effect = "Allow",
      Action = ["kms:Decrypt", "kms:GenerateDataKey"], Resource = [aws_kms_key.documents.arn]
    }
  ] })
}

resource "aws_dynamodb_resource_policy" "registry" {
  resource_arn = aws_dynamodb_table.trade_finance_registry.arn
  policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Sid       = "DenyOutsideEcsTaskRole", Effect = "Deny", Principal = "*",
    Action    = ["dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:Query", "dynamodb:UpdateItem"],
    Resource  = concat([aws_dynamodb_table.trade_finance_registry.arn], local.registry_gsi_arns),
    Condition = { ArnNotEquals = { "aws:PrincipalArn" = aws_iam_role.ecs_task.arn } }
  }] })
}

# CI deploy role. AWS requires Resource="*" for GetAuthorizationToken and
# RegisterTaskDefinition; all resource-scoped operations below use exact ARNs.
resource "aws_iam_role" "ci_deploy" {
  count = var.github_oidc_provider_arn == null ? 0 : 1
  name  = "${local.name}-ci-deploy"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect = "Allow", Principal = { Federated = var.github_oidc_provider_arn },
    Action = "sts:AssumeRoleWithWebIdentity",
    Condition = { StringEquals = { "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com" },
    StringLike = { "token.actions.githubusercontent.com:sub" = "repo:${var.github_repository}:ref:refs/heads/main" } }
  }] })
}

resource "aws_iam_role_policy" "ci_deploy" {
  count = var.github_oidc_provider_arn == null ? 0 : 1
  role  = aws_iam_role.ci_deploy[0].id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Sid = "EcrAuthorization", Effect = "Allow", Action = ["ecr:GetAuthorizationToken"], Resource = ["*"] },
    {
      Sid      = "PushImages", Effect = "Allow",
      Action   = ["ecr:BatchCheckLayerAvailability", "ecr:PutImage", "ecr:InitiateLayerUpload", "ecr:UploadLayerPart", "ecr:CompleteLayerUpload"],
      Resource = [aws_ecr_repository.api.arn, aws_ecr_repository.web.arn]
    },
    { Sid = "RegisterTask", Effect = "Allow", Action = ["ecs:RegisterTaskDefinition"], Resource = ["*"] },
    {
      Sid = "UpdateNamedServices", Effect = "Allow", Action = ["ecs:UpdateService"],
      Resource = [
        "arn:aws:ecs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:service/${aws_ecs_cluster.main.name}/tradesentry-api",
        "arn:aws:ecs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:service/${aws_ecs_cluster.main.name}/tradesentry-web"
      ]
    },
    { Sid = "PassTaskRole", Effect = "Allow", Action = ["iam:PassRole"], Resource = [aws_iam_role.ecs_task.arn] }
  ] })
}

resource "aws_ecr_repository" "api" {
  name = "tradesentry-api"
  image_scanning_configuration { scan_on_push = true }
  encryption_configuration {
    encryption_type = "KMS"
    kms_key         = aws_kms_key.documents.arn
  }
}
resource "aws_ecr_repository" "web" {
  name = "tradesentry-web"
  image_scanning_configuration { scan_on_push = true }
  encryption_configuration {
    encryption_type = "KMS"
    kms_key         = aws_kms_key.documents.arn
  }
}

resource "aws_ecs_cluster" "main" {
  name = local.name
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}
resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/tradesentry/api"
  retention_in_days = 90
  kms_key_id        = aws_kms_key.documents.arn
}
resource "aws_cloudwatch_log_group" "web" {
  name              = "/ecs/tradesentry/web"
  retention_in_days = 90
  kms_key_id        = aws_kms_key.documents.arn
}

resource "aws_iam_role" "ecs_execution" {
  name = "${local.name}-ecs-execution"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect = "Allow", Principal = { Service = "ecs-tasks.amazonaws.com" }, Action = "sts:AssumeRole"
  }] })
}

resource "aws_iam_role_policy" "ecs_execution" {
  role = aws_iam_role.ecs_execution.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Sid = "EcrAuthorization", Effect = "Allow", Action = ["ecr:GetAuthorizationToken"], Resource = ["*"] },
    { Sid = "PullImages", Effect = "Allow", Action = ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer", "ecr:BatchCheckLayerAvailability"], Resource = [aws_ecr_repository.api.arn, aws_ecr_repository.web.arn] },
    { Sid = "WriteApiLogs", Effect = "Allow", Action = ["logs:CreateLogStream", "logs:PutLogEvents"], Resource = ["${aws_cloudwatch_log_group.api.arn}:log-stream:*"] },
    { Sid = "WriteWebLogs", Effect = "Allow", Action = ["logs:CreateLogStream", "logs:PutLogEvents"], Resource = ["${aws_cloudwatch_log_group.web.arn}:log-stream:*"] }
    ,
    { Sid = "ReadRuntimeConfig", Effect = "Allow", Action = ["secretsmanager:GetSecretValue"], Resource = [aws_secretsmanager_secret.application.arn] },
    { Sid = "DecryptRuntimeConfig", Effect = "Allow", Action = ["kms:Decrypt"], Resource = [aws_kms_key.documents.arn] }
  ] })
}

resource "aws_ecs_task_definition" "api" {
  family                   = "tradesentry-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 256
  memory                   = 512
  task_role_arn            = aws_iam_role.ecs_task.arn
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  container_definitions = jsonencode([{ name = "api", image = "${aws_ecr_repository.api.repository_url}:${var.image_tag}", essential = true,
    portMappings = [{ containerPort = 8000, protocol = "tcp" }],
    environment = [
      { name = "AWS_REGION", value = var.aws_region },
      { name = "APP_VERSION", value = var.image_tag },
      { name = "ENVIRONMENT", value = var.environment },
      { name = "DEPLOYMENT", value = "AWS ECS · Textract · RDS · DynamoDB · ElastiCache · S3" },
      { name = "INFRASTRUCTURE_NOTE", value = "Deployed on AWS using hackathon credits" },
      { name = "SERVICE_CHECK_MODE", value = "live" },
      { name = "OCR_MODE", value = "live" },
      { name = "S3_BUCKET", value = aws_s3_bucket.documents.id },
      { name = "S3_KMS_KEY_ID", value = aws_kms_key.documents.arn },
      { name = "CROSS_IBU_TABLE_NAME", value = aws_dynamodb_table.trade_finance_registry.name },
      { name = "OTEL_SERVICE_NAME", value = "tradesentry-api" },
      { name = "OTEL_EXPORTER_OTLP_ENDPOINT", value = var.otel_exporter_otlp_endpoint }
    ],
    secrets = [
      { name = "DATABASE_URL", valueFrom = "${aws_secretsmanager_secret.application.arn}:DATABASE_URL::" },
      { name = "REDIS_URL", valueFrom = "${aws_secretsmanager_secret.application.arn}:REDIS_URL::" },
      { name = "JWT_PUBLIC_KEY", valueFrom = "${aws_secretsmanager_secret.application.arn}:JWT_PUBLIC_KEY::" }
    ],
    logConfiguration = { logDriver = "awslogs", options = { "awslogs-group" = aws_cloudwatch_log_group.api.name, "awslogs-region" = var.aws_region, "awslogs-stream-prefix" = "ecs" } }
  }])
}

resource "aws_ecs_task_definition" "web" {
  family                   = "tradesentry-web"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  container_definitions = jsonencode([{ name = "web", image = "${aws_ecr_repository.web.repository_url}:${var.image_tag}", essential = true,
    portMappings     = [{ containerPort = 3000, protocol = "tcp" }],
    logConfiguration = { logDriver = "awslogs", options = { "awslogs-group" = aws_cloudwatch_log_group.web.name, "awslogs-region" = var.aws_region, "awslogs-stream-prefix" = "ecs" } }
  }])
}

resource "aws_ecs_service" "api" {
  name            = "tradesentry-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.service_desired_count
  launch_type     = "FARGATE"
  network_configuration {
    subnets          = local.subnet_ids
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }
  health_check_grace_period_seconds = 60
  depends_on                        = [aws_lb_listener_rule.api]
}

resource "aws_ecs_service" "web" {
  name            = "tradesentry-web"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.web.arn
  desired_count   = var.service_desired_count
  launch_type     = "FARGATE"
  network_configuration {
    subnets          = local.subnet_ids
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.web.arn
    container_name   = "web"
    container_port   = 3000
  }
  health_check_grace_period_seconds = 60
  depends_on                        = [aws_lb_listener.http]
}

resource "aws_lb" "demo" {
  name                       = "${local.name}-demo"
  internal                   = false
  load_balancer_type         = "application"
  security_groups            = [aws_security_group.alb.id]
  subnets                    = local.subnet_ids
  drop_invalid_header_fields = true
}

resource "aws_lb_target_group" "api" {
  name        = "${local.name}-api"
  port        = 8000
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = local.vpc_id
  health_check {
    path                = "/health"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 15
    matcher             = "200"
  }
}

resource "aws_lb_target_group" "web" {
  name        = "${local.name}-web"
  port        = 3000
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = local.vpc_id
  health_check {
    path    = "/"
    matcher = "200-399"
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.demo.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.web.arn
  }
}

resource "aws_lb_listener_rule" "api" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 10
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
  condition {
    path_pattern {
      values = ["/health", "/cases*", "/cross-ibu*", "/audit-events*"]
    }
  }
}

resource "aws_lb_listener_rule" "api_docs" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 11
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
  condition {
    path_pattern {
      values = ["/docs*", "/openapi.json"]
    }
  }
}

# Structured-log metric extraction.
resource "aws_cloudwatch_log_metric_filter" "case_latency" {
  name           = "case_processing_latency_ms"
  log_group_name = aws_cloudwatch_log_group.api.name
  pattern        = "{ $.case_processing_latency_ms = * }"
  metric_transformation {
    name      = "case_processing_latency_ms"
    namespace = "TradeSentry"
    value     = "$.case_processing_latency_ms"
    unit      = "Milliseconds"
  }
}
resource "aws_cloudwatch_log_metric_filter" "tool_latency" {
  name           = "tool_call_latency_ms"
  log_group_name = aws_cloudwatch_log_group.api.name
  pattern        = "{ $.tool_call_latency_ms = * }"
  metric_transformation {
    name      = "tool_call_latency_ms"
    namespace = "TradeSentry"
    value     = "$.tool_call_latency_ms"
    unit      = "Milliseconds"
    dimensions = {
      ToolName = "$.tool_name"
    }
  }
}
resource "aws_cloudwatch_log_metric_filter" "risk_distribution" {
  name           = "risk_band_distribution"
  log_group_name = aws_cloudwatch_log_group.api.name
  pattern        = "{ $.event_type = \"RISK_SCORED\" }"
  metric_transformation {
    name      = "risk_band_distribution"
    namespace = "TradeSentry"
    value     = "1"
    dimensions = {
      RiskBand = "$.risk_band"
    }
  }
}
resource "aws_cloudwatch_log_metric_filter" "extraction_confidence" {
  name           = "extraction_confidence_avg"
  log_group_name = aws_cloudwatch_log_group.api.name
  pattern        = "{ $.extraction_confidence = * }"
  metric_transformation {
    name      = "extraction_confidence_avg"
    namespace = "TradeSentry"
    value     = "$.extraction_confidence"
  }
}
resource "aws_cloudwatch_log_metric_filter" "cross_ibu_rate" {
  name           = "cross_ibu_match_rate"
  log_group_name = aws_cloudwatch_log_group.api.name
  pattern        = "{ $.cross_ibu_match_rate = * }"
  metric_transformation {
    name      = "cross_ibu_match_rate"
    namespace = "TradeSentry"
    value     = "$.cross_ibu_match_rate"
  }
}

resource "aws_cloudwatch_metric_alarm" "error_rate" {
  alarm_name          = "${local.name}-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  threshold           = 1
  alarm_actions       = var.alarm_action_arns
  metric_query {
    id = "errors"
    metric {
      namespace   = "AWS/ApplicationELB"
      metric_name = "HTTPCode_Target_5XX_Count"
      period      = 300
      stat        = "Sum"
    }
    return_data = false
  }
  metric_query {
    id = "requests"
    metric {
      namespace   = "AWS/ApplicationELB"
      metric_name = "RequestCount"
      period      = 300
      stat        = "Sum"
    }
    return_data = false
  }
  metric_query {
    id          = "rate"
    expression  = "IF(requests > 0, 100 * errors / requests, 0)"
    label       = "ErrorPercent"
    return_data = true
  }
}
resource "aws_cloudwatch_metric_alarm" "p95_latency" {
  alarm_name          = "${local.name}-p95-latency"
  namespace           = "TradeSentry"
  metric_name         = "case_processing_latency_ms"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  period              = 300
  extended_statistic  = "p95"
  threshold           = 10000
  alarm_actions       = var.alarm_action_arns
}
resource "aws_cloudwatch_metric_alarm" "ecs_crash_loop" {
  alarm_name  = "${local.name}-ecs-crash-loop"
  namespace   = "ECS/ContainerInsights"
  metric_name = "RunningTaskCount"
  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = aws_ecs_service.api.name
  }
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  period              = 60
  statistic           = "Minimum"
  threshold           = 1
  alarm_actions       = var.alarm_action_arns
}
resource "aws_cloudwatch_metric_alarm" "dynamodb_throttles" {
  alarm_name          = "${local.name}-dynamodb-throttles"
  namespace           = "AWS/DynamoDB"
  metric_name         = "ThrottledRequests"
  dimensions          = { TableName = aws_dynamodb_table.trade_finance_registry.name }
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_actions       = var.alarm_action_arns
}
