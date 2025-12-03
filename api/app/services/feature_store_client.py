from google.cloud import aiplatform
from google.cloud.aiplatform_v1 import FeaturestoreOnlineServingServiceClient, ReadFeatureValuesRequest
from google.cloud.aiplatform_v1.types import FeatureSelector, IdMatcher

class FeatureStoreClient:
    def __init__(self, project_id, region, fs_id):
        self.project_id = project_id
        self.region = region
        self.fs_id = fs_id
        
        # API Endpoint for Online Serving
        api_endpoint = f"{region}-aiplatform.googleapis.com"
        self.client = FeaturestoreOnlineServingServiceClient(client_options={"api_endpoint": api_endpoint})
        
        # Full path to the Feature Store
        self.fs_path = f"projects/{project_id}/locations/{region}/featurestores/{fs_id}"

    def get_streaming_features(self, card_id: str):
        """
        Fetches real-time velocity features for a card.
        Returns: { 'txn_count_10m': int, 'txn_sum_10m': float }
        """
        entity_type_path = f"{self.fs_path}/entityTypes/cards"
        
        # Select features to read
        feature_selector = FeatureSelector(
            id_matcher=IdMatcher(ids=["txn_count_10m", "txn_sum_10m"])
        )

        try:
            response = self.client.read_feature_values(
                request=ReadFeatureValuesRequest(
                    entity_type=entity_type_path,
                    entity_id=card_id,
                    feature_selector=feature_selector
                )
            )
            
            # Parse response (Vertex returns typed values)
            # Default to 0 if feature is missing (cold start)
            data = response.entity_view.data
            count = 0
            total = 0.0
            
            # Helper to extract value based on type
            for feature in data:
                fid = feature.id.split("/")[-1]
                if fid == "txn_count_10m":
                    count = feature.value.int64_value
                elif fid == "txn_sum_10m":
                    total = feature.value.double_value
            
            return {"txn_count_10m": count, "txn_sum_10m": total}

        except Exception as e:
            print(f"Error fetching features for {card_id}: {e}")
            return {"txn_count_10m": 0, "txn_sum_10m": 0.0}
