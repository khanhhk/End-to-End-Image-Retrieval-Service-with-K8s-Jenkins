# Read more about OpenTelemetry here:
# https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/fastapi/fastapi.html
import datetime
import os
import uuid
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
start_http_server(port=8098, addr="0.0.0.0")

# Service name is required for most backends
resource = Resource(attributes={SERVICE_NAME: "ingesting-service"})

# Exporter to export metrics to Prometheus
reader = PrometheusMetricReader()

# Meter is responsible for creating and recording metrics
provider = MeterProvider(resource=resource, metric_readers=[reader])
set_meter_provider(provider)
meter = metrics.get_meter("ingesting", "0.1.1")

ingesting_counter = meter.create_counter(
    name="ingesting_push_image_counter", description="Number of push_image requests"
)

ingesting_histogram = meter.create_histogram(
    name="ingesting_push_image_response_time_seconds",
    description="Response time for push_image",
    unit="s",
)

vector_size_gauge = Gauge("ingesting_vector_size", "Size of returned vector")
response_time_summary = Summary(
    "ingesting_response_time_summary_seconds", "Summary of response time"
)

app = FastAPI()


@app.post("/push_image")
async def push_image(file: UploadFile = File(...)):
    start_time = time()
    ingesting_counter.add(1, {"api": "/push_image"})
    try:
        image_bytes = await file.read()
        # Check file extension
        ext = file.filename.split(".")[-1].lower()
        if ext not in {"jpg", "jpeg", "png"}:
            raise HTTPException(
                status_code=400, detail="Only .jpg/.jpeg/.png files are allowed."
            )
        # Validate image
        try:
            Image.open(BytesIO(image_bytes)).convert("RGB")
        except UnidentifiedImageError:
            raise HTTPException(
                status_code=400, detail="Uploaded file is not a valid image."
            )
        # Get feature vector from embedding service
        feature = get_feature_vector(image_bytes)
        vector_size_gauge.set(len(feature))

        file_id = str(uuid.uuid4())
        gcs_path = f"images/{file_id}.{ext}"

        # 1. Upload to GCS
        blob = bucket.blob(gcs_path)
        if not blob.exists():
            try:
                blob.upload_from_string(image_bytes, content_type=file.content_type)
                logger.info(f"Uploaded image to GCS successfully: {gcs_path}")
            except Exception as e:
                logger.error(f"Failed to upload image to GCS: {e}")
                raise HTTPException(
                    status_code=500, detail=f"Failed to upload image to GCS: {e}"
                )
        else:
            logger.warning(f"Image already exists: {gcs_path}")

        # 2. Generate signed URL with download name
        response_disposition = f"attachment; filename={file.filename}"
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(hours=1),
            method="GET",
            response_disposition=response_disposition,
        )

        # 3. Upsert to Pinecone
        index.upsert(
            [(file_id, feature, {"gcs_path": gcs_path, "filename": file.filename})]
        )
        logger.info(f"Inserted vector into Pinecone: {file_id}")

        elapsed = time() - start_time
        ingesting_histogram.record(elapsed, {"api": "/push_image"})
        response_time_summary.observe(elapsed)

        return {
            "message": "Successfully!",
            "file_id": file_id,
            "gcs_path": gcs_path,
            "signed_url": signed_url,
        }
    except Exception as e:
        logger.error(f"Error in pushing image: {e}")
        raise HTTPException(status_code=500, detail=f"Error in pushing image: {e}")
