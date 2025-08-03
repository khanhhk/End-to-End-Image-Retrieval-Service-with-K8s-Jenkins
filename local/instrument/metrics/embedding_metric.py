# Read more about OpenTelemetry here:
# https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/fastapi/fastapi.html
from io import BytesIO
from time import time
from typing import List

import torch
from fastapi import FastAPI, File, HTTPException, UploadFile
from opentelemetry import metrics
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.metrics import set_meter_provider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from PIL import Image, UnidentifiedImageError
from prometheus_client import Gauge, Summary, start_http_server
from transformers import ViTImageProcessor, ViTMSNModel

# Load model & extractor
MODEL_NAME = "facebook/vit-msn-base"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

extractor = ViTImageProcessor.from_pretrained(MODEL_NAME)
model = ViTMSNModel.from_pretrained(MODEL_NAME).to(DEVICE)
model.eval()

# Start Prometheus client
start_http_server(port=8099, addr="0.0.0.0")

# Service name is required for most backends
resource = Resource(attributes={SERVICE_NAME: "embedding-service"})

# Exporter to export metrics to Prometheus
reader = PrometheusMetricReader()

# Meter is responsible for creating and recording metrics
provider = MeterProvider(resource=resource, metric_readers=[reader])
set_meter_provider(provider)
meter = metrics.get_meter("embedding", "0.1.1")

embedding_counter = meter.create_counter(
    name="embedding_request_counter", description="Number of embedding requests"
)

embedding_histogram = meter.create_histogram(
    name="embedding_response_time_seconds",
    description="Response time for embedding requests",
    unit="s",
)

embedding_vector_size_gauge = Gauge(
    "embedding_vector_size", "Size (length) of the last embedding vector"
)

embedding_response_time_summary = Summary(
    "embedding_response_time_summary_seconds",
    "Summary of embedding response time",
)

app = FastAPI()


@app.post("/embed", response_model=List[float])
async def embed_image(file: UploadFile = File(...)):
    starting_time = time()
    try:
        image = Image.open(BytesIO(await file.read())).convert("RGB")
    except UnidentifiedImageError:
        raise HTTPException(
            status_code=400, detail="Uploaded file is not a valid image."
        )

    # Preprocess
    inputs = extractor(images=image, return_tensors="pt").to(DEVICE)

    with torch.no_grad():
        outputs = model(**inputs)
        embedding = outputs.last_hidden_state[:, 0, :]
        vector = embedding.squeeze().cpu().tolist()

    elapsed_time = time() - starting_time
    vector_size = len(vector)
    # Labels for all metrics
    label = {"api": "/embed"}

    embedding_counter.add(1, label)
    embedding_histogram.record(elapsed_time, label)
    embedding_response_time_summary.observe(elapsed_time)
    embedding_vector_size_gauge.set(vector_size)

    return vector
