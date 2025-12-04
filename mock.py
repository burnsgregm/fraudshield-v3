from fastapi import FastAPI
from pydantic import BaseModel
import random
import time

app = FastAPI(title="FraudShield V3: Real-Time Hybrid API", version="3.1.0")

class TransactionRequest(BaseModel):
    transaction_id: str
    tenant_id: str
    card_id: str
    amount: float

@app.post("/v3/score")
def score(txn: TransactionRequest):
    # Simulate processing delay (Network + Feature Store + Model)
    time.sleep(0.12) 
    
    # Mock logic for realistic responses
    is_suspicious = txn.amount > 800
    
    score = random.uniform(0.75, 0.95) if is_suspicious else random.uniform(0.01, 0.2)
    risk = "HIGH" if score > 0.7 else "LOW"
    
    return {
        "transaction_id": txn.transaction_id,
        "tenant_id": txn.tenant_id,
        "model_version": "fraudshield-hybrid-v1",
        "risk_assessment": {
            "score": round(score, 4),
            "risk_band": risk,
            "components": {
                "xgboost_prob": round(score * 0.9, 4),
                "iso_forest_anomaly": round(random.uniform(0.5, 0.9), 4) if is_suspicious else 0.1
            }
        },
        "input_features": {
            "amount": txn.amount,
            "velocity_features": {
                "txn_count_10m": random.randint(5, 20) if is_suspicious else random.randint(0, 3),
                "txn_sum_10m": txn.amount * random.uniform(1.0, 3.0)
            }
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)