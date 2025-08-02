# Read more about OpenTelemetry here:
# https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/fastapi/fastapi.html
from io import BytesIO

import easyocr
import numpy as np
from loguru import logger
from time import time
from fastapi import FastAPI, File, UploadFile
from opentelemetry import metrics
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.metrics import set_meter_provider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from PIL import Image
from prometheus_client import start_http_server

# Start Prometheus client
start_http_server(port=8099, addr="0.0.0.0")

# Service name is required for most backends
resource = Resource(attributes={SERVICE_NAME: "ocr-service"})

# Exporter to export metrics to Prometheus
reader = PrometheusMetricReader()

# Meter is responsible for creating and recording metrics
provider = MeterProvider(resource=resource, metric_readers=[reader])
set_meter_provider(provider)
meter = metrics.get_meter("myocr", "0.1.2")

# Create your first counter
counter = meter.create_counter(
    name="ocr_request_counter",
    description="Number of OCR requests"
)

histogram = meter.create_histogram(
    name="ocr_response_histogram",
    description="OCR response histogram",
    unit="seconds",
)

app = FastAPI()

@app.post("/ocr")
async def ocr(file: UploadFile = File(...)):
    # Mark the starting point for the response
    starting_time = time()

    reader = easyocr.Reader(
        ["vi", "en"],
        gpu=True,
        detect_network="craft",
        model_storage_directory="./model_storage/model",
        download_enabled=False,
    )

    # Read image from route
    request_object_content = await file.read()

    # time to wait for response
    pil_image = Image.open(BytesIO(request_object_content))

    # Get the detection from EasyOCR
    detection = reader.readtext(pil_image)

    # Create the final result
    result = {"bboxes": [], "texts": [], "probs": []}
    for bbox, text, prob in detection:
        # Convert a list of NumPy int elements to premitive numbers
        bbox = np.array(bbox).tolist()
        result["bboxes"].append(bbox)
        result["texts"].append(text)
        result["probs"].append(prob)

    # Labels for all metrics
    label = {"api": "/ocr"}

    # Increase the counter
    counter.add(10, label)

    # Mark the end of the response
    ending_time = time()
    elapsed_time = ending_time - starting_time

    # Add histogram
    logger.info("elapsed time: ", elapsed_time)
    logger.info(elapsed_time)
    histogram.record(elapsed_time, label)

    return result