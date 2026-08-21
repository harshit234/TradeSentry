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
