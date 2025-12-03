import os
import joblib
import numpy as np
import xgboost as xgb
from google.cloud.aiplatform.prediction.predictor import Predictor
from google.cloud.aiplatform.utils import prediction_utils

class CprPredictor(Predictor):
    def __init__(self):
        self.xgb_model = None
        self.iso_model = None

    def load(self, artifacts_uri: str):
        """Loads both models from the GCS artifact directory."""
        print(f"Loading artifacts from {artifacts_uri}")
        
        # 1. Load XGBoost
        # Vertex AI downloads artifacts to a local path (artifacts_uri)
        xgb_path = os.path.join(artifacts_uri, "model.bst")
        self.xgb_model = xgb.XGBClassifier()
        self.xgb_model.load_model(xgb_path)
        
        # 2. Load Isolation Forest
        iso_path = os.path.join(artifacts_uri, "isolation_forest.joblib")
        self.iso_model = joblib.load(iso_path)
        
        print("Hybrid models loaded successfully.")

    def predict(self, instances):
        """
        Input: List of lists (feature vectors)
        Output: Dictionary with score and risk band
        """
        # Convert to numpy array
        inputs = np.array(instances)
        
        # Thread A: XGBoost Probability (0 to 1)
        prob_xgb = self.xgb_model.predict_proba(inputs)[:, 1]
        
        # Thread B: Isolation Forest
        # decision_function returns negative for anomalies, positive for normal.
        # We invert it so higher = more anomalous.
        # Normalizing roughly to 0-1 for the ensemble (simplified logic)
        raw_iso = self.iso_model.decision_function(inputs)
        # Flip: -1 (anomaly) becomes 1, 1 (normal) becomes 0
        prob_iso = 1 - ((raw_iso + 1) / 2) 
        prob_iso = np.clip(prob_iso, 0, 1)

        # Ensemble Logic
        # 80% Supervised, 20% Unsupervised
        final_scores = (0.8 * prob_xgb) + (0.2 * prob_iso)
        
        results = []
        for score in final_scores:
            band = "LOW"
            if score > 0.7: band = "HIGH"
            elif score > 0.3: band = "MEDIUM"
            
            results.append({
                "score": float(score),
                "risk_band": band,
                "components": {
                    "xgb": float(prob_xgb[0]),
                    "iso": float(prob_iso[0])
                }
            })
            
        return {"predictions": results}
