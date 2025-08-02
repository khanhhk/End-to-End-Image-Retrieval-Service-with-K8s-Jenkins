# Read more about OpenTelemetry here:
# https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/fastapi/fastapi.html
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
from ingesting.utils import get_index, get_storage_client, get_feature_vector
from ingesting.config import Config
import atexit
import uuid
import datetime
import json
from loguru import logger
from google.cloud import pubsub_v1
from io import BytesIO
from PIL import Image, UnidentifiedImageError
from fastapi import UploadFile, File, HTTPException, FastAPI
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import get_tracer_provider, set_tracer_provider, Link

set_tracer_provider(
    TracerProvider(resource=Resource.create({SERVICE_NAME: "ingesting-service"}))
)
tracer = get_tracer_provider().get_tracer("ingesting", "0.1.1")

jaeger_exporter = JaegerExporter(
    agent_host_name="localhost",
    agent_port=6831,
)
span_processor = BatchSpanProcessor(jaeger_exporter)
get_tracer_provider().add_span_processor(span_processor)
atexit.register(span_processor.shutdown)

index = get_index(Config.INDEX_NAME)
publisher = pubsub_v1.PublisherClient()
GCS_BUCKET_NAME = Config.GCS_BUCKET_NAME

try:
    storage_client = get_storage_client()
    bucket = storage_client.get_bucket(GCS_BUCKET_NAME)
    if not bucket.exists():
        logger.error(f"Bucket {GCS_BUCKET_NAME} not found in GCS")
        raise HTTPException(status_code=404, detail=f"GCS bucket not found")
    logger.info(f"Connected to GCS bucket: {GCS_BUCKET_NAME}")
except Exception as e:
    logger.error(f"GCS error: {e}")
    raise HTTPException(status_code=500, detail=str(e))

app = FastAPI()

@app.post("/push_image")
async def push_image(file: UploadFile = File(...)):
    with tracer.start_as_current_span("push_image") as push_span:

        with tracer.start_as_current_span("validate-image", links=[Link(push_span.get_span_context())]):
            image_bytes = await file.read()
            ext = file.filename.split(".")[-1].lower()
            if ext not in {"jpg", "jpeg", "png"}:
                raise HTTPException(status_code=400, detail="Only .jpg/.jpeg/.png allowed")
            try:
                Image.open(BytesIO(image_bytes)).convert("RGB")
            except UnidentifiedImageError:
                raise HTTPException(status_code=400, detail="Invalid image file")

        with tracer.start_as_current_span("get-feature-vector", links=[Link(push_span.get_span_context())]):
            feature = get_feature_vector(image_bytes)

        file_id = str(uuid.uuid4())
        gcs_path = f"images/{file_id}.{ext}"

        with tracer.start_as_current_span("upload-to-gcs", links=[Link(push_span.get_span_context())]):
            blob = bucket.blob(gcs_path)
            if not blob.exists():
                try:
                    blob.upload_from_string(image_bytes, content_type=file.content_type)
                    logger.info(f"Uploaded to GCS: {gcs_path}")
                except Exception as e:
                    logger.error(f"GCS upload failed: {e}")
                    raise HTTPException(status_code=500, detail="GCS upload failed")

        with tracer.start_as_current_span("generate-signed-url", links=[Link(push_span.get_span_context())]):
            response_disposition = f"attachment; filename={file.filename}"
            signed_url = blob.generate_signed_url(
                version="v4",
                expiration=datetime.timedelta(hours=1),
                method="GET",
                response_disposition=response_disposition,
            )

        with tracer.start_as_current_span("upsert-to-pinecone", links=[Link(push_span.get_span_context())]):
            index.upsert([(
                file_id,
                feature,
                {"gcs_path": gcs_path, "filename": file.filename}
            )])
            logger.info(f"Upserted vector to Pinecone: {file_id}")

        with tracer.start_as_current_span("publish-pubsub", links=[Link(push_span.get_span_context())]):
            message = {
                "id": file_id,
                "bucket": GCS_BUCKET_NAME,
                "path": gcs_path,
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
            publisher.publish(Config.PUBSUB_TOPIC, json.dumps(message).encode("utf-8"))
            logger.info(f"Published to Pub/Sub: {message}")

        return {
            "message": "Successfully!",
            "file_id": file_id,
            "gcs_path": gcs_path,
            "signed_url": signed_url
        }