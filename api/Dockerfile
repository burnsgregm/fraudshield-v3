# In directory: fraudshield-v3/api/
cat <<EOF > Dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
# Install system dependency required by numpy/pandas/gRPC libraries
RUN apt-get update && apt-get install -y libgomp1 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
# Environment variable for Cloud Run/FastAPI
ENV PORT=8080
# Run the application (Note: We'd use Cloud Run for deployment)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
EOF