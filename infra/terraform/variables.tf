variable "jwt_secret" {
  description = "JWT auth secret key"
  sensitive   = true
}

variable "xendit_secret_key" {
  description = "Xendit API Key"
  type        = string
  sensitive   = true
}

variable "xendit_callback_token" {
  description = "Callback verification token from Xendit dashboard"
  type        = string
  sensitive   = true
}

variable "postgres_user" {
  description = "Postgres database admin username"
  type        = string
  sensitive   = true
}

variable "postgres_password" {
  description = "Postgres database admin password"
  type        = string
  sensitive   = true
}
