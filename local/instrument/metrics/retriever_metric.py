# Read more about OpenTelemetry here:
# https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/fastapi/fastapi.html
import datetime
import os
from io import BytesIO
from time import time

import requests
from fastapi import FastAPI, File, HTTPException, UploadFile
from google.cloud import storage
from google.oauth2 import service_account
from loguru import logger
from opentelemetry import metrics
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.metrics import set_meter_provider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from PIL import Image, UnidentifiedImageError
from pinecone import Pinecone, ServerlessSpec
from prometheus_client import Gauge, Summary, start_http_server


class Config:
    # Config for Pinecone
    INDEX_NAME = "mlops1-project"
    INPUT_RESOLUTION = 768
    PINECONE_CLOUD = "gcp"
    PINECONE_REGION = "us-central1"
    # Config for retriever
    TOP_K = 5
    # Config for GCS
    GCS_BUCKET_NAME = "image-retrieval-bucket-1907"
    # Config for embedding service
    EMBEDDING_SERVICE_URL = os.getenv(
        "EMBEDDING_SERVICE_URL", "http://localhost:5000/embed"
    )


PINECONE_APIKEY = os.environ["PINECONE_APIKEY"]


def get_storage_client():
    json_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if json_path:
        credentials = service_account.Credentials.from_service_account_file(json_path)
        return storage.Client(credentials=credentials)
    return storage.Client()


def get_index(index_name):
    pc = Pinecone(api_key=PINECONE_APIKEY)
    # if index_name in pc.list_indexes().names():
    #     pc.delete_index(index_name)
    #     logger.info(f"Deleted existing Pinecone index: {index_name}")
    if index_name not in pc.list_indexes().names():
        pc.create_index(
            name=index_name,
            metric="cosine",
            dimension=Config.INPUT_RESOLUTION,
            spec=ServerlessSpec(
                cloud=Config.PINECONE_CLOUD, region=Config.PINECONE_REGION
            ),
        )
        logger.info(f"Created Pinecone index: {index_name}")
    return pc.Index(index_name)


def get_feature_vector(image_bytes: bytes) -> list:
    try:
        logger.info(f"Calling embedding service at {Config.EMBEDDING_SERVICE_URL}")
        response = requests.post(
            url=Config.EMBEDDING_SERVICE_URL,
            files={"file": ("image.jpg", image_bytes, "image/jpeg")},
        )
        response.raise_for_status()
        feature = response.json()
        return feature
    except Exception as e:
        logger.error(f"Failed to get feature vector: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get feature vector from embedding service",
        )


def search(index, input_emb, top_k):
    if not input_emb:
        raise ValueError("Input embedding is empty")
    matching = index.query(vector=input_emb, top_k=top_k, include_values=True)[
        "matches"
    ]
    match_ids = [match_id["id"] for match_id in matching]
    return match_ids


index = get_index(Config.INDEX_NAME)

GCS_BUCKET_NAME = Config.GCS_BUCKET_NAME
try:
    storage_client = get_storage_client()
    bucket = storage_client.get_bucket(GCS_BUCKET_NAME)
    if not bucket.exists():
        logger.error(f"Bucket {GCS_BUCKET_NAME} not found in Google Cloud Storage.")
        raise HTTPException(
            status_code=404, detail=f"Bucket {GCS_BUCKET_NAME} not found."
        )

    logger.info(f"Connected to GCS bucket '{GCS_BUCKET_NAME}' successfully")
except Exception as e:
    logger.error(f"Error accessing GCS bucket '{GCS_BUCKET_NAME}': {e}")
    raise HTTPException(status_code=500, detail=str(e))

# Start Prometheus client
start_http_server(port=8097, addr="0.0.0.0")

# Service name is required for most backends
resource = Resource(attributes={SERVICE_NAME: "ingesting-service"})

# Exporter to export metrics to Prometheus
reader = PrometheusMetricReader()

# Meter is responsible for creating and recording metrics
provider = MeterProvider(resource=resource, metric_readers=[reader])
set_meter_provider(provider)
meter = metrics.get_meter("ingesting", "0.1.1")

search_counter = meter.create_counter(
    name="retriever_search_image_counter", description="Number of search_image requests"
)

search_histogram = meter.create_histogram(
    name="retriever_search_image_response_time_seconds",
    description="Response time for search_image requests",
    unit="s",
)

retriever_vector_size_gauge = Gauge(
    "retriever_vector_size",
    "Length of embedding vector returned from embedding service",
)

retriever_response_time_summary = Summary(
    "retriever_response_time_summary_seconds", "Summary of search_image response time"
)

app = FastAPI()


@app.post("/search_image")
async def search_image(file: UploadFile = File(...)):
    try:
        image_bytes = await file.read()
        # Validate image
        try:
            Image.open(BytesIO(image_bytes)).convert("RGB")
        except UnidentifiedImageError:
            raise HTTPException(
                status_code=400, detail="Uploaded file is not a valid image."
            )

        # Embedding
        feature = get_feature_vector(image_bytes)

        # Search
        search_start = time()
        match_ids = search(index, feature, top_k=Config.TOP_K)
        search_elapsed = time() - search_start
        logger.info(f"Search completed in {search_elapsed:.4f} seconds")

        # Metrics
        labels = {"api": "/search_image"}
        search_counter.add(1, labels)
        search_histogram.record(search_elapsed, labels)
        retriever_response_time_summary.observe(search_elapsed)
        retriever_vector_size_gauge.set(len(feature))

        if not match_ids:
            return []

        response = index.fetch(ids=match_ids)
        images_url = []

        for match_id in match_ids:
            if len(images_url) == Config.TOP_K:
                break
            if match_id in response.get("vectors", {}):
                metadata = response["vectors"][match_id].get("metadata", {})
                gcs_path = metadata.get("gcs_path", "")
                blob = bucket.blob(gcs_path)
                if not blob.exists():
                    continue
                signed_url = blob.generate_signed_url(
                    version="v4", expiration=datetime.timedelta(hours=1), method="GET"
                )
                images_url.append(signed_url)

        return images_url

    except Exception as e:
        logger.error(f"Error in image search process: {e}")
        raise HTTPException(
            status_code=400, detail=f"Error in image search process: {e}"
        )
