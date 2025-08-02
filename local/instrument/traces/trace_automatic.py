# Read more about OpenTelemetry here:
# https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/fastapi/fastapi.html
from io import BytesIO

import easyocr
import numpy as np
from fastapi import FastAPI, File, UploadFile
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import get_tracer_provider, set_tracer_provider
from PIL import Image

set_tracer_provider(
    TracerProvider(resource=Resource.create({SERVICE_NAME: "ocr-service"}))
)
tracer = get_tracer_provider().get_tracer("myocr", "0.1.2")

jaeger_exporter = JaegerExporter(
    agent_host_name="localhost",
    agent_port=6831,
)
span_processor = BatchSpanProcessor(jaeger_exporter)
get_tracer_provider().add_span_processor(span_processor)

app = FastAPI()


@app.post("/ocr")
async def ocr(file: UploadFile = File(...)):
    reader = easyocr.Reader(
        ["vi", "en"],
        gpu=False,
        detect_network="craft",
        model_storage_directory="../model_storage/model",
        download_enabled=False,
    )
    # Read image from route
    request_object_content = await file.read()
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

    return result