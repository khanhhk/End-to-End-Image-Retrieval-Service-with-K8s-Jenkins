# Read more about OpenTelemetry here:
# https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/fastapi/fastapi.html
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
from embedding.main import extractor, model, DEVICE
import atexit
from io import BytesIO
import torch
from typing import List
from PIL import Image, UnidentifiedImageError
from fastapi import UploadFile, File, HTTPException, FastAPI
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import get_tracer_provider, set_tracer_provider, Link

set_tracer_provider(
    TracerProvider(resource=Resource.create({SERVICE_NAME: "embedding-service"}))
)
tracer = get_tracer_provider().get_tracer("embedding", "0.1.1")

jaeger_exporter = JaegerExporter(
    agent_host_name="localhost",
    agent_port=6831,
)
span_processor = BatchSpanProcessor(jaeger_exporter)
get_tracer_provider().add_span_processor(span_processor)
atexit.register(span_processor.shutdown)

app = FastAPI()

@app.post("/embed", response_model=List[float])
async def embed_image_with_trace(file: UploadFile = File(...)):
    with tracer.start_as_current_span("embedding-request") as request_span:

        with tracer.start_as_current_span("read-image", links=[Link(request_span.get_span_context())]):
            try:
                image_data = await file.read()
                image = Image.open(BytesIO(image_data)).convert("RGB")
            except UnidentifiedImageError:
                raise HTTPException(status_code=400, detail="Uploaded file is not a valid image.")

        with tracer.start_as_current_span("preprocess", links=[Link(request_span.get_span_context())]):
            inputs = extractor(images=image, return_tensors="pt").to(DEVICE)

        with tracer.start_as_current_span("model-inference", links=[Link(request_span.get_span_context())]):
            with torch.no_grad():
                outputs = model(**inputs)
                embedding = outputs.last_hidden_state[:, 0, :]  # CLS token
                vector = embedding.squeeze().cpu().tolist()

    return vector
