import atexit
from io import BytesIO
from typing import List

import torch
import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import get_tracer_provider, set_tracer_provider
from PIL import Image, UnidentifiedImageError
from transformers import ViTImageProcessor, ViTMSNModel

set_tracer_provider(
    TracerProvider(resource=Resource.create({SERVICE_NAME: "embedding-service"}))
)
tracer = get_tracer_provider().get_tracer("embedding", "0.1.1")
jaeger_exporter = JaegerExporter(
    agent_host_name="jaeger-tracing-jaeger-all-in-one.tracing.svc.cluster.local",
    agent_port=6831,
)
span_processor = BatchSpanProcessor(jaeger_exporter)
get_tracer_provider().add_span_processor(span_processor)
atexit.register(span_processor.shutdown)

# Load model & extractor
MODEL_NAME = "facebook/vit-msn-base"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

extractor = ViTImageProcessor.from_pretrained(MODEL_NAME)
model = ViTMSNModel.from_pretrained(MODEL_NAME).to(DEVICE)
model.eval()

# FastAPI app
app = FastAPI(title="ViT-MSN Embedding Service")


@app.get("/")
def read_root():
    return {"message": "Welcome to ViT-MSN Embedding API. Visit /docs to test."}


@app.get("/healthz")
def health_check():
    return {"status": "healthy"}


@app.post("/embed", response_model=List[float])
async def embed_image(file: UploadFile = File(...)):
    with tracer.start_as_current_span("embed_image") as span:
        try:
            span.set_attribute("file_name", file.filename)
            span.set_attribute("content_type", file.content_type)

            with tracer.start_as_current_span("load_image"):
                image = Image.open(BytesIO(await file.read())).convert("RGB")

        except UnidentifiedImageError:
            span.record_exception(Exception("Invalid image format"))
            raise HTTPException(
                status_code=400, detail="Uploaded file is not a valid image."
            )

        # Preprocess
        with tracer.start_as_current_span("preprocess_image"):
            inputs = extractor(images=image, return_tensors="pt").to(DEVICE)

        # Inference
        with tracer.start_as_current_span("model_inference"):
            with torch.no_grad():
                outputs = model(**inputs)
                embedding = outputs.last_hidden_state[:, 0, :]  # CLS token
                vector = embedding.squeeze().cpu().tolist()

        span.set_attribute("vector_length", len(vector))

    return vector


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5000)
