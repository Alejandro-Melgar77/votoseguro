variable "region" {
  type    = string
  default = "us-east-1"
}
variable "name" {
  type    = string
  default = "votoseguro"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,19}$", var.name))
    error_message = "Use entre 3 y 20 caracteres en minúsculas, números y guiones."
  }
}
variable "api_domain" {
  type        = string
  description = "Dominio de la API, por ejemplo api.votoseguro.org."
}
variable "certificate_arn" {
  type        = string
  description = "Certificado ACM validado para api_domain en la misma región."
}
variable "route53_zone_id" {
  type    = string
  default = ""
}
variable "admin_email" {
  type = string
}
variable "image_tag" {
  type    = string
  default = "release"
}
variable "service_enabled" {
  type        = bool
  default     = false
  description = "Activar solo después de subir imagen y ejecutar migraciones."
}
variable "api_count" {
  type    = number
  default = 2
}
variable "db_instance_class" {
  type    = string
  default = "db.t4g.micro"
}
variable "db_multi_az" {
  type    = bool
  default = true
}
variable "llm_base_url" {
  type        = string
  description = "Endpoint de IA existente; se conserva su configuración y nombre."
}
variable "llm_model_name" {
  type    = string
  default = "votoseguro-lfm3"
}
variable "smtp_host" {
  type    = string
  default = ""
}
variable "smtp_from_email" {
  type    = string
  default = ""
}
variable "alarm_email" {
  type    = string
  default = ""
}
