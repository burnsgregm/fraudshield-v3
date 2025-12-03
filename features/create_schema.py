from google.cloud import aiplatform
import time

# Configuration from your env
PROJECT_ID = "fraudshield-v3-dev-5320"
REGION = "us-central1"
FEATURE_STORE_ID = "fraudshield_feature_store_dev"

def create_schema():
    print(f"Initializing Schema for {PROJECT_ID}...")
    aiplatform.init(project=PROJECT_ID, location=REGION)
    
    fs = aiplatform.Featurestore(featurestore_name=FEATURE_STORE_ID)
    
    # 1. Create Entity Type: 'cards'
    # Check if exists first to avoid errors
    try:
        cards_entity = fs.create_entity_type(
            entity_type_id="cards", 
            description="Credit Card Entities"
        )
        cards_entity.wait()
        print("Entity 'cards' created.")
    except Exception as e:
        print(f"Entity creation skipped (might exist): {e}")
        cards_entity = fs.get_entity_type("cards")

    # 2. Create Features: 'txn_count_10m', 'txn_sum_10m'
    # We use batch_create for efficiency
    try:
        cards_entity.batch_create_features(
            feature_configs={
                "txn_count_10m": {"value_type": "INT64", "description": "10 min sliding count"},
                "txn_sum_10m":   {"value_type": "DOUBLE", "description": "10 min sliding sum"},
            }
        ).wait()
        print("Features created successfully.")
    except Exception as e:
        print(f"Feature creation skipped: {e}")

if __name__ == "__main__":
    create_schema()
