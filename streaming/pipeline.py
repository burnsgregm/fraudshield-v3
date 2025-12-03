import argparse
import json
import logging
from datetime import datetime

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, GoogleCloudOptions, StandardOptions
from apache_beam.transforms.trigger import AfterWatermark, AfterProcessingTime, AccumulationMode
from apache_beam.transforms.window import SlidingWindows
from google.cloud import aiplatform

# --- Configuration ---
PROJECT_ID = "fraudshield-v3-dev-5320"
REGION = "us-central1"
FEATURE_STORE_ID = "fraudshield_feature_store_dev"
SUBSCRIPTION_ID = "projects/fraudshield-v3-dev-5320/subscriptions/fraudshield-raw-sub"

ALLOWED_LATENESS_SECONDS = 300  # 5 minutes
WINDOW_SIZE_SECONDS = 600       # 10 minutes
WINDOW_PERIOD_SECONDS = 60      # 1 minute

class ParseAndTimestamp(beam.DoFn):
    def process(self, element):
        try:
            record = json.loads(element.decode("utf-8"))
            event_ts = record.get("timestamp")
            if event_ts:
                dt = datetime.fromisoformat(event_ts.replace("Z", "+00:00"))
                yield beam.window.TimestampedValue(record, dt.timestamp())
        except Exception as e:
            logging.error(f"Parse error: {e}")

class ExtractKey(beam.DoFn):
    def process(self, element):
        tenant = element.get("tenant_id", "default")
        card = element.get("card_id", "unknown")
        key = f"{tenant}#{card}"
        yield (key, element)

class WriteToFeatureStore(beam.DoFn):
    def __init__(self, project, region, fs_id):
        self.project = project
        self.region = region
        self.fs_id = fs_id

    def setup(self):
        aiplatform.init(project=self.project, location=self.region)
        self.fs = aiplatform.Featurestore(featurestore_name=self.fs_id)
        self.entity = self.fs.get_entity_type("cards")

    def process(self, element, window=beam.DoFn.WindowParam):
        key, agg = element
        _, card_id = key.split("#")
        ts = window.end.to_utc_datetime()
        try:
            self.entity.write_feature_values(
                entity_id=card_id,
                feature_values={
                    "txn_count_10m": int(agg["count"]),
                    "txn_sum_10m": float(agg["sum"])
                },
                feature_time=ts
            )
            logging.info(f"Updated {key} @ {ts}: {agg}")
        except Exception as e:
            logging.error(f"Failed to write {key}: {e}")

def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--job_name", required=True)
    parser.add_argument("--runner", default="DataflowRunner")
    parser.add_argument("--temp_location", required=True)
    args, beam_args = parser.parse_known_args()

    options = PipelineOptions(beam_args)
    google_opts = options.view_as(GoogleCloudOptions)
    google_opts.project = PROJECT_ID
    google_opts.region = REGION
    google_opts.job_name = args.job_name
    google_opts.temp_location = args.temp_location
    google_opts.staging_location = args.temp_location
    
    # Force Dataflow Runner
    options.view_as(StandardOptions).runner = "DataflowRunner"
    options.view_as(StandardOptions).streaming = True

    with beam.Pipeline(options=options) as p:
        (
            p
            | "Read" >> beam.io.ReadFromPubSub(subscription=SUBSCRIPTION_ID)
            | "Parse" >> beam.ParDo(ParseAndTimestamp())
            | "Key" >> beam.ParDo(ExtractKey())
            | "Window" >> beam.WindowInto(
                SlidingWindows(WINDOW_SIZE_SECONDS, WINDOW_PERIOD_SECONDS),
                trigger=AfterWatermark(early=AfterProcessingTime(10), late=AfterProcessingTime(1)),
                accumulation_mode=AccumulationMode.ACCUMULATING,
                allowed_lateness=ALLOWED_LATENESS_SECONDS
            )
            | "Aggregate" >> beam.CombinePerKey(lambda x: {"count": len(x), "sum": sum(i["amount"] for i in x)})
            | "Write" >> beam.ParDo(WriteToFeatureStore(PROJECT_ID, REGION, FEATURE_STORE_ID))
        )

if __name__ == "__main__":
    run()
