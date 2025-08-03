from io import BytesIO
from typing import List

import torch
import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from transformers import ViTImageProcessor, ViTMSNModel

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
        embedding = outputs.last_hidden_state[:, 0, :]  # CLS token
        vector = embedding.squeeze().cpu().tolist()

    return vector


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5000)
