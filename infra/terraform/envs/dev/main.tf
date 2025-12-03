terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 4.0.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# --- Enabled APIs ---
resource "google_project_service" "enabled_apis" {
  for_each = toset([
    "aiplatform.googleapis.com", "bigquery.googleapis.com",
    "storage.googleapis.com", "artifactregistry.googleapis.com",
    "run.googleapis.com", "cloudbuild.googleapis.com",
    "pubsub.googleapis.com", "dataflow.googleapis.com"
  ])
  service            = each.key
  disable_on_destroy = false
}

# --- Storage ---
resource "google_storage_bucket" "artifacts" {
  name                        = "fraudshield-artifacts-${var.env}-${var.project_id}"
  location                    = var.region
  force_destroy               = true
  uniform_bucket_level_access = true
  depends_on                  = [google_project_service.enabled_apis]
}

resource "google_storage_bucket" "dataflow_temp" {
  name                        = "fraudshield-dataflow-temp-${var.env}-${var.project_id}"
  location                    = var.region
  force_destroy               = true
  uniform_bucket_level_access = true
  depends_on                  = [google_project_service.enabled_apis]
}

resource "google_artifact_registry_repository" "repo" {
  location      = var.region
  repository_id = "fraudshield-repo"
  format        = "DOCKER"
  depends_on    = [google_project_service.enabled_apis]
}

# --- Pub/Sub ---
resource "google_pubsub_topic" "predictions" {
  name       = "fraudshield-predictions"
  depends_on = [google_project_service.enabled_apis]
}

resource "google_pubsub_topic" "raw_events" {
  name       = "fraudshield-raw-events"
  depends_on = [google_project_service.enabled_apis]
}

resource "google_pubsub_subscription" "raw_events_sub" {
  name  = "fraudshield-raw-sub"
  topic = google_pubsub_topic.raw_events.name
  message_retention_duration = "604800s" # 7 days
}

# --- Data & Vertex AI ---
resource "google_bigquery_dataset" "fraudshield" {
  dataset_id                 = "fraudshield"
  location                   = var.region
  delete_contents_on_destroy = true
  depends_on                 = [google_project_service.enabled_apis]
}

resource "google_vertex_ai_featurestore" "featurestore" {
  name     = "fraudshield_feature_store_${var.env}"
  region   = var.region
  labels   = { env = var.env }
  online_serving_config {
    fixed_node_count = 1
  }
  depends_on = [google_project_service.enabled_apis]
}

resource "google_vertex_ai_endpoint" "primary" {
  name         = "fraudshield-hybrid-endpoint"
  display_name = "fraudshield-hybrid-endpoint"
  location     = var.region
  depends_on   = [google_project_service.enabled_apis]
}

# --- IAM for Dataflow ---
resource "google_service_account" "dataflow_sa" {
  account_id   = "fraudshield-dataflow-sa"
  display_name = "Dataflow Service Account for FraudShield V3"
}

resource "google_project_iam_member" "dataflow_worker" {
  project = var.project_id
  role    = "roles/dataflow.worker"
  member  = "serviceAccount:${google_service_account.dataflow_sa.email}"
}

resource "google_project_iam_member" "dataflow_admin" {
  project = var.project_id
  role    = "roles/dataflow.admin"
  member  = "serviceAccount:${google_service_account.dataflow_sa.email}"
}

resource "google_project_iam_member" "dataflow_storage" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.dataflow_sa.email}"
}

resource "google_project_iam_member" "dataflow_pubsub" {
  project = var.project_id
  role    = "roles/pubsub.editor"
  member  = "serviceAccount:${google_service_account.dataflow_sa.email}"
}

resource "google_project_iam_member" "dataflow_vertex" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.dataflow_sa.email}"
}
