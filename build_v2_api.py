import os

# --- FILE DEFINITIONS ---

# 1. Requirements (Added SHAP and Vertex AI SDK)
requirements_txt = """fastapi==0.95.1
uvicorn==0.22.0
google-cloud-aiplatform==1.35.0
google-cloud-storage==2.10.0
google-cloud-pubsub==2.18.0
xgboost==1.6.2
pandas==1.5.3
scikit-learn==1.2.2
shap==0.41.0
pydantic==1.10.7
numpy<2.0.0
"""

# 2. Feature Store Client (Fetches history from Vertex)
fs_client_code = """from google.cloud import aiplatform
from google.cloud.aiplatform_v1 import FeaturestoreOnlineServingServiceClient, ReadFeatureValuesRequest
from google.cloud.aiplatform_v1.types import FeatureSelector, IdMatcher
import os

# HARDCODED CONFIG FOR V2
PROJECT_ID = "fraudshield-v2-dev"
REGION = "us-central1"
FEATURE_STORE_ID = "fraudshield_feature_store_dev"

class FeatureStoreClient:
    def __init__(self):
        api_endpoint = f"{REGION}-aiplatform.googleapis.com"
        self.client = FeaturestoreOnlineServingServiceClient(client_options={"api_endpoint": api_endpoint})
        self.fs_path = f"projects/{PROJECT_ID}/locations/{REGION}/featurestores/{FEATURE_STORE_ID}"

    def get_customer_features(self, customer_id: str):
        return self._get_features("customers", customer_id, ["txn_count_7d", "txn_amount_sum_7d", "avg_ticket_30d"])

    def get_card_features(self, card_id: str):
        return self._get_features("cards", card_id, ["txn_count_7d", "txn_amount_sum_7d"])

    def _get_features(self, entity_type, entity_id, feature_ids):
        entity_path = f"{self.fs_path}/entityTypes/{entity_type}"
        selector = FeatureSelector(id_matcher=IdMatcher(ids=feature_ids))
        try:
            response = self.client.read_feature_values(
                request=ReadFeatureValuesRequest(entity_type=entity_path, entity_id=entity_id, feature_selector=selector)
            )
            result = {}
            for i, feature in enumerate(response.header.feature_descriptors):
                val = 0.0
                data = response.entity_view.data[i]
                if data.value.double_value: val = data.value.double_value
                elif data.value.int64_value: val = float(data.value.int64_value)
                result[feature.id.split("/")[-1]] = val
            return result
        except Exception as e:
            print(f"FS Error: {e}")
            return {f: 0.0 for f in feature_ids}
"""

# 3. Model Endpoint Client (New: Calls Vertex Endpoint for Scoring)
endpoint_client_code = """from google.cloud import aiplatform
import os

class ModelEndpointClient:
    def __init__(self, project_id, region, endpoint_name):
        aiplatform.init(project=project_id, location=region)
        endpoints = aiplatform.Endpoint.list(filter=f'display_name="{endpoint_name}"')
        if not endpoints:
            raise RuntimeError(f"Endpoint {endpoint_name} not found in Vertex AI.")
        self.endpoint = endpoints[0]

    def predict(self, feature_vector):
        # Vertex expects [[f1, f2, f3...]]
        prediction = self.endpoint.predict(instances=[feature_vector])
        # XGBoost output is usually [Prob_Class_0, Prob_Class_1] or just Prob_Class_1
        # Depending on the serving container. We assume Prob(Fraud).
        # Adjust logic if the container returns pairs.
        return prediction.predictions[0] 
"""

# 4. SHAP Explainer (New: Calculates Feature Contributions locally)
shap_explainer_code = """import shap
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
"""

# 5. Main API (Orchestrator)
main_app_code = """from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import json
from google.cloud import pubsub_v1
from app.services.feature_store_client import FeatureStoreClient
from app.services.model_endpoint_client import ModelEndpointClient
from app.services.shap_explainer import ShapExplainer

app = FastAPI(title="AutoML FraudShield V2 API")

# --- CONFIG ---
PROJECT_ID = "fraudshield-v2-dev"
REGION = "us-central1"
ENDPOINT_NAME = "fraudshield-endpoint"
PUBSUB_TOPIC = "fraudshield-predictions"

# URI PLACEHOLDER - USER WILL REPLACE THIS AFTER PIPELINE RUNS
SHAP_ARTIFACT_URI = os.environ.get("SHAP_ARTIFACT_URI", "") 

# Globals
fs_client = None
endpoint_client = None
shap_explainer = None
publisher = None
topic_path = None

class TransactionRequest(BaseModel):
    transaction_id: str
    customer_id: str
    card_id: str
    amount: float
    timestamp: str

@app.on_event("startup")
def startup_event():
    global fs_client, endpoint_client, shap_explainer, publisher, topic_path
    
    # 1. Init Feature Store
    fs_client = FeatureStoreClient()
    
    # 2. Init Vertex Endpoint
    try:
        endpoint_client = ModelEndpointClient(PROJECT_ID, REGION, ENDPOINT_NAME)
        print("Vertex Endpoint connected.")
    except Exception as e:
        print(f"Warning: Endpoint connection failed: {e}")

    # 3. Init SHAP Explainer
    if SHAP_ARTIFACT_URI:
        try:
            # Parse gs://bucket/path/to/artifacts
            parts = SHAP_ARTIFACT_URI.replace("gs://", "").split("/")
            bucket = parts[0]
            prefix = "/".join(parts[1:])
            
            shap_explainer = ShapExplainer(PROJECT_ID, bucket, prefix)
            shap_explainer.load_artifacts()
        except Exception as e:
            print(f"Warning: SHAP init failed: {e}")
    
    # 4. Init Pub/Sub
    try:
        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path(PROJECT_ID, PUBSUB_TOPIC)
    except Exception:
        print("Warning: PubSub init failed")

@app.post("/v1/score")
def score(txn: TransactionRequest):
    if not endpoint_client:
        raise HTTPException(503, "Scoring service unavailable")

    # 1. Feature Engineering (Must match training order!)
    cust = fs_client.get_customer_features(txn.customer_id)
    card = fs_client.get_card_features(txn.card_id)
    
    # Vector: [amount, txn_count_7d, txn_amount_sum_7d, avg_ticket_30d, card_count_7d, card_sum_7d]
    features = [
        txn.amount,
        cust.get("txn_count_7d", 0),
        cust.get("txn_amount_sum_7d", 0.0),
        cust.get("avg_ticket_30d", 0.0),
        card.get("txn_count_7d", 0),
        card.get("txn_amount_sum_7d", 0.0)
    ]

    # 2. Score (Vertex Endpoint)
    try:
        # Vertex wrapper returns list of probs. We take the last one (Positive Class) or 
        # if it returns a single float, use that.
        prediction = endpoint_client.predict(features)
        # Handle different XGBoost container output formats
        prob_fraud = prediction[1] if isinstance(prediction, list) else prediction
    except Exception as e:
        raise HTTPException(500, f"Scoring failed: {str(e)}")

    # 3. Risk Banding (FR-D3)
    risk = "LOW"
    if prob_fraud >= 0.6: risk = "HIGH"
    elif prob_fraud >= 0.2: risk = "MEDIUM"

    # 4. Explain (Local SHAP) (FR-E1)
    explanations = []
    if shap_explainer:
        try:
            explanations = shap_explainer.explain(features)
        except Exception as e:
            print(f"SHAP failed: {e}")

    # 5. Log (Pub/Sub) (FR-M1)
    if publisher and topic_path:
        log_entry = {
            "transaction_id": txn.transaction_id,
            "score": prob_fraud,
            "risk_band": risk,
            "explanations": explanations
        }
        publisher.publish(topic_path, json.dumps(log_entry).encode("utf-8"))

    return {
        "transaction_id": txn.transaction_id,
        "score": prob_fraud,
        "risk_band": risk,
        "explanations": explanations
    }
"""

# --- DIRECTORY SETUP ---
os.makedirs("api/app/services", exist_ok=True)

# --- FILE WRITING ---
files = {
    "api/requirements.txt": requirements_txt,
    "api/app/services/feature_store_client.py": fs_client_code,
    "api/app/services/model_endpoint_client.py": endpoint_client_code,
    "api/app/services/shap_explainer.py": shap_explainer_code,
    "api/app/main.py": main_app_code
}

for path, content in files.items():
    with open(path, "w") as f:
        f.write(content)
    print(f"Created {path}")

print("V2 API structure created successfully.")