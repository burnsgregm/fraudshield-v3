from google.cloud import pubsub_v1
from google.cloud import bigquery
import json
import datetime

# CONFIG
PROJECT_ID = "fraudshield-v2-dev"
SUBSCRIPTION_ID = "fraudshield-logger-sub"
TABLE_ID = f"{PROJECT_ID}.fraudshield.predictions_log_v2"

# CLIENTS
subscriber = pubsub_v1.SubscriberClient()
bq_client = bigquery.Client(project=PROJECT_ID)
subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_ID)

def callback(message):
    try:
        # 1. Parse Message
        data = json.loads(message.data.decode("utf-8"))
        print(f"Received prediction for tx: {data.get('transaction_id')}")

        # 2. Add Ingestion Metadata
        # Use current UTC time for the log timestamp
        row = {
            "transaction_id": data.get("transaction_id"),
            "score": data.get("score"),
            "risk_band": data.get("risk_band"),
            "explanations": json.dumps(data.get("explanations")), # Convert list/dict back to JSON string for BQ
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "model_version": "fraudshield-xgb-v2"
        }

        # 3. Insert into BigQuery
        errors = bq_client.insert_rows_json(TABLE_ID, [row])
        
        if errors:
            print(f"BQ Insert Errors: {errors}")
            # Do not ack if BQ fails, so Pub/Sub retries
            message.nack()
        else:
            # Success! Acknowledge message so it's removed from queue
            message.ack()

    except Exception as e:
        print(f"Critical Error: {e}")
        message.nack()

print(f"Listening for logs on {subscription_path}...")
streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)

try:
    streaming_pull_future.result()
except KeyboardInterrupt:
    streaming_pull_future.cancel()