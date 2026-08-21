variable "aws_region" {
  type    = string
  default = "ap-south-1"
}
variable "aws_profile" {
  type    = string
  default = "tradesentry-dev"
}
variable "environment" {
  type    = string
  default = "staging"
}
variable "vpc_id" {
  type        = string
  description = "Existing VPC for the Sprint 0 skeleton"
}
variable "private_subnet_ids" {
  type        = list(string)
  description = "Existing private subnet IDs"
}
variable "vpc_cidr" {
  type        = string
  description = "VPC CIDR used only for ECS egress to private data services"
}
variable "github_oidc_provider_arn" {
  type        = string
  description = "Existing GitHub Actions OIDC provider ARN"
}
variable "github_repository" {
  type    = string
  default = "harshit234/TradeSentry"
}
variable "otel_exporter_otlp_endpoint" {
  type        = string
  description = "Private OpenTelemetry collector endpoint"
}
variable "alarm_action_arns" {
  type    = list(string)
  default = []
}
