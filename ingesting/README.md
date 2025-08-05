```bash
# Run
uvicorn main:app --host 0.0.0.0 --port 5001

# Build docker image
docker build -t hoangkimkhanh1907/ingesting-service:0.0.18 -f ./ingesting/Dockerfile .

# Run docker container
docker run --network host --env-file ./ingesting/.env -v /home/hkk1907/VNPT/ad/image-retrieval-project-mlops-f9986ebe9e54.json:/secrets/gcp-key.json:ro -p 5001:5001 hoangkimkhanh1907/ingesting-service:0.0.18
```