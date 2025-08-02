```bash
# Run
uvicorn main:app --host 0.0.0.0 --port 5002

# Build docker image
docker build -t retriever-service .

# Run docker container
docker run --network host --env-file .env -v /home/khanhhk/MLOPS/MLEK3/project_m1/image-retrieval-project-mlops-f9986ebe9e54.json:/secrets/gcp-key.json:ro -p 5002:5002 retriever-service
```