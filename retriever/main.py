import datetime
import time
from io import BytesIO

import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from loguru import logger
from PIL import Image, UnidentifiedImageError

from retriever.config import Config
from retriever.utils import (get_feature_vector, get_index, get_storage_client,
                             search)

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
    try:
        image_bytes = await file.read()
        # Validate image
        try:
            Image.open(BytesIO(image_bytes)).convert("RGB")
        except UnidentifiedImageError:
            raise HTTPException(
                status_code=400, detail="Uploaded file is not a valid image."
            )

        # Get feature vector from embedding service
        feature = get_feature_vector(image_bytes)

        start_time = time.time()
        match_ids = search(index, feature, top_k=Config.TOP_K)
        elapsed_time = time.time() - start_time
        logger.info(f"Search completed in {elapsed_time:.4f} seconds")
        if not match_ids:
            logger.warning("No match IDs found from Pinecone search.")
            return []
        response = index.fetch(ids=match_ids)

        images_url = []
        for match_id in match_ids:
            if len(images_url) == Config.TOP_K:
                break
            if match_id in response.get("vectors", {}):
                metadata = response["vectors"][match_id].get("metadata", {})
                gcs_path = metadata.get("gcs_path", "")
                blob = bucket.blob(gcs_path)
                if not blob.exists():
                    logger.warning(
                        f"Image with GCS path {gcs_path} does not exist in bucket."
                    )
                    continue
                signed_url = blob.generate_signed_url(
                    version="v4", expiration=datetime.timedelta(hours=1), method="GET"
                )
                images_url.append(signed_url)
                logger.info(f"Found URL for match ID {match_id}")
            else:
                logger.warning(f"Match ID {match_id} not found in response.")
        return images_url
    except Exception as e:
        logger.error(f"Error in image search process: {e}")
        raise HTTPException(
            status_code=400, detail=f"Error in image search process: {e}"
        )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5002)
