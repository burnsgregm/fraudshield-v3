from google.cloud import aiplatform

PROJECT_ID = "fraudshield-v3-dev-5320"
REGION = "us-central1"
IMAGE_URI = "us-central1-docker.pkg.dev/fraudshield-v3-dev-5320/fraudshield-repo/hybrid-cpr:v1"
ARTIFACT_URI = "gs://fraudshield-artifacts-dev-fraudshield-v3-dev-5320/v3_hybrid_model/"
ENDPOINT_NAME = "fraudshield-hybrid-endpoint"

aiplatform.init(project=PROJECT_ID, location=REGION)

print("Registering Model (this connects the Image to the Artifacts)...")
model = aiplatform.Model.upload(
    display_name="fraudshield-hybrid-v1",
    artifact_uri=ARTIFACT_URI,
    serving_container_image_uri=IMAGE_URI,
    serving_container_predict_route="/predict",
    serving_container_health_route="/health"
)

print("Fetching Endpoint...")
endpoint = aiplatform.Endpoint.list(filter=f'display_name="{ENDPOINT_NAME}"')[0]

print(f"Deploying Model to Endpoint {endpoint.name} (this takes time)...")
model.deploy(
    endpoint=endpoint,
    machine_type="n1-standard-2",
    min_replica_count=1,
    max_replica_count=1,
    traffic_split={"0": 100}
)
print("Deployment Complete!")
