import atexit
import datetime
import time
from io import BytesIO

import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from loguru import logger
from opentelemetry import metrics
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.metrics import set_meter_provider
from opentelemetry.sdk.metrics import MeterProvider
from prometheus_client import Gauge, Summary, start_http_server
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
    agent_host_name="jaeger-tracing-jaeger-all-in-one.tracing.svc.cluster.local",
    agent_port=6831,
)
span_processor = BatchSpanProcessor(jaeger_exporter)
get_tracer_provider().add_span_processor(span_processor)
atexit.register(span_processor.shutdown)

index = get_index(Config.INDEX_NAME)
logger.info(f"Pinecone index: {Config.INDEX_NAME}")

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

app = FastAPI(
    title="Retriever Service",
    docs_url="/retriever/docs",
    openapi_url="/retriever/openapi.json",
)


@app.get("/")
def read_root():
    return {"message": "Welcome to the Image Retriever API. Visit /docs to test."}


@app.get("/healthz")
def health_check():
    return {"status": "OK!"}


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
            search_start = time()
            match_ids = search(index, feature, top_k=Config.TOP_K)
            search_elapsed = time() - search_start
            logger.info(f"Search completed in {search_elapsed:.4f} seconds")
            labels = {"api": "/search_image"}
            search_counter.add(1, labels)
            search_histogram.record(search_elapsed, labels)
            retriever_response_time_summary.observe(search_elapsed)
            retriever_vector_size_gauge.set(len(feature))
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


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5002)
