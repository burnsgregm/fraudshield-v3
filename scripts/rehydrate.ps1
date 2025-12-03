<#
.SYNOPSIS
    FraudShield V2 Data Re-hydration Script
.DESCRIPTION
    1. Activates local Python environment.
    2. Generates fresh mock transaction data (CSV).
    3. Uploads raw data to BigQuery.
    4. Calculates aggregations (SQL).
    5. Ingests features into Vertex AI Feature Store.
#>

$ErrorActionPreference = "Stop"

Write-Host "?? Starting FraudShield V2 Data Re-hydration..." -ForegroundColor Cyan

# 1. Check & Activate Virtual Environment
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "   -> Activating virtual environment..." -ForegroundColor Gray
    & .\venv\Scripts\Activate.ps1
} else {
    Write-Warning "   [!] 'venv' folder not found. Attempting to run with system Python..."
}

# 2. Generate Data
Write-Host "`n[Step 1/2] Generating Mock Data..." -ForegroundColor Yellow
try {
    python data/generate_mock_data.py
} catch {
    Write-Error "Failed to generate data. Check if python is installed."
    exit 1
}

# 3. Ingest to Feature Store
Write-Host "`n[Step 2/2] Ingesting to BigQuery & Feature Store..." -ForegroundColor Yellow
Write-Host "          (This process typically takes 5-8 minutes)" -ForegroundColor Gray

try {
    python features/ingest_features.py
} catch {
    Write-Error "Ingestion script failed."
    exit 1
}

Write-Host "`n? Re-hydration Complete! The V2 Environment is ready." -ForegroundColor Green