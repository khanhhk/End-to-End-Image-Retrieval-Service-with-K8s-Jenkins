import datetime
import json
import uuid
from io import BytesIO

import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from loguru import logger
from PIL import Image, UnidentifiedImageError

from ingesting.config import Config
from ingesting.utils import get_feature_vector, get_index, get_storage_client

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

app = FastAPI(
    title="Ingesting Service",
    docs_url="/ingesting/docs",
    openapi_url="/ingesting/openapi.json",
)


@app.get("/")
def read_root():
    return {"message": "Welcome to the Image Ingestion API. Visit /docs to test."}


@app.get("/healthz")
def health_check():
    return {"status": "healthy"}


@app.post("/push_image")
async def push_image(file: UploadFile = File(...)):
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

        return {
            "message": "Successfully!",
            "file_id": file_id,
            "gcs_path": gcs_path,
            "signed_url": signed_url,
        }
    except Exception as e:
        logger.error(f"Error in pushing image: {e}")
        raise HTTPException(status_code=500, detail=f"Error in pushing image: {e}")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5001)
