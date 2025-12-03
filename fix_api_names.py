import os

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

# URI PLACEHOLDER - LOADED FROM ENV
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
    
    fs_client = FeatureStoreClient()
    
    try:
        endpoint_client = ModelEndpointClient(PROJECT_ID, REGION, ENDPOINT_NAME)
        print("Vertex Endpoint connected.")
    except Exception as e:
        print(f"Warning: Endpoint connection failed: {e}")

    if SHAP_ARTIFACT_URI:
        try:
            parts = SHAP_ARTIFACT_URI.replace("gs://", "").split("/")
            bucket = parts[0]
            prefix = "/".join(parts[1:])
            shap_explainer = ShapExplainer(PROJECT_ID, bucket, prefix)
            shap_explainer.load_artifacts()
        except Exception as e:
            print(f"Warning: SHAP init failed: {e}")
    
    try:
        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path(PROJECT_ID, PUBSUB_TOPIC)
    except Exception:
        print("Warning: PubSub init failed")

@app.post("/v1/score")
def score(txn: TransactionRequest):
    if not endpoint_client:
        raise HTTPException(503, "Scoring service unavailable")

    # 1. Feature Engineering
    cust = fs_client.get_customer_features(txn.customer_id)
    card = fs_client.get_card_features(txn.card_id)
    
    # FIX: Create Dictionary for Vertex (Explicit Names)
    # These keys MUST match the Training Pipeline SQL aliases exactly
    features_dict = {
        "amount": txn.amount,
        "txn_count_7d": cust.get("txn_count_7d", 0),
        "txn_amount_sum_7d": cust.get("txn_amount_sum_7d", 0.0),
        "avg_ticket_30d": cust.get("avg_ticket_30d", 0.0),
        "card_count_7d": card.get("txn_count_7d", 0),
        "card_sum_7d": card.get("txn_amount_sum_7d", 0.0)
    }

    # Create List for SHAP (Must match feature_map.json order)
    # The order is: amount, txn_count, txn_sum, avg_ticket, card_count, card_sum
    features_list = [
        features_dict["amount"],
        features_dict["txn_count_7d"],
        features_dict["txn_amount_sum_7d"],
        features_dict["avg_ticket_30d"],
        features_dict["card_count_7d"],
        features_dict["card_sum_7d"]
    ]

    # 2. Score (Vertex Endpoint) - PASS THE DICT
    try:
        prediction = endpoint_client.predict(features_dict)
        prob_fraud = prediction[1] if isinstance(prediction, list) else prediction
    except Exception as e:
        raise HTTPException(500, f"Scoring failed: {str(e)}")

    # 3. Risk Banding
    risk = "LOW"
    if prob_fraud >= 0.6: risk = "HIGH"
    elif prob_fraud >= 0.2: risk = "MEDIUM"

    # 4. Explain (Local SHAP) - PASS THE LIST
    explanations = []
    if shap_explainer:
        try:
            explanations = shap_explainer.explain(features_list)
        except Exception as e:
            print(f"SHAP failed: {e}")

    # 5. Log (Pub/Sub)
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

with open("api/app/main.py", "w") as f:
    f.write(main_app_code)

print("API patched with Feature Names.")