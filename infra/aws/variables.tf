variable "aws_region" {
  type    = string
  default = "ap-south-1"
}
variable "aws_profile" {
  type     = string
  default  = null
  nullable = true
}
variable "environment" {
  type    = string
  default = "staging"
}
variable "vpc_id" {
  type        = string
  default     = null
  nullable    = true
  description = "Existing VPC; null selects the account default VPC"
}
variable "subnet_ids" {
  type        = list(string)
  default     = []
  description = "ECS/RDS/Redis subnet IDs; empty selects default-VPC subnets"
}
variable "vpc_cidr" {
  type        = string
  default     = null
  nullable    = true
  description = "VPC CIDR; null reads it from the selected default VPC"
}
variable "github_oidc_provider_arn" {
  type        = string
  default     = null
  nullable    = true
  description = "Optional existing GitHub Actions OIDC provider ARN"
}
variable "github_repository" {
  type    = string
  default = "harshit234/TradeSentry"
}
variable "otel_exporter_otlp_endpoint" {
  type        = string
  default     = ""
  description = "Optional private OpenTelemetry collector endpoint"
}
variable "alarm_action_arns" {
  type    = list(string)
  default = []
}
variable "image_tag" {
  type        = string
  default     = "latest"
  description = "Immutable git SHA image tag used by both ECS tasks"
}
variable "service_desired_count" {
  type        = number
  default     = 1
  description = "Set to zero during the first deployment phase before images/secrets exist"
}
variable "allowed_ingress_cidrs" {
  type        = list(string)
  default     = ["0.0.0.0/0"]
  description = "Hackathon demo ALB ingress CIDRs; restrict for non-demo environments"
}
