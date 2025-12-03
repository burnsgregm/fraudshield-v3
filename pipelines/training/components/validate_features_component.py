from kfp.dsl import component, Input, Dataset, Output, Metrics

@component(
    base_image="python:3.10",
    packages_to_install=["pandas"]
)
def validate_features(
    training_data: Input[Dataset],
    validation_metrics: Output[Metrics]
):
    import pandas as pd
    
    print("Validating feature quality...")
    df = pd.read_csv(training_data.path)
    
    # validation constraints
    MAX_MISSING_PCT = 0.05
    REQUIRED_COLS = ["amount", "txn_count_7d", "txn_amount_sum_7d", "is_fraud"]
    
    # 1. Schema Check
    missing_cols = [col for col in REQUIRED_COLS if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Data Validation Failed: Missing required columns: {missing_cols}")
        
    # 2. Null Value Check
    for col in df.columns:
        missing_cnt = df[col].isnull().sum()
        missing_pct = missing_cnt / len(df)
        
        print(f"Feature '{col}': {missing_pct:.2%} missing")
        validation_metrics.log_metric(f"{col}_missing_pct", missing_pct)
        
        if missing_pct > MAX_MISSING_PCT:
            raise ValueError(f"Data Validation Failed: Feature '{col}' has {missing_pct:.2%} missing values (Threshold: {MAX_MISSING_PCT:.2%})")

    print("Validation passed.")