```bash
# Run
uvicorn main:app --host 0.0.0.0 --port 5002

# Build docker image
docker build -t hoangkimkhanh1907/retriever-service:0.0.15 -f ./retriever/Dockerfile .
# Run docker container
docker run --network host --env-file ./retriever/.env -v /home/hkk1907/VNPT/ad/image-retrieval-project-mlops-f9986ebe9e54.json:/secrets/gcp-key.json:ro -p 5002:5002 hoangkimkhanh1907/retriever-service:0.0.15
```