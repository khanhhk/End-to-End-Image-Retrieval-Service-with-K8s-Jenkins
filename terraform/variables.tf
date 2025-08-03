variable "project_id" {
  description = "The project ID to host the cluster in"
  type        = string
  default     = "image-retrieval-project-mlops"
}

variable "region" {
  description = "The region the cluster in"
  type        = string
  default     = "asia-southeast1"
}

variable "zone" {
  description = "Zone to deploy GKE nodes"
  type        = string
  default     = "asia-southeast1-a"
}

variable "bucket" {
  description = "GCS bucket name"
  type        = string
  default     = "image-retrieval-bucket-1907"
}
