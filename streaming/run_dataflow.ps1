$env:PROJECT_ID = "fraudshield-v3-dev-5320"
$env:REGION = "us-central1"
$BUCKET = "fraudshield-dataflow-temp-dev-$env:PROJECT_ID"
$JOB_NAME = "fraudshield-streaming-v3-20251202-172344"
$SERVICE_ACCOUNT = "fraudshield-dataflow-sa@$env:PROJECT_ID.iam.gserviceaccount.com"

Write-Host "Submitting Dataflow Job: $JOB_NAME"

python streaming/pipeline.py \
  --runner=DataflowRunner \
  --job_name=$JOB_NAME \
  --temp_location=gs://$BUCKET/temp \
  --service_account_email=$SERVICE_ACCOUNT \
  --setup_file=streaming/setup.py \
  --region=$env:REGION
