# In directory: fraudshield-v3/features/
cat <<EOF > variables.py
# This assumes PROJECT_ID and REGION are read from environment variables set in the CI/CD pipeline
# For local use:
PROJECT_ID = "$env:PROJECT_ID"
REGION = "us-central1"
ENV = "dev"
FEATURE_STORE_ID = f"fraudshield_feature_store_{ENV}"

# Entity Definitions (Offline/Batch features are simplified for this phase)
CUSTOMER_FEATURES = ["txn_count_7d", "txn_amount_sum_7d", "avg_ticket_30d"]
CARD_FEATURES = ["txn_count_7d", "txn_amount_sum_7d", "txn_count_10m", "txn_sum_10m"] # Includes V3 Streaming features

# V3 Hybrid Model Configuration
MODEL_ARTIFACT_URI = f"gs://fraudshield-artifacts-{ENV}-{PROJECT_ID}/v3_hybrid_model"
EOF