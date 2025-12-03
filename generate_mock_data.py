import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

# Settings
NUM_TRANSACTIONS = 5000
NUM_CUSTOMERS = 100
NUM_TERMINALS = 50
START_DATE = datetime(2024, 1, 1)

def generate_data():
    print(f"Generating {NUM_TRANSACTIONS} transactions...")
    
    # IDs
    customer_ids = [f"CUST_{i:04d}" for i in range(NUM_CUSTOMERS)]
    terminal_ids = [f"TERM_{i:04d}" for i in range(NUM_TERMINALS)]
    
    data = []
    
    for _ in range(NUM_TRANSACTIONS):
        # 1. Basic Transaction Info
        tx_id = f"TXN_{random.randint(10000000, 99999999)}"
        customer_id = random.choice(customer_ids)
        terminal_id = random.choice(terminal_ids)
        
        # Time distribution (more tx during day)
        days_offset = random.randint(0, 90)
        hour = int(np.random.normal(14, 4)) % 24 # Peak at 2pm
        tx_ts = START_DATE + timedelta(days=days_offset, hours=hour, minutes=random.randint(0,59))
        
        # Amounts (Log-normal distribution for realistic spend)
        amount = round(np.random.lognormal(3.5, 1.0), 2)
        
        # 2. Fraud Logic (Injecting signals for the model to find)
        is_fraud = 0
        
        # SCENARIO A: High Amount Spike
        if amount > 800 and random.random() < 0.8:
            is_fraud = 1
            
        # SCENARIO B: Late Night Activity (2AM - 5AM)
        if 2 <= tx_ts.hour <= 5 and random.random() < 0.3:
            is_fraud = 1
            
        # SCENARIO C: The "Busted Terminal" (Specific terminal has high fraud)
        if terminal_id == "TERM_0013" and random.random() < 0.5:
            is_fraud = 1

        data.append({
            "tx_id": tx_id,
            "customer_id": customer_id,
            "terminal_id": terminal_id,
            "tx_ts": tx_ts,
            "amount": amount,
            "is_fraud": is_fraud
        })

    df = pd.DataFrame(data)
    
    # Save to CSV
    output_path = "data/sample_transactions.csv"
    df.to_csv(output_path, index=False)
    print(f"? Data saved to {output_path}")
    print(df["is_fraud"].value_counts())

if __name__ == "__main__":
    generate_data()