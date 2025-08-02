from time import sleep

import requests
from loguru import logger

def predict():
    logger.info("Sending POST requests!")
    files = {
        "file": open("./examples/receipt.jpg", "rb"),
    }
    response = requests.post(
        "http://localhost:8000/ocr",
        headers={
            "accept": "application/json",
        },
        files=files,
    )


if __name__ == "__main__":
    while True:
        predict()
        sleep(0.5)
