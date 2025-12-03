from kfp import dsl, compiler
# Import components
from components.validate_features_component import validate_features
from components.export_shap_artifacts_component import export_shap_artifacts
from components.train_model_component import train_xgboost_model
from components.deploy_model_component import deploy_model_to_endpoint

# --- CONFIG ---
PROJECT_ID = "fraudshield-v2-dev" 
REGION = "us-central1"
BUCKET_NAME = f"fraudshield-artifacts-dev-{PROJECT_ID}"
PIPELINE_ROOT = f"gs://{BUCKET_NAME}/pipeline_root"
SERVING_IMAGE = "us-docker.pkg.dev/vertex-ai/prediction/xgboost-cpu.1-6:latest"

@dsl.component(base_image="python:3.10", packages_to_install=["pandas", "google-cloud-bigquery", "db-dtypes"])
def extract_bq_to_dataset(project_id: str, query: str, dataset: dsl.Output[dsl.Dataset]):
    from google.cloud import bigquery
    import pandas as pd
    client = bigquery.Client(project=project_id)
    # The BQ client requires pyarrow/db-dtypes to handle the timestamp conversion to dataframe
    df = client.query(query).to_dataframe()
    df.to_csv(dataset.path, index=False)

@dsl.pipeline(
    name="fraudshield-training-pipeline-v2",
    description="V2 Pipeline: Validation -> Train -> SHAP -> Deploy"
)
def fraudshield_pipeline_v2(
    project_id: str = PROJECT_ID,
    region: str = REGION
):
    # CORRECTION: Mapped terminal_id to card_id and tx_id to transaction_id
    query = f"""
        SELECT 
            t.tx_id as transaction_id, 
            t.customer_id, 
            t.terminal_id as card_id, 
            t.tx_ts as timestamp,
            t.is_fraud, 
            t.amount,
            c.txn_count_7d, 
            c.txn_amount_sum_7d, 
            c.avg_ticket_30d,
            d.txn_count_7d as card_count_7d, 
            d.txn_amount_sum_7d as card_sum_7d
        FROM `{project_id}.fraudshield.transactions` t
        JOIN `{project_id}.fraudshield.features_customers` c 
            ON t.customer_id = c.customer_id AND t.tx_ts = c.feature_timestamp
        JOIN `{project_id}.fraudshield.features_cards` d
            ON t.terminal_id = d.card_id AND t.tx_ts = d.feature_timestamp
    """
    
    # Step 1: Extract
    extraction_task = extract_bq_to_dataset(
        project_id=project_id, 
        query=query
    )

    # Step 2: Validate Features (FR-E2)
    validation_task = validate_features(
        training_data=extraction_task.outputs["dataset"]
    )

    # Step 3: Train Model (Only runs if validation passes)
    train_task = train_xgboost_model(
        training_data=extraction_task.outputs["dataset"]
    ).after(validation_task)

    # Step 4: Export SHAP Artifacts (FR-E1)
    shap_task = export_shap_artifacts(
        training_data=extraction_task.outputs["dataset"]
    ).after(extraction_task)

    # Step 5: Deploy (FR-D2)
    deploy_task = deploy_model_to_endpoint(
        project_id=project_id,
        region=region,
        model=train_task.outputs["model_artifact"],
        endpoint_name="fraudshield-endpoint",
        display_name="fraudshield-xgb-v2",
        serving_container=SERVING_IMAGE
    ).after(train_task)

if __name__ == "__main__":
    compiler.Compiler().compile(
        pipeline_func=fraudshield_pipeline_v2,
        package_path="fraudshield_pipeline_v2.json"
    )
    
    # Auto-submit
    from google.cloud import aiplatform
    aiplatform.init(project=PROJECT_ID, location=REGION)
    
    job = aiplatform.PipelineJob(
        display_name="fraudshield-v2-run",
        template_path="fraudshield_pipeline_v2.json",
        pipeline_root=PIPELINE_ROOT,
        enable_caching=False
    )
    job.submit()
    print("Pipeline submitted successfully!")