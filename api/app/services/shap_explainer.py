import shap
import xgboost as xgb
import pandas as pd
import json
import os
from google.cloud import storage

class ShapExplainer:
    def __init__(self, project_id, bucket_name, artifact_prefix):
        self.project_id = project_id
        self.bucket_name = bucket_name
        self.artifact_prefix = artifact_prefix 
        self.explainer = None
        self.feature_names = []
        self.local_model = None

    def load_artifacts(self):
        print(f"Downloading SHAP artifacts from gs://{self.bucket_name}/{self.artifact_prefix}...")
        client = storage.Client(project=self.project_id)
        bucket = client.bucket(self.bucket_name)

        # Helper to find file recursively
        def download(fname):
            blobs = list(bucket.list_blobs(prefix=self.artifact_prefix))
            target = next((b for b in blobs if b.name.endswith(fname)), None)
            if target: target.download_to_filename(fname)
            else: raise FileNotFoundError(f"{fname} not found in {self.artifact_prefix}")

        download("feature_map.json")
        with open("feature_map.json", "r") as f:
            self.feature_names = json.load(f)

        download("background_data.parquet")
        bg_df = pd.read_parquet("background_data.parquet")

        download("model.bst")
        self.local_model = xgb.Booster()
        self.local_model.load_model("model.bst")

        print("Initializing TreeExplainer...")
        self.explainer = shap.TreeExplainer(self.local_model, bg_df)
        print("SHAP Explainer ready.")

    def explain(self, feature_vector):
        if not self.explainer: return []
        df = pd.DataFrame([feature_vector], columns=self.feature_names)
        shap_values = self.explainer.shap_values(df)[0]
        
        contributions = [
            {"feature": name, "contribution": float(val)} 
            for name, val in zip(self.feature_names, shap_values)
        ]
        # Sort by absolute impact
        contributions.sort(key=lambda x: abs(x["contribution"]), reverse=True)
        return contributions[:5]
