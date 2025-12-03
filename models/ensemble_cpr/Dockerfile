FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY predictor.py .
# The base image logic is handled by Vertex AI's CPR helper usually, 
# but for custom builds we define the entrypoint via the SDK deployment.
