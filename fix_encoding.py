import os

# We use triple-single-quotes (''') for the outer wrapper 
# so the triple-double-quotes (""") inside the code don't break the script.
dashboard_code = '''import streamlit as st
from google.cloud import bigquery
from google.cloud import aiplatform
from google.oauth2 import service_account
import pandas as pd
import plotly.express as px
import os
import sys
import json

# --- CONFIG ---
PROJECT_ID = "fraudshield-v2-dev"
REGION = "us-central1"
TABLE_ID = f"{PROJECT_ID}.fraudshield.predictions_log_v2"
PIPELINE_ROOT = f"gs://fraudshield-artifacts-dev-{PROJECT_ID}/pipeline_root"

st.set_page_config(page_title="FraudShield Cockpit", layout="wide")

# --- AUTHENTICATION HANDLER ---
def get_credentials():
    # Check if running on Streamlit Cloud (secrets present)
    if "gcp_service_account" in st.secrets:
        return service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"]
        )
    # Fallback to local default (your laptop)
    return None 

creds = get_credentials()

# --- SIDEBAR ---
st.sidebar.title("FraudShield V2")
st.sidebar.markdown(f"**Project:** `{PROJECT_ID}`")

if st.sidebar.button("Refresh Data"):
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("Operations")

# --- RETRAIN BUTTON ---
if st.sidebar.button("Trigger Retraining"):
    with st.spinner("Compiling and Submitting Pipeline..."):
        try:
            # Setup paths for local pipeline import
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(current_dir)
            sys.path.append(os.path.join(parent_dir, 'pipelines', 'training'))
            
            from pipeline_definition_v2 import fraudshield_pipeline_v2
            from kfp import compiler

            # 1. Compile
            package_path = "fraudshield_manual_retrain.json"
            compiler.Compiler().compile(
                pipeline_func=fraudshield_pipeline_v2,
                package_path=package_path
            )
            
            # 2. Submit (Pass credentials explicitly)
            aiplatform.init(project=PROJECT_ID, location=REGION, credentials=creds)
            job = aiplatform.PipelineJob(
                display_name="fraudshield-v2-manual-dashboard",
                template_path=package_path,
                pipeline_root=PIPELINE_ROOT,
                enable_caching=False
            )
            job.submit()
            st.sidebar.success(f"Pipeline Submitted! Job: {job.resource_name.split('/')[-1]}")
        except Exception as e:
            st.sidebar.error(f"Failed: {e}")

# --- MAIN DASHBOARD ---
st.title("FraudShield Operations Center")

@st.cache_data(ttl=60)
def load_data():
    # Pass credentials explicitly to BigQuery Client
    client = bigquery.Client(project=PROJECT_ID, credentials=creds)
    # Double quotes inside here are safe because outer wrapper is single quotes
    query = f"""
        SELECT transaction_id, score, risk_band, timestamp, model_version
        FROM `{TABLE_ID}`
        ORDER BY timestamp DESC
        LIMIT 1000
    """
    return client.query(query).to_dataframe()

try:
    df = load_data()
    
    if df.empty:
        st.warning("No logs found in BigQuery yet.")
    else:
        # METRICS
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Predictions", len(df))
        col2.metric("Avg Fraud Score", f"{df['score'].mean():.4f}")
        high_risk_count = len(df[df['risk_band'] == 'HIGH'])
        col3.metric("High Risk Tx", high_risk_count, delta_color="inverse")
        latest_version = df.iloc[0]['model_version'] if 'model_version' in df.columns else "N/A"
        col4.metric("Active Model", latest_version)

        # CHARTS
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Score Distribution")
            fig_hist = px.histogram(df, x="score", nbins=20, title="Fraud Score Histogram", color_discrete_sequence=['#636EFA'])
            st.plotly_chart(fig_hist, use_container_width=True)
        with c2:
            st.subheader("Drift Monitor")
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            fig_line = px.line(df, x="timestamp", y="score", title="Avg Score Over Time", markers=True)
            st.plotly_chart(fig_line, use_container_width=True)

        st.subheader("Recent Live Traffic")
        st.dataframe(df[['timestamp', 'transaction_id', 'score', 'risk_band']].head(20), use_container_width=True)

except Exception as e:
    st.error(f"Connection Error: {e}")
'''

# Force UTF-8 Write
with open("dashboard/app.py", "w", encoding="utf-8") as f:
    f.write(dashboard_code)

print("Dashboard file rewritten with clean UTF-8 encoding.")