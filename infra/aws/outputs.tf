output "region" {
  value = var.region
}

output "ecr_repository" {
  value = aws_ecr_repository.api.repository_url
}

output "api_url" {
  value = "https://${var.api_domain}/api/v1"
}

output "api_dns_target" {
  value = aws_lb.api.dns_name
}

output "frontend_url" {
  value = "https://${aws_cloudfront_distribution.web.domain_name}"
}

output "frontend_bucket" {
  value = aws_s3_bucket.web.id
}

output "cloudfront_id" {
  value = aws_cloudfront_distribution.web.id
}

output "cluster" {
  value = aws_ecs_cluster.main.name
}

output "api_task_definition" {
  value = aws_ecs_task_definition.api.arn
}

output "app_secret_arn" {
  value = aws_secretsmanager_secret.app.arn
}

output "migration_network" {
  value = { awsvpcConfiguration = { subnets = aws_subnet.private[*].id, securityGroups = [aws_security_group.tasks.id], assignPublicIp = "DISABLED" } }
}
