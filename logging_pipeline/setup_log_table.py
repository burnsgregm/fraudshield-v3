from google.cloud import bigquery
import os

PROJECT_ID = "fraudshield-v2-dev"
DATASET_ID = "fraudshield"
TABLE_ID = "predictions_log_v2"

def create_log_table():
    client = bigquery.Client(project=PROJECT_ID)
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

    schema = [
        bigquery.SchemaField("transaction_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("score", "FLOAT", mode="REQUIRED"),
        bigquery.SchemaField("risk_band", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("explanations", "JSON", mode="NULLABLE"), # V2 Feature: Storing SHAP as JSON
        bigquery.SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED"), # Ingestion time
        bigquery.SchemaField("model_version", "STRING", mode="NULLABLE")
    ]

    table = bigquery.Table(table_ref, schema=schema)
    
    # Partition by day for cost efficiency
    table.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field="timestamp"
    )

    try:
        client.create_table(table)
        print(f"Created table {table_ref}")
    except Exception as e:
        print(f"Table might already exist: {e}")

if __name__ == "__main__":
    create_log_table()