terraform {
  required_providers {
    google = {
      source = "hashicorp/google"
      version = "4.80.0" // Provider version
    }
  }
  required_version = "1.5.6" // Terraform version
}

provider "google" {
  project     = var.project_id
  region      = var.region
  zone    = var.zone
}

// GKE Standard Cluster
resource "google_container_cluster" "gke_cluster" {
  name     = "${var.project_id}-gke"
  location = var.region
  remove_default_node_pool = true
  initial_node_count       = 1
  node_locations = [var.zone]
}

# Custom Node Pool
resource "google_container_node_pool" "node_pool" {
  name     = "node-pool-gke"
  cluster  = google_container_cluster.gke_cluster.name
  location = var.region
  node_count = 1
  node_config {
    machine_type = "e2-standard-4"
    preemptible  = false
    disk_size_gb = 40
  }
}

resource "google_storage_bucket" "my-bucket" {
  name          = var.bucket
  location      = var.region
  force_destroy = true
  uniform_bucket_level_access = true
}

resource "google_pubsub_topic" "mlops_topic" {
  name   = var.pubsub_topic
}

resource "google_pubsub_subscription" "mlops_subscription" {
  name  = "${var.pubsub_topic}-sub"
  topic = google_pubsub_topic.mlops_topic.id
  ack_deadline_seconds = 20
  depends_on = [google_pubsub_topic.mlops_topic]
}