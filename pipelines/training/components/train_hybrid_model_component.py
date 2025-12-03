import kfp.dsl as dsl
from kfp.dsl import component, Input, Output, Dataset, Model, Metrics
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.ensemble import IsolationForest
import joblib
import os

@component(
    base_image="python:3.10", 
    packages_to_install=["pandas", "xgboost", "scikit-learn", "joblib"]
)
def train_hybrid_model(
    training_data: Input[Dataset], 
    artifact_uri: str,
    metrics_artifact: Output[Metrics]
):
    """
    Trains XGBoost (supervised) and Isolation Forest (unsupervised) and saves 
    both artifacts to a single GCS location (artifact_uri) for the CPR to load.
    """
    df = pd.read_csv(training_data.path)
    
    # Assuming the training data now includes both V2 features (7d/30d) AND 
    # V3 streaming features (10m) for a complete training set.
    
    # Feature set for the model (must match the API vector order)
    features = ["amount", "txn_count_10m", "txn_sum_10m"] 
    
    X = df[features]
    y = df['is_fraud']
    
    # --- 1. XGBoost Training (Supervised) ---
    print("Starting XGBoost training...")
    model_xgb = xgb.XGBClassifier(objective="binary:logistic", n_estimators=50)
    model_xgb.fit(X, y)
    
    # Save XGBoost
    xgb_path = os.path.join(artifact_uri, "model.bst")
    model_xgb.save_model("model.bst")
    os.system(f"gsutil cp model.bst {xgb_path}")
    
    # --- 2. Isolation Forest Training (Unsupervised) ---
    print("Starting Isolation Forest training...")
    # Train on non-fraudulent data to define the normal baseline
    X_normal = df[df['is_fraud'] == 0][features]
    model_iso = IsolationForest(contamination=0.01, random_state=42, n_estimators=100)
    model_iso.fit(X_normal)
    
    # Save Isolation Forest
    iso_path = os.path.join(artifact_uri, "isolation_forest.joblib")
    joblib.dump(model_iso, "isolation_forest.joblib")
    os.system(f"gsutil cp isolation_forest.joblib {iso_path}")

    # --- Metrics (Simplified) ---
    metrics_artifact.log_metric("models_trained", 2)
    metrics_artifact.log_metric("xgb_artifact_gcs", xgb_path)
    metrics_artifact.log_metric("iso_artifact_gcs", iso_path)

    print("Hybrid model artifacts saved successfully.")

