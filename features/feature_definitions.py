from google.cloud import aiplatform
import variables # This imports the variables.py file in the same folder

def create_feature_store_resources():
    # Initialize SDK with project config
    aiplatform.init(project=variables.PROJECT_ID, location=variables.REGION)
    
    fs_name = variables.FEATURE_STORE_ID
    print(f"Connecting to Feature Store: {fs_name}...")
    
    # -------------------------------------------------------------------------
    # 1. Define Entity Types
    # SRS Reference: We need 'customers' and 'cards'
    # -------------------------------------------------------------------------
    entity_types = {
        "customers": "Customer entity for fraud detection",
        "cards": "Credit card entity"
    }

    for entity_name, description in entity_types.items():
        try:
            # Create EntityType (or get if exists)
            print(f"Checking Entity Type: {entity_name}...")
            
            # FIXED: Explicitly passing featurestore_name
            aiplatform.EntityType.create(
                featurestore_name=fs_name,
                entity_type_id=entity_name,
                description=description
            )
            print(f"✅ Entity Type '{entity_name}' created/verified.")
        except Exception as e:
            if "already exists" in str(e):
                print(f"ℹ️ Entity Type '{entity_name}' already exists. Skipping creation.")
            else:
                print(f"❌ Error creating {entity_name}: {e}")
                # We don't raise here to allow the script to try defining features 
                # even if the entity already existed.

    # -------------------------------------------------------------------------
    # 2. Define Features for 'customers'
    # [cite_start]SRS Reference [cite: 188-190]: Rolling aggregates
    # -------------------------------------------------------------------------
    customer_features = {
        "txn_count_7d": "INT64",
        "txn_amount_sum_7d": "DOUBLE",
        "avg_ticket_30d": "DOUBLE"
    }
    
    batch_create_features("customers", fs_name, customer_features)

    # -------------------------------------------------------------------------
    # 3. Define Features for 'cards'
    # [cite_start]SRS Reference [cite: 196-197]
    # -------------------------------------------------------------------------
    card_features = {
        "txn_count_7d": "INT64",
        "txn_amount_sum_7d": "DOUBLE"
    }
    
    batch_create_features("cards", fs_name, card_features)

def batch_create_features(entity_name, fs_name, feature_dict):
    print(f"Defining features for entity: {entity_name}...")
    
    # Get EntityType resource reference
    fs = aiplatform.Featurestore(featurestore_name=fs_name)
    et = fs.get_entity_type(entity_type_id=entity_name)
    
    # Prepare config batch
    feature_configs = {}
    for name, dtype in feature_dict.items():
        feature_configs[name] = {
            "value_type": dtype, 
            "description": f"Feature {name}"
        }

    try:
        # Batch create features
        et.batch_create_features(feature_configs=feature_configs).wait()
        print(f"✅ Features defined for {entity_name}")
    except Exception as e:
        if "already exists" in str(e):
             print(f"ℹ️ Features for {entity_name} already exist.")
        else:
            print(f"⚠️ Error creating features for {entity_name}: {e}")

if __name__ == "__main__":
    create_feature_store_resources()