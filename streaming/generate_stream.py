import time
import json
import random
import logging
from datetime import datetime, timezone
from google.cloud import pubsub_v1

# --- Configuration ---
PROJECT_ID = "fraudshield-v3-dev-5320"
TOPIC_ID = "fraudshield-raw-events"
NUM_MESSAGES = 500
SLEEP_TIME = 0.5 # Send 2 transactions per second

# Setup Publisher
publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)

customer_ids = [f"CUST_{i:04d}" for i in range(100)]
card_ids = [f"CARD_{i:04d}" for i in range(50)]

print(f"Publishing {NUM_MESSAGES} events to {topic_path}...")

for i in range(NUM_MESSAGES):
    data = {
        "transaction_id": f"tx_{int(time.time())}_{i}",
        "tenant_id": "tenant_A", # Simulating multi-tenancy
        "customer_id": random.choice(customer_ids),
        "card_id": random.choice(card_ids),
        "amount": round(random.uniform(10, 500), 2),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # Simulate a "Velocity Attack" on one specific card
    if i % 20 == 0:
        data["card_id"] = "CARD_9999_ATTACK"
        data["amount"] = 1000.00
        print(f"!!! Sending ATTACK transaction on {data['card_id']} !!!")

    msg_bytes = json.dumps(data).encode("utf-8")
    
    try:
        future = publisher.publish(topic_path, msg_bytes)
        # future.result() # Block until published (optional)
    except Exception as e:
        print(f"Error: {e}")

    if i % 10 == 0:
        print(f"Sent {i} events...")
        
    time.sleep(SLEEP_TIME)

print("Stream simulation complete.")
