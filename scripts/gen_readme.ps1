# =============================================================================
# README GENERATOR & PUSH SCRIPT
# =============================================================================

$ProjectName = "AutoML FraudShield"
$ProjectID = "fraudshield-479419"
$RepoOwner = "BURNSGREGM"
$RepoName = "fraudshield-v1"
$RepoURL = "https://github.com/$RepoOwner/$RepoName"

Write-Host "Generating $ProjectName README.md..." -ForegroundColor Cyan

# 1. Define README Content (Using Here-String for multi-line Markdown)
$ReadmeContent = @"
# $ProjectName: Production-Grade MLOps on GCP

This repository contains the full source code, infrastructure as code (IaC), and automated pipelines for **AutoML FraudShield**, a production-grade fraud detection system built to demonstrate a complete MLOps lifecycle on Google Cloud Platform (GCP).

The architecture is designed for **reproducibility** and **low-latency serving**.

## 1. Core Architecture
The system utilizes the best-in-class MLOps tools within Vertex AI to manage data synchronization, training, and deployment.

| Layer | Component | Technology | Purpose |
| :--- | :--- | :--- | :--- |
| **Data & Storage** | Offline Data | BigQuery, GCS | Stores raw transaction logs and model artifacts. |
| **Feature Store** | Online/Offline Store | **Vertex AI Feature Store** | Provides real-time and historical aggregates (e.g., 7-day spend count). |
| **Orchestration** | Training Pipeline | **Vertex AI Pipelines (KFP)** | Automated ELT, XGBoost training, and model registration. |
| **Serving Layer** | Prediction API | **FastAPI** on **Cloud Run** | Low-latency endpoint that fetches features and serves predictions. |

## 2. Key Features Implemented
* **IaC:** All resources (BQ Dataset, GCS Buckets, Feature Store) are defined via **Terraform** (`infra/terraform`).
* **Real-Time Serving:** The Cloud Run API queries the Feature Store's online serving layer for features like `customer_txn_sum_7d`.
* **Model Training:** Training logic is containerized within the pipeline, using BQ to join raw transactions with engineered features.
* **Deployment:** Model registration is handled via the Vertex AI Model Registry, providing versioning for the production artifact.

## 3. Reproduction & Setup

This project requires a Google Cloud project with billing enabled.

| Tool | Purpose | Status |
| :--- | :--- | :--- |
| **Terraform** | Resource provisioning | Complete |
| **Python** | Data generation, scripting | Complete |
| **gcloud/bq** | Utility commands | Complete |

### Quick Start (Rehydration)
To provision all infrastructure, load data, and start the automated training pipeline, execute the main rehydration script from the project root:

```powershell
.\rehydrate.ps1