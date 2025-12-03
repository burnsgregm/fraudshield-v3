from google.cloud import aiplatform
import os

class ModelEndpointClient:
    def __init__(self, project_id, region, endpoint_name):
        aiplatform.init(project=project_id, location=region)
        endpoints = aiplatform.Endpoint.list(filter=f'display_name="{endpoint_name}"')
        if not endpoints:
            raise RuntimeError(f"Endpoint {endpoint_name} not found in Vertex AI.")
        self.endpoint = endpoints[0]

    def predict(self, feature_vector):
        # Vertex expects [[f1, f2, f3...]]
        prediction = self.endpoint.predict(instances=[feature_vector])
        # XGBoost output is usually [Prob_Class_0, Prob_Class_1] or just Prob_Class_1
        # Depending on the serving container. We assume Prob(Fraud).
        # Adjust logic if the container returns pairs.
        return prediction.predictions[0] 
