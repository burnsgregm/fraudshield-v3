from kfp.dsl import component, Input, Output, Artifact, Dataset

@component(
    base_image="python:3.10",
    packages_to_install=["pandas", "numpy", "pyarrow"]
)
def export_shap_artifacts(
    training_data: Input[Dataset],
    shap_artifacts: Output[Artifact]
):
    import pandas as pd
    import os
    import json

    # 1. Load Training Data
    print("Loading training data for SHAP background generation...")
    df = pd.read_csv(training_data.path)
    
    # 2. Filter for "Normal" Transactions (Class 0)
    # SHAP works best when explaining deviations from a "baseline" of normal behavior.
    # We sample 1000 rows to keep the explanation step fast ( < 200ms latency requirement).
    background_df = df[df['is_fraud'] == 0]
    
    if len(background_df) > 1000:
        background_df = background_df.sample(n=1000, random_state=42)
    
    print(f"Selected {len(background_df)} rows for background dataset.")

    # 3. Drop Non-Feature Columns
    # We must ensure the background dataset strictly matches the model's feature input.
    # Exclude IDs, timestamps, and the label.
    excluded_cols = ['transaction_id', 'customer_id', 'card_id', 'timestamp', 'tx_ts', 'is_fraud']
    feature_cols = [c for c in df.columns if c not in excluded_cols]
    
    # Reorder to ensure stability
    background_clean = background_df[feature_cols]

    # 4. Save Artifacts
    os.makedirs(shap_artifacts.path, exist_ok=True)
    
    # Save the dataframe (Parquet is faster/smaller than CSV)
    bg_path = os.path.join(shap_artifacts.path, "background_data.parquet")
    background_clean.to_parquet(bg_path, index=False)
    
    # Save the feature map (List of feature names in strict order)
    # The Scoring API will use this to reconstruct the vector correctly.
    fm_path = os.path.join(shap_artifacts.path, "feature_map.json")
    with open(fm_path, 'w') as f:
        json.dump(feature_cols, f)

    print(f"SHAP artifacts saved to {shap_artifacts.path}")