# FraudShield V3 – Real-Time Transaction Fraud Detection (GCP | Feature Store | Hybrid CPR Model)

FraudShield V3 is an end-to-end **real-time fraud detection system** built on **Google Cloud Platform** with a **Custom Prediction Routine (CPR)** hybrid model, online feature lookups, and a streaming ingestion pipeline.

This version demonstrates **enterprise-grade MLOps patterns**, including:

- **Real-time ingestion:** Pub/Sub → Dataflow (10-minute event-time sliding windows)
- **Online feature serving:** Vertex AI Feature Store
- **Hybrid modeling:** XGBoost (supervised) + Isolation Forest (unsupervised) + ensemble logic
- **Model deployment:** Vertex AI Endpoint + GCS model artifacts
- **Low-latency online scoring:** FastAPI service
- **Offline analytics:** BigQuery (predictions, drift, feature distributions)
- **Infrastructure-as-code:** Terraform modules provisioning all services

---

## 📐 Architecture Diagram (V3)

![Architecture](images/architecture.svg)

---

## 🖼 Demo Screenshots

### **FraudShield Operations Center**
A Streamlit dashboard visualizing predictions, drift signals, score distributions, and system status.

![Ops Dashboard](images/dashboard.png)

### **API Scoring Example**
Example of a real request to the `/v3/score` FastAPI endpoint showing:
- Fraud score  
- Component scores (XGBoost + Isolation Forest)  
- Velocity features reconstructed from Feature Store  

![API Response](images/json.png)

---

## 📁 Repository Structure

```
fraudshield-v3/
│
├── api/                     # FastAPI scoring service
│   ├── app/
│   │   ├── main.py
│   │   └── services/
│   └── Dockerfile
│
├── dashboard/               # Streamlit monitoring UI
│   └── app.py
│
├── streaming/               # Dataflow streaming pipeline
│   ├── generate_stream.py
│   ├── pipeline.py
│   └── requirements.txt
│
├── pipelines/               # Training pipelines
│   └── training/
│       ├── pipeline_definition_v3.py
│       └── components/
│
├── models/                  # Hybrid CPR model
│   ├── train_hybrid.py
│   └── ensemble_cpr/
│       ├── predictor.py
│       ├── requirements.txt
│       └── Dockerfile
│
├── infra/                   # Terraform IaC
│   └── terraform/
│       ├── envs/dev/
│       └── modules/
│
├── monitoring/              # Drift monitoring jobs
│   └── monitoring_job.py
│
├── docs/                    # Versioned design docs
│   ├── MCG - Personal - FraudShield V3.pdf
│   └── SRS+TDD+DM - Personal - FraudShield V3.pdf
│
├── images/                  # Screenshots for README + portfolio
│   ├── dashboard.png
│   └── json.png
│
└── README.md
```

---

## 🚀 Running Locally

### **1. Start the FastAPI Scoring Service**
```bash
uvicorn api.app.main:app --reload --port 8000
```

Then open:

```
http://localhost:8000/docs
```

### **2. Trigger a Test Score**
```bash
curl -X POST "http://localhost:8000/v3/score"      -H "Content-Type: application/json"      -d '{
            "transaction_id": "demo_tx_99",
            "tenant_id": "tenant_A",
            "card_id": "card_1234",
            "amount": 950.0
         }'
```

---

## 📊 What FraudShield Demonstrates

- Real-time ML system design  
- Online feature engineering & serving  
- Hybrid model architecture using CPR  
- End-to-end MLOps with Terraform, monitoring, and retraining  
- Production-style API engineering  

---

## 📎 Supporting Case Study

Full case study (HTML version):  
`docs/Burns_Greg_CS_FraudShield_V3.html`

One-page executive summary:  
`docs/Burns_Greg_CS_1P_FraudShield_V3.pdf`

Architecture diagram:  
`docs/Burns_Greg_CS_FraudShield_V3.svg`

---

## © Credits  
Designed, implemented, and deployed by **Greg Burns**.
