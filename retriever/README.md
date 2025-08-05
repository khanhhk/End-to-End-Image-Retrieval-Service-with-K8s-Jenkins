```bash
# Run
uvicorn main:app --host 0.0.0.0 --port 5002

# Build docker image
docker build -t hoangkimkhanh1907/retriever-service:0.0.24 -f ./retriever/Dockerfile .
# Run docker container
docker run --network host --env-file ./retriever/.env -v /home/khanhhk/MLOPS/MLEK3/project/image-retrieval-project-mlops-f9986ebe9e54.json:/secrets/gcp-key.json:ro -p 5002:5002 hoangkimkhanh1907/retriever-service:0.0.24
```