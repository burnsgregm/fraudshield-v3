variable "project_id" {
  description = "The GCP Project ID"
  type        = string
  default     = "fraudshield-v3-dev-5320" 
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "env" {
  description = "Environment"
  type        = string
  default     = "dev"
}