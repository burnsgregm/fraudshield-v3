# Define the root project name
$projectRoot = "fraudshield"

# 1. Create Root Directory
New-Item -Path $projectRoot -ItemType Directory -Force | Out-Null

# 2. Create Documentation & Config
$dirs = @(
    "docs/architecture_diagrams",
    "notebooks"
)
foreach ($d in $dirs) { New-Item -Path "$projectRoot/$d" -ItemType Directory -Force | Out-Null }
New-Item -Path "$projectRoot/README.md" -ItemType File -Force | Out-Null
New-Item -Path "$projectRoot/pyproject.toml" -ItemType File -Force | Out-Null

# 3. Infrastructure (Terraform) Structure [cite: 336]
$infraDirs = @(
    "infra/terraform/modules/bigquery",
    "infra/terraform/modules/feature_store",
    "infra/terraform/modules/vertex_pipelines",
    "infra/terraform/modules/cloud_run_api",
    "infra/terraform/modules/monitoring",
    "infra/terraform/envs/dev",
    "infra/terraform/envs/prod"
)
foreach ($d in $infraDirs) { New-Item -Path "$projectRoot/$d" -ItemType Directory -Force | Out-Null }

# Create placeholder Terraform files
New-Item -Path "$projectRoot/infra/terraform/envs/dev/main.tf" -ItemType File -Force | Out-Null
New-Item -Path "$projectRoot/infra/terraform/envs/dev/variables.tf" -ItemType File -Force | Out-Null
New-Item -Path "$projectRoot/infra/terraform/envs/prod/main.tf" -ItemType File -Force | Out-Null
New-Item -Path "$projectRoot/infra/terraform/envs/prod/variables.tf" -ItemType File -Force | Out-Null

# 4. Data & Schemas [cite: 344]
New-Item -Path "$projectRoot/data/schemas" -ItemType Directory -Force | Out-Null
New-Item -Path "$projectRoot/data/schemas/transactions_schema.json" -ItemType File -Force | Out-Null
New-Item -Path "$projectRoot/data/schemas/predictions_log_schema.json" -ItemType File -Force | Out-Null

# 5. Features Logic [cite: 356]
New-Item -Path "$projectRoot/features/tests" -ItemType Directory -Force | Out-Null
New-Item -Path "$projectRoot/features/__init__.py" -ItemType File -Force | Out-Null
New-Item -Path "$projectRoot/features/feature_definitions.py" -ItemType File -Force | Out-Null

# 6. Pipelines (Training & Monitoring) [cite: 361]
$pipelineDirs = @(
    "pipelines/training/components",
    "pipelines/monitoring",
    "pipelines/utils"
)
foreach ($d in $pipelineDirs) { New-Item -Path "$projectRoot/$d" -ItemType Directory -Force | Out-Null }
New-Item -Path "$projectRoot/pipelines/__init__.py" -ItemType File -Force | Out-Null
New-Item -Path "$projectRoot/pipelines/training/pipeline_definition.py" -ItemType File -Force | Out-Null

# 7. Serving API (FastAPI) [cite: 378]
$apiDirs = @(
    "api/app/routers",
    "api/app/services",
    "api/tests"
)
foreach ($d in $apiDirs) { New-Item -Path "$projectRoot/$d" -ItemType Directory -Force | Out-Null }
New-Item -Path "$projectRoot/api/Dockerfile" -ItemType File -Force | Out-Null
New-Item -Path "$projectRoot/api/app/main.py" -ItemType File -Force | Out-Null

# 8. Model Artifacts & Local Training Scripts [cite: 396]
New-Item -Path "$projectRoot/models/artifacts" -ItemType Directory -Force | Out-Null
New-Item -Path "$projectRoot/models/train_model.py" -ItemType File -Force | Out-Null

Write-Host "Directory structure for $projectRoot created successfully." -ForegroundColor Green