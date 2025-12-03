from kfp import dsl
from kfp import compiler
import os

# Configuration
PROJECT_ID = "fraudshield-v2-dev"
REGION = "us-central1"
BUCKET_NAME = f"fraudshield-artifacts-dev-{PROJECT_ID}"
PIPELINE_ROOT = f"gs://{BUCKET_NAME}/pipeline_root"

# -----------------------------------------------------------------------------
# Component 1: Train Model
# -----------------------------------------------------------------------------
@dsl.component(
    base_image="python:3.9",
    packages_to_install=["pandas", "xgboost", "scikit-learn", "google-cloud-bigquery", "db-dtypes", "pyarrow"]
)
def train_xgboost_model(
    project_id: str,
    region: str,
    metrics: dsl.Output[dsl.Metrics],
    model: dsl.Output[dsl.Model],
):
    import pandas as pd
    import xgboost as xgb
    from google.cloud import bigquery
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import roc_auc_score, average_precision_score
    import os

    # 1. Define the SQL Query
    print(f"Connecting to BigQuery in {project_id}...")
    client = bigquery.Client(project=project_id, location=region)
    
    # FIXED QUERY: Using correct column names from the 'features_cards' table
    query = f"""
    SELECT 
        t.is_fraud,
        t.amount,
        -- Customer Features (c)
        c.txn_count_7d, 
        c.txn_amount_sum_7d, 
        c.avg_ticket_30d,
        -- Card Features (d) - These exist as 'txn_...' in the table, so we alias them here
        d.txn_count_7d as card_count_7d, 
        d.txn_amount_sum_7d as card_sum_7d
    FROM `{project_id}.fraudshield.transactions` t
    JOIN `{project_id}.fraudshield.features_customers` c 
        ON t.customer_id = c.customer_id AND t.timestamp = c.feature_timestamp
    JOIN `{project_id}.fraudshield.features_cards` d
        ON t.card_id = d.card_id AND t.timestamp = d.feature_timestamp
    """
    
    # 2. Load Data
    print("Running extraction query...")
    try:
        df = client.query(query).to_dataframe()
        print(f"✅ Data loaded: {len(df)} rows, {len(df.columns)} columns.")
    except Exception as e:
        print(f"❌ Query failed: {e}")
        raise e
    
    # 3. Prepare Data
    X = df.drop(columns=["is_fraud"])
    y = df["is_fraud"]
    
    print(f"Training Features: {list(X.columns)}")
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # 4. Train
    print("Starting XGBoost training...")
    model_xgb = xgb.XGBClassifier(
        objective="binary:logistic", 
        eval_metric="logloss", 
        use_label_encoder=False, 
        n_estimators=100
    )
    model_xgb.fit(X_train, y_train)
    
    # 5. Evaluate
    y_probs = model_xgb.predict_proba(X_test)[:, 1]
    roc_auc = roc_auc_score(y_test, y_probs)
    pr_auc = average_precision_score(y_test, y_probs)
    print(f"Metrics: ROC_AUC={roc_auc}, PR_AUC={pr_auc}")
    
    metrics.log_metric("roc_auc", roc_auc)
    metrics.log_metric("pr_auc", pr_auc)
    
    # 6. Save Artifact
    model.metadata["framework"] = "xgboost"
    model_path = os.path.join(model.path, "model.bst")
    os.makedirs(model.path, exist_ok=True)
    model_xgb.save_model(model_path)
    print(f"Model saved to {model_path}")

# -----------------------------------------------------------------------------
# Component 2: Register Model
# -----------------------------------------------------------------------------
@dsl.component(
    base_image="python:3.9",
    packages_to_install=["google-cloud-aiplatform"]
)
def register_model(
    project_id: str,
    region: str,
    model: dsl.Input[dsl.Model],
    display_name: str,
    serving_image: str
):
    from google.cloud import aiplatform
    
    print(f"Registering model from: {model.uri}")
    
    aiplatform.init(project=project_id, location=region)
    
    aiplatform.Model.upload(
        display_name=display_name,
        artifact_uri=model.uri.replace("/model.bst", ""),
        serving_container_image_uri=serving_image,
        sync=True
    )
    print("✅ Model registered successfully.")

# -----------------------------------------------------------------------------
# Pipeline Definition
# -----------------------------------------------------------------------------
@dsl.pipeline(
    name="fraudshield-training-pipeline",
    description="End-to-end fraud detection pipeline (Simplified)"
)
def fraudshield_pipeline(
    project_id: str = PROJECT_ID,
    region: str = REGION
):
    # Step 1: Train
    train_task = train_xgboost_model(
        project_id=project_id,
        region=region
    )

    # Step 2: Register
    register_task = register_model(
        project_id=project_id,
        region=region,
        model=train_task.outputs["model"],
        display_name="fraudshield-xgb-v1",
        serving_image="us-docker.pkg.dev/vertex-ai/prediction/xgboost-cpu.1-6:latest"
    )
    register_task.after(train_task)

# -----------------------------------------------------------------------------
# Compiler
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import google.cloud.aiplatform as aiplatform
    
    template_path = "fraudshield_pipeline.json"
    compiler.Compiler().compile(
        pipeline_func=fraudshield_pipeline,
        package_path=template_path
    )
    print(f"Pipeline compiled to {template_path}")
    
    aiplatform.init(project=PROJECT_ID, location=REGION)
    
    job = aiplatform.PipelineJob(
        display_name="fraudshield-training-run-fixed",
        template_path=template_path,
        pipeline_root=PIPELINE_ROOT,
        enable_caching=False
    )
    
    job.submit()
    print("Pipeline job submitted! Check the Console.")