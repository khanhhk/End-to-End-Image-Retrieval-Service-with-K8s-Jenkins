# Read more about OpenTelemetry here:
# https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/fastapi/fastapi.html
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
import atexit
import datetime
import time
from io import BytesIO

from fastapi import FastAPI, File, HTTPException, UploadFile
from loguru import logger
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Link, get_tracer_provider, set_tracer_provider
from PIL import Image, UnidentifiedImageError
from retriever.config import Config
from retriever.utils import (get_feature_vector, get_index, get_storage_client,
                             search)

set_tracer_provider(
    TracerProvider(resource=Resource.create({SERVICE_NAME: "retriever-service"}))
)
tracer = get_tracer_provider().get_tracer("retriever", "0.1.1")

jaeger_exporter = JaegerExporter(
    agent_host_name="localhost",
    agent_port=6831,
)
span_processor = BatchSpanProcessor(jaeger_exporter)
get_tracer_provider().add_span_processor(span_processor)
atexit.register(span_processor.shutdown)

index = get_index(Config.INDEX_NAME)
GCS_BUCKET_NAME = Config.GCS_BUCKET_NAME

try:
    storage_client = get_storage_client()
    bucket = storage_client.get_bucket(GCS_BUCKET_NAME)
    if not bucket.exists():
        logger.error(f"Bucket {GCS_BUCKET_NAME} not found in GCS")
        raise HTTPException(status_code=404, detail="Bucket not found")
    logger.info(f"Connected to GCS bucket: {GCS_BUCKET_NAME}")
except Exception as e:
    logger.error(f"GCS error: {e}")
    raise HTTPException(status_code=500, detail=str(e))

app = FastAPI()


@app.post("/search_image")
async def search_image(file: UploadFile = File(...)):
    with tracer.start_as_current_span("search_image") as main_span:

        with tracer.start_as_current_span(
            "validate-image", links=[Link(main_span.get_span_context())]
        ):
            image_bytes = await file.read()
            try:
                Image.open(BytesIO(image_bytes)).convert("RGB")
            except UnidentifiedImageError:
                raise HTTPException(
                    status_code=400, detail="Uploaded file is not a valid image."
                )

        with tracer.start_as_current_span(
            "get-feature-vector", links=[Link(main_span.get_span_context())]
        ):
            feature = get_feature_vector(image_bytes)

        with tracer.start_as_current_span(
            "pinecone-search", links=[Link(main_span.get_span_context())]
        ):
            start_time = time.time()
            match_ids = search(index, feature, top_k=Config.TOP_K)
            elapsed = time.time() - start_time
            logger.info(f"Search completed in {elapsed:.4f} seconds")
            if not match_ids:
                return []

        with tracer.start_as_current_span(
            "fetch-from-pinecone", links=[Link(main_span.get_span_context())]
        ):
            response = index.fetch(ids=match_ids)

        images_url = []
        with tracer.start_as_current_span(
            "generate-signed-urls", links=[Link(main_span.get_span_context())]
        ):
            for match_id in match_ids:
                if len(images_url) == Config.TOP_K:
                    break
                if match_id in response.get("vectors", {}):
                    metadata = response["vectors"][match_id].get("metadata", {})
                    gcs_path = metadata.get("gcs_path", "")
                    blob = bucket.blob(gcs_path)
                    if not blob.exists():
                        logger.warning(f"GCS blob not found: {gcs_path}")
                        continue
                    signed_url = blob.generate_signed_url(
                        version="v4",
                        expiration=datetime.timedelta(hours=1),
                        method="GET",
                    )
                    images_url.append(signed_url)
                else:
                    logger.warning(f"Missing vector metadata for ID: {match_id}")

        return images_url
