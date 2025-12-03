from google.cloud import bigquery
from google.cloud import aiplatform
import pandas as pd
import time
import variables  # Ensures we get the correct PROJECT_ID

def calculate_and_ingest():
    print(f"Initializing for Project: {variables.PROJECT_ID}...")
    bq_client = bigquery.Client(project=variables.PROJECT_ID)
    aiplatform.init(project=variables.PROJECT_ID, location=variables.REGION)
    fs = aiplatform.Featurestore(featurestore_name=variables.FEATURE_STORE_ID)

    # --- STEP 0: LOAD RAW DATA (The Fix) ---
    print("Step 0: Uploading sample_transactions.csv to BigQuery...")
    table_id = f"{variables.PROJECT_ID}.fraudshield.transactions"
    
    # Check if table exists, if not upload
    try:
        bq_client.get_table(table_id)
        print(" -> Table already exists. Skipping upload.")
    except Exception:
        print(" -> Table not found. Uploading now...")
        df = pd.read_csv("data/sample_transactions.csv")
        # Ensure timestamp is parsed correctly
        df['tx_ts'] = pd.to_datetime(df['tx_ts'])
        
        job_config = bigquery.LoadJobConfig(
            write_disposition="WRITE_TRUNCATE",
            schema=[
                bigquery.SchemaField("tx_ts", "TIMESTAMP"),
            ],
        )
        job = bq_client.load_table_from_dataframe(df, table_id, job_config=job_config)
        job.result() # Wait for completion
        print(f" -> Successfully loaded {job.output_rows} rows to {table_id}")

    # --- STEP 1: CALCULATE CUSTOMER FEATURES ---
    print("\nStep 1: Calculating Customer Features (SQL)...")
    cust_query = f"""
        CREATE OR REPLACE TABLE `{variables.PROJECT_ID}.fraudshield.features_customers` AS
        SELECT customer_id, tx_ts as feature_timestamp,
        COUNT(*) OVER(PARTITION BY customer_id ORDER BY UNIX_SECONDS(tx_ts) RANGE BETWEEN 604800 PRECEDING AND CURRENT ROW) as txn_count_7d,
        SUM(amount) OVER(PARTITION BY customer_id ORDER BY UNIX_SECONDS(tx_ts) RANGE BETWEEN 604800 PRECEDING AND CURRENT ROW) as txn_amount_sum_7d,
        AVG(amount) OVER(PARTITION BY customer_id ORDER BY UNIX_SECONDS(tx_ts) RANGE BETWEEN 2592000 PRECEDING AND CURRENT ROW) as avg_ticket_30d
        FROM `{variables.PROJECT_ID}.fraudshield.transactions`
    """
    bq_client.query(cust_query).result()
    print(" -> Customer features calculated.")

    # --- STEP 2: CALCULATE CARD FEATURES ---
    print("Step 2: Calculating Card Features (SQL)...")
    card_query = f"""
        CREATE OR REPLACE TABLE `{variables.PROJECT_ID}.fraudshield.features_cards` AS
        SELECT terminal_id as card_id, tx_ts as feature_timestamp, 
        COUNT(*) OVER(PARTITION BY terminal_id ORDER BY UNIX_SECONDS(tx_ts) RANGE BETWEEN 604800 PRECEDING AND CURRENT ROW) as txn_count_7d,
        SUM(amount) OVER(PARTITION BY terminal_id ORDER BY UNIX_SECONDS(tx_ts) RANGE BETWEEN 604800 PRECEDING AND CURRENT ROW) as txn_amount_sum_7d
        FROM `{variables.PROJECT_ID}.fraudshield.transactions`
    """
    # Note: In V1 mock data, we used 'terminal_id' as a proxy for 'card_id' for simplicity
    bq_client.query(card_query).result()
    print(" -> Card features calculated.")

    # --- STEP 3: CREATE ENTITIES (Idempotent) ---
    print("\nStep 3: Ensuring Entities & Features Exist in Vertex AI...")
    try:
        aiplatform.EntityType.create(featurestore_name=variables.FEATURE_STORE_ID, entity_type_id="customers")
    except: pass
    
    try:
        aiplatform.EntityType.create(featurestore_name=variables.FEATURE_STORE_ID, entity_type_id="cards")
    except: pass

    # Batch create features
    cust_feats = {"txn_count_7d": "INT64", "txn_amount_sum_7d": "DOUBLE", "avg_ticket_30d": "DOUBLE"}
    card_feats = {"txn_count_7d": "INT64", "txn_amount_sum_7d": "DOUBLE"}

    def create_feats(entity, feats):
        et = fs.get_entity_type(entity_type_id=entity)
        try:
            et.batch_create_features(feature_configs={k: {"value_type": v} for k,v in feats.items()}).wait()
        except: pass

    create_feats("customers", cust_feats)
    create_feats("cards", card_feats)

    # --- STEP 4: INGEST TO ONLINE STORE ---
    print("\nStep 4: Ingesting to Online Store (This takes ~5-10 mins)...")
    
    fs.get_entity_type("customers").ingest_from_bq(
        feature_ids=["txn_count_7d", "txn_amount_sum_7d", "avg_ticket_30d"],
        feature_time="feature_timestamp",
        bq_source_uri=f"bq://{variables.PROJECT_ID}.fraudshield.features_customers",
        entity_id_field="customer_id"
    )
    
    fs.get_entity_type("cards").ingest_from_bq(
        feature_ids=["txn_count_7d", "txn_amount_sum_7d"],
        feature_time="feature_timestamp",
        bq_source_uri=f"bq://{variables.PROJECT_ID}.fraudshield.features_cards",
        entity_id_field="card_id"
    )
    print(" -> Ingestion jobs submitted successfully.")

if __name__ == "__main__":
    calculate_and_ingest()