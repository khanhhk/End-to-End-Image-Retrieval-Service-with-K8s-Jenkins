import os
import requests
from pinecone import Pinecone, ServerlessSpec
from loguru import logger
from fastapi import HTTPException
from google.cloud import storage
from google.oauth2 import service_account
from config import Config

PINECONE_APIKEY = os.environ["PINECONE_APIKEY"]

def get_storage_client():
    json_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if json_path:
        credentials = service_account.Credentials.from_service_account_file(json_path)
        return storage.Client(credentials=credentials)
    return storage.Client()

def get_index(index_name):
    pc = Pinecone(api_key=PINECONE_APIKEY)
    # if index_name in pc.list_indexes().names():
    #     pc.delete_index(index_name)
    #     logger.info(f"Deleted existing Pinecone index: {index_name}")
    if index_name not in pc.list_indexes().names():
        pc.create_index(
            name=index_name,
            metric="cosine",
            dimension=Config.INPUT_RESOLUTION,
            spec=ServerlessSpec(
                cloud = Config.PINECONE_CLOUD,
                region = Config.PINECONE_REGION
            )
        )
        logger.info(f"Created Pinecone index: {index_name}")
    return pc.Index(index_name)

def get_feature_vector(image_bytes: bytes) -> list:
    try:
        logger.info(f"Calling embedding service at {Config.EMBEDDING_SERVICE_URL}")
        response = requests.post(
            url=Config.EMBEDDING_SERVICE_URL,
            files={"file": ("image.jpg", image_bytes, "image/jpeg")}
        )
        response.raise_for_status()
        feature = response.json()
        return feature 
    except Exception as e:
        logger.error(f"Failed to get feature vector: {e}")
        raise HTTPException(status_code=500, detail="Failed to get feature vector from embedding service")

def search(index, input_emb, top_k):
    if not input_emb:
        raise ValueError("Input embedding is empty")
    matching = index.query(vector=input_emb, top_k=top_k, include_values=True)[
        "matches"
    ]
    match_ids = [match_id["id"] for match_id in matching]
    return match_ids

