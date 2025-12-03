from google.cloud import bigquery
from google.cloud import aiplatform
import pandas as pd
import numpy as np
import sys
import os
from kfp import compiler

# --- PATH FIX ---
# Add the training pipeline directory to sys.path so we can import 'components'
# This fixes the "ModuleNotFoundError: No module named 'components'"
training_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../pipelines/training'))
if training_dir not in sys.path:
    sys.path.append(training_dir)

# Now we can import the pipeline definition directly
from pipeline_definition_v2 import fraudshield_pipeline_v2

# --- CONFIG ---
PROJECT_ID = "fraudshield-v2-dev"
REGION = "us-central1"
BQ_TABLE = f"{PROJECT_ID}.fraudshield.predictions_log_v2"
PIPELINE_ROOT = f"gs://fraudshield-artifacts-dev-{PROJECT_ID}/pipeline_root"

def monitor_drift():
    client = bigquery.Client(project=PROJECT_ID)
    
    print("--- 1. Fetching Prediction Logs ---")
    query = f"""
        SELECT score, risk_band, timestamp 
        FROM `{BQ_TABLE}`
        ORDER BY timestamp DESC
    """
    df = client.query(query).to_dataframe()
    
    # Needs at least a few rows to calculate meaningful stats
    if len(df) < 2:
        print("Not enough data to calculate drift. (Need > 2 predictions)")
        return

    # Simulate "Today" vs "Baseline"
    # We split the data 20/80 just to demonstrate the math
    split_idx = int(len(df) * 0.2)
    if split_idx == 0: split_idx = 1 # Ensure at least 1 row in recent
    
    recent_df = df.iloc[:split_idx]
    baseline_df = df.iloc[split_idx:]
    
    avg_recent = recent_df['score'].mean()
    avg_baseline = baseline_df['score'].mean() if not baseline_df.empty else 0.5
    
    print(f"Baseline Avg Score: {avg_baseline:.4f}")
    print(f"Recent Avg Score:   {avg_recent:.4f}")
    
    # Avoid divide by zero
    if avg_baseline == 0: avg_baseline = 0.001
    
    drift_pct = abs((avg_recent - avg_baseline) / avg_baseline)
    print(f"Drift Detected:     {drift_pct:.2%}")
    
    # THRESHOLD: 20% deviation triggers retrain
    DRIFT_THRESHOLD = 0.20
    
    if drift_pct > DRIFT_THRESHOLD:
        print(f">>> ALERT: Drift > {DRIFT_THRESHOLD:.0%}. Triggering Retraining Pipeline...")
        trigger_retrain()
    else:
        print(">>> Status: System Healthy. No retraining needed.")

def trigger_retrain():
    print("--- 2. Compiling & Submitting Pipeline ---")
    
    package_path = "fraudshield_retrain_pipeline.json"
    compiler.Compiler().compile(
        pipeline_func=fraudshield_pipeline_v2,
        package_path=package_path
    )
    
    aiplatform.init(project=PROJECT_ID, location=REGION)
    
    job = aiplatform.PipelineJob(
        display_name="fraudshield-v2-autotrain",
        template_path=package_path,
        pipeline_root=PIPELINE_ROOT,
        enable_caching=False
    )
    job.submit()
    print(">>> Retraining Job Submitted: fraudshield-v2-autotrain")

if __name__ == "__main__":
    monitor_drift()