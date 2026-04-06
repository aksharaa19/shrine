terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_sql_database_instance" "shrine_db" {
  name             = "shrine-db"
  database_version = "POSTGRES_15"
  
  settings {
    tier = "db-f1-micro"
    
    ip_configuration {
      ipv4_enabled    = true
      private_network = google_compute_network.vpc_network.id
    }
    
    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      point_in_time_recovery_enabled = true
    }
  }
}

resource "google_compute_network" "vpc_network" {
  name                    = "shrine-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "subnet" {
  name          = "shrine-subnet"
  ip_cidr_range = "10.0.1.0/24"
  network       = google_compute_network.vpc_network.id
  region        = var.region
}

resource "google_storage_bucket" "shrine_bucket" {
  name          = "shrine-data-${var.project_id}"
  location      = var.region
  force_destroy = true
  
  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }
}

resource "google_service_account" "shrine_sa" {
  account_id   = "shrine-service-account"
  display_name = "Shrine Service Account"
}

resource "google_project_iam_member" "shrine_sa_roles" {
  for_each = toset([
    "roles/cloudsql.client",
    "roles/storage.objectAdmin",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter"
  ])
  
  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.shrine_sa.email}"
}

output "db_connection_name" {
  value = google_sql_database_instance.shrine_db.connection_name
}

output "bucket_name" {
  value = google_storage_bucket.shrine_bucket.name
}