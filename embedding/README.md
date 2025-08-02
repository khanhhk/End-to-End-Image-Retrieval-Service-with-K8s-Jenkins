```bash
# Run
uvicorn main:app --host 0.0.0.0 --port 5000

# Build docker image
docker build -t embedding-service .

# Run docker container
docker run -p 5000:5000 embedding-service
```