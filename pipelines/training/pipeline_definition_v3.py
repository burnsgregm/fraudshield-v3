# In directory: fraudshield-v3/pipelines/training/
cat <<EOF > pipeline_definition_v3.py
from kfp import dsl, compiler
from components.deploy_model_component import deploy_model_to_endpoint
from components.train_model_component import train_hybrid_model

# --- Pipeline Constants (Injected from CI/CD Env) ---
PROJECT_ID = "$env:PROJECT_ID"
REGION = "us-central1"
BUCKET = f"fraudshield-artifacts-dev-{PROJECT_ID}"
PIPELINE_ROOT = f"gs://{BUCKET}/pipeline_root"
IMAGE_URI = f"us-central1-docker.pkg.dev/{PROJECT_ID}/fraudshield-repo/hybrid-cpr:v2"

@dsl.component(base_image="python:3.10", packages_to_install=["pandas", "google-cloud-bigquery", "db-dtypes"])
def extract_bq_to_dataset(project_id: str, query: str, dataset: dsl.Output[dsl.Dataset]):
    from google.cloud import bigquery
    # This query would join transactions with offline features (7d/30d)
    bigquery.Client(project=project_id).query(query).to_dataframe().to_csv(dataset.path, index=False)

@dsl.pipeline(name="fraudshield-training-pipeline-v3")
def fraudshield_pipeline_v3(project_id: str = PROJECT_ID, region: str = REGION):
    # This query pulls historical data (for training 7d/30d features) + the static labels
    query = f"""
    SELECT t.tx_id as transaction_id, t.customer_id, t.card_id, t.amount, t.is_fraud,
           c.txn_count_7d, c.txn_amount_sum_7d, c.avg_ticket_30d, 
           d.txn_count_7d as card_count_7d, d.txn_amount_sum_7d as card_sum_7d
    FROM `{project_id}.fraudshield.transactions` t
    JOIN `{project_id}.fraudshield.features_customers` c ON t.customer_id = c.customer_id AND t.tx_ts = c.feature_timestamp
    JOIN `{project_id}.fraudshield.features_cards` d ON t.card_id = d.card_id AND t.tx_ts = d.feature_timestamp
    """
    
    extract = extract_bq_to_dataset(project_id=project_id, query=query)
    
    # Train the hybrid model (produces model.bst AND isolation_forest.joblib)
    train = train_hybrid_model(training_data=extract.outputs["dataset"], artifact_uri=f"gs://{BUCKET}/v3_hybrid_model")

    # Deploy the CPR container using the artifacts produced by the train step
    deploy_model_to_endpoint(
        project_id=project_id,
        region=region,
        # model_artifact is the GCS path where both models were saved
        model=train.outputs["model_artifact"], 
        endpoint_name="fraudshield-hybrid-endpoint",
        display_name="fraudshield-hybrid-v1",
        serving_container=IMAGE_URI,
        predictor_file="predictor.py" # Specify the entrypoint for the CPR
    ).after(train)

if __name__ == "__main__":
    compiler.Compiler().compile(pipeline_func=fraudshield_pipeline_v3,
                                package_path="fraudshield_pipeline_v3.json")
    
    # Submission logic would typically follow here
EOF