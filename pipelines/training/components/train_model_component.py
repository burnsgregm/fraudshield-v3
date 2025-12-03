from kfp.dsl import component, Input, Output, Dataset, Model, Metrics

@component(base_image="python:3.10", packages_to_install=["pandas", "xgboost", "scikit-learn"])
def train_xgboost_model(
    training_data: Input[Dataset], 
    model_artifact: Output[Model], 
    metrics_artifact: Output[Metrics]
):
    import pandas as pd
    import xgboost as xgb
    import os
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import roc_auc_score, average_precision_score

    # 1. Load Data
    df = pd.read_csv(training_data.path)
    
    # 2. Separate Features & Label
    excluded_cols = ['transaction_id', 'customer_id', 'card_id', 'timestamp', 'tx_ts', 'is_fraud']
    feature_cols = [c for c in df.columns if c not in excluded_cols]
    
    X = df[feature_cols]
    y = df['is_fraud']

    # 3. Train
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # CRITICAL FIX: Convert to numpy values to strip feature names.
    # This allows the Serving Container to accept simple lists [[v1, v2...]] without schema errors.
    model = xgb.XGBClassifier(objective="binary:logistic", use_label_encoder=False, n_estimators=100)
    model.fit(X_train.values, y_train)

    # 4. Evaluate
    # Use .values here too so dimensions match
    y_probs = model.predict_proba(X_test.values)[:, 1]
    metrics_artifact.log_metric("roc_auc", roc_auc_score(y_test, y_probs))
    metrics_artifact.log_metric("pr_auc", average_precision_score(y_test, y_probs))

    # 5. Save Model
    model_artifact.metadata["framework"] = "xgboost"
    os.makedirs(model_artifact.path, exist_ok=True)
    model.save_model(os.path.join(model_artifact.path, "model.bst"))