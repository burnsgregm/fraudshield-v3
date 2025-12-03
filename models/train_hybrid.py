import pandas as pd
import numpy as np
import xgboost as xgb
import joblib
import os
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import train_test_split

# Ensure output dir exists
os.makedirs("models_out", exist_ok=True)

print("Generating mock training data...")
# Mock data matching V3 schema (streaming features included)
data = []
for i in range(1000):
    is_fraud = 0
    amount = np.random.uniform(10, 500)
    # Streaming features
    txn_count_10m = np.random.randint(1, 10)
    txn_sum_10m = amount * txn_count_10m
    
    # Inject Fraud Patterns
    if np.random.random() < 0.1:
        is_fraud = 1
        amount = np.random.uniform(800, 2000)
        txn_count_10m = np.random.randint(10, 50) # Velocity attack
        txn_sum_10m = amount * txn_count_10m

    data.append([amount, txn_count_10m, txn_sum_10m, is_fraud])

df = pd.DataFrame(data, columns=["amount", "txn_count_10m", "txn_sum_10m", "is_fraud"])
X = df.drop("is_fraud", axis=1)
y = df["is_fraud"]

print("Training XGBoost (Supervised)...")
model_xgb = xgb.XGBClassifier(objective="binary:logistic", n_estimators=50, use_label_encoder=False)
model_xgb.fit(X, y)
model_xgb.save_model("models_out/model.bst")

print("Training Isolation Forest (Unsupervised)...")
# IsoForest trains on *all* data to learn "normality"
model_iso = IsolationForest(n_estimators=100, contamination=0.1, random_state=42)
model_iso.fit(X)
joblib.dump(model_iso, "models_out/isolation_forest.joblib")

print("Artifacts saved to models_out/")
