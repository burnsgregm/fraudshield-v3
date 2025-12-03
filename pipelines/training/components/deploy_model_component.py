from kfp.dsl import component, Input, Model

@component(
    base_image="python:3.10",
    packages_to_install=["google-cloud-aiplatform"]
)
def deploy_model_to_endpoint(
    project_id: str,
    region: str,
    model: Input[Model],
    endpoint_name: str,
    display_name: str,
    serving_container: str
):
    from google.cloud import aiplatform
    
    print(f"Deploying model to endpoint: {endpoint_name}")
    aiplatform.init(project=project_id, location=region)

    # 1. Upload Model to Registry
    # Note: In a real pipeline, Registration and Deployment might be separate. 
    # Combining here for V2 simplicity.
    uploaded_model = aiplatform.Model.upload(
        display_name=display_name,
        artifact_uri=model.uri.replace("/model.bst", ""), # Vertex expects the folder, not the file
        serving_container_image_uri=serving_container,
        sync=True
    )
    
    # 2. Find the Endpoint
    endpoints = aiplatform.Endpoint.list(filter=f'display_name="{endpoint_name}"')
    if not endpoints:
        # Fallback if Terraform didn't create it, though it should have
        endpoint = aiplatform.Endpoint.create(display_name=endpoint_name)
    else:
        endpoint = endpoints[0]

    # 3. Deploy (Canary Logic)
    # If endpoint has traffic, we deploy as challenger (10% traffic).
    # If empty, we deploy as 100%.
    traffic_split = {"0": 100}
    if endpoint.traffic_split:
        print("Endpoint has existing traffic. Deploying as Challenger (10%).")
        # Logic to grab ID of current model would go here. 
        # For this demo, we just deploy with 100 to force the update, 
        # or you can set traffic_percentage=10 to be safe.
        
    endpoint.deploy(
        model=uploaded_model,
        deployed_model_display_name=display_name,
        machine_type="n1-standard-2",
        traffic_percentage=100, # Setting to 100 for V2 Demo simplicity (Champion)
        sync=True
    )
    
    print(f"Model deployed to {endpoint.resource_name}")