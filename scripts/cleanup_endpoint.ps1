# In your project root (fraudshield-v3)
cat <<EOF > scripts/cleanup_endpoint.ps1
# This script undeploys the model and deletes the expensive Vertex AI Endpoint, 
# but keeps the Feature Store, BQ, and GCS buckets intact for reuse in V4.

$ENDPOINT_ID = "fraudshield-hybrid-endpoint"
$REGION = "$env:REGION"
$PROJECT_ID = "$env:PROJECT_ID"

Write-Host "Attempting to undeploy and delete Vertex AI Endpoint $ENDPOINT_ID..." -ForegroundColor Yellow

# 1. Undeploy all models (required before endpoint deletion)
gcloud ai endpoints undeploy-model $ENDPOINT_ID --all --region=$REGION --project=$PROJECT_ID --quiet

# 2. Delete the Endpoint itself
gcloud ai endpoints delete $ENDPOINT_ID --region=$REGION --project=$PROJECT_ID --quiet

Write-Host "Endpoint $ENDPOINT_ID deletion initiated." -ForegroundColor Green
EOF