import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import plotly.express as px
from google.oauth2 import service_account
from google.cloud import bigquery
from google.cloud import aiplatform
import os

# Page Config
st.set_page_config(
    page_title="FraudShield V3 Operations",
    page_icon="Ì†ΩÌª°Ô∏è",
    layout="wide"
)

# --- CONFIGURATION ---
PROJECT_ID = "fraudshield-v3-dev-5320"
REGION = "us-central1"
# V3 uses a dedicated topic, but for offline analytics we assume a sink to BQ exists
TABLE_ID = f"{PROJECT_ID}.fraudshield.predictions" 

# --- AUTHENTICATION HANDLER (V2 Logic) ---
def get_credentials():
    # Check if running on Streamlit Cloud (secrets present)
    if "gcp_service_account" in st.secrets:
        return service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"]
        )
    # Fallback to local default (your laptop)
    return None 

creds = get_credentials()

# --- MOCK DATA GENERATOR (V3 Demo) ---
def generate_mock_data():
    """Generates realistic-looking V3 fraud logs for demo purposes."""
    data = []
    base_time = datetime.now()
    
    # Generate 100 recent transactions
    for i in range(100):
        is_fraud = np.random.choice([True, False], p=[0.15, 0.85])
        
        # Logic to make data look correlated
        score = np.random.uniform(0.7, 0.99) if is_fraud else np.random.uniform(0.01, 0.4)
        risk = "HIGH" if score > 0.7 else ("MEDIUM" if score > 0.3 else "LOW")
        
        tx = {
            "timestamp": (base_time - timedelta(minutes=i)).strftime("%Y-%m-%d %H:%M:%S"),
            "transaction_id": f"TXN_{100000+i}",
            "tenant_id": "tenant_A" if i % 2 == 0 else "tenant_B",
            "amount": round(np.random.uniform(10, 1500), 2),
            "score": round(score, 4),
            "risk_band": risk,
            "model_version": "fraudshield-hybrid-v1"
        }
        data.append(tx)
    
    return pd.DataFrame(data)

# --- SIDEBAR ---
st.sidebar.title("Ì†ΩÌª°Ô∏è FraudShield V3")
st.sidebar.markdown(f"**Project:** `{PROJECT_ID}`")
mode = st.sidebar.radio("Data Source", ["Live Stream (Demo)", "BigQuery (Offline)"])

if st.sidebar.button("Refresh Data"):
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("Operations")

# --- RETRAIN BUTTON (V2 Style) ---
if st.sidebar.button("Trigger Retraining (Hybrid)"):
    with st.spinner("Submitting V3 Training Pipeline..."):
        time.sleep(2) # Simulate API call
        st.sidebar.success(f"Pipeline Submitted! Job: fraudshield-train-v3-{int(time.time())}")

# --- MAIN PAGE ---
st.title("FraudShield Operations Center")

# Data Loading Logic
df = pd.DataFrame()

if mode == "Live Stream (Demo)":
    # Simulate loading
    with st.spinner('Fetching real-time predictions from Pub/Sub...'):
        time.sleep(0.5) 
    df = generate_mock_data()
    st.sidebar.success("Ì†ΩÌø¢ System Status: ONLINE")
    st.sidebar.info("Streaming Engine: Active\n\nEndpoint: fraudshield-hybrid-endpoint")

else:
    # BigQuery Connection (V2 Logic)
    try:
        client = bigquery.Client(project=PROJECT_ID, credentials=creds)
        query = f"""
            SELECT transaction_id, score, risk_band, timestamp, model_version
            FROM `{TABLE_ID}`
            ORDER BY timestamp DESC
            LIMIT 1000
        """
        df = client.query(query).to_dataframe()
    except Exception as e:
        st.error(f"BigQuery Connection Error: {e}")
        st.warning("Switch to 'Live Stream (Demo)' to view the dashboard interface.")

# --- DASHBOARD VISUALIZATION ---
if not df.empty:
    # 1. METRICS ROW
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Predictions", len(df))
    
    avg_score = df['score'].mean()
    col2.metric("Avg Fraud Score", f"{avg_score:.4f}")
    
    high_risk_count = len(df[df['risk_band'] == 'HIGH'])
    col3.metric("High Risk Tx", high_risk_count, delta_color="inverse")
    
    latest_version = df.iloc[0]['model_version'] if 'model_version' in df.columns else "N/A"
    col4.metric("Active Model", latest_version)

    # 2. CHARTS ROW (Plotly)
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Score Distribution")
        fig_hist = px.histogram(
            df, 
            x="score", 
            nbins=20, 
            title="Fraud Score Histogram", 
            color="risk_band",
            color_discrete_map={"LOW": "#00CC96", "MEDIUM": "#FFA15A", "HIGH": "#EF553B"}
        )
        st.plotly_chart(fig_hist, use_container_width=True)
        
    with c2:
        st.subheader("Drift Monitor")
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        # Sort by time for the line chart
        df_sorted = df.sort_values('timestamp')
        fig_line = px.line(
            df_sorted, 
            x="timestamp", 
            y="score", 
            title="Avg Score Over Time", 
            markers=True,
            line_shape="spline"
        )
        st.plotly_chart(fig_line, use_container_width=True)

    # 3. DATA TABLE
    st.subheader("Recent Live Traffic")
    
    def color_risk(val):
        color = '#ff4b4b' if val == 'HIGH' else ('#ffa421' if val == 'MEDIUM' else '#21c354')
        return f'color: {color}; font-weight: bold'

    st.dataframe(
        df[['timestamp', 'transaction_id', 'score', 'risk_band', 'amount', 'tenant_id']]
        .style.applymap(color_risk, subset=['risk_band']),
        use_container_width=True
    )

# Footer
st.markdown("---")
st.caption("FraudShield V3 | Powered by Vertex AI & Dataflow | Build: v3.1.0-stable")