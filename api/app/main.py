import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google.cloud import aiplatform
from app.services.feature_store_client import FeatureStoreClient

app = FastAPI(title="FraudShield V3: Real-Time Hybrid API")

# Configuration
PROJECT_ID = ""
REGION = ""
FEATURE_STORE_ID = "fraudshield_feature_store_dev"
ENDPOINT_NAME = "fraudshield-hybrid-endpoint"

# Global Clients
fs_client = None
endpoint = None

class TransactionRequest(BaseModel):
    transaction_id: str
    tenant_id: str
    card_id: str
    amount: float

@app.on_event("startup")
def startup_event():
    global fs_client, endpoint
    print("Initializing V3 Services...")
    
    # 1. Connect to Feature Store
    fs_client = FeatureStoreClient(PROJECT_ID, REGION, FEATURE_STORE_ID)
    
    # 2. Connect to Vertex Endpoint
    aiplatform.init(project=PROJECT_ID, location=REGION)
    endpoints = aiplatform.Endpoint.list(filter=f'display_name="{ENDPOINT_NAME}"')
    if endpoints:
        endpoint = endpoints[0]
        print(f"Connected to Endpoint: {endpoint.resource_name}")
    else:
        print("WARNING: Endpoint not found. Prediction will fail.")

@app.post("/v3/score")
def score(txn: TransactionRequest):
    if not endpoint:
        raise HTTPException(status_code=503, detail="Model Endpoint unavailable")

    # 1. Fetch Real-Time Features (The "Velocity")
    # This hits the data your Dataflow job is currently writing
    velocity = fs_client.get_streaming_features(txn.card_id)
    
    # 2. Construct Feature Vector
    # Order MUST match training: [amount, txn_count_10m, txn_sum_10m]
    vector = [
        txn.amount,
        velocity["txn_count_10m"],
        velocity["txn_sum_10m"]
    ]
    
    # 3. Call Hybrid Model (The "Brain")
    try:
        # Vertex Endpoint expects a list of instances
        prediction = endpoint.predict(instances=[vector])
        result = prediction.predictions[0] # The dict returned by predictor.py
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")

    # 4. Return Combined Intelligence
    return {
        "transaction_id": txn.transaction_id,
        "tenant_id": txn.tenant_id,
        "velocity_features": velocity,
        "risk_assessment": result
    }
