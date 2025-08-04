```bash
# Run
uvicorn main:app --host 0.0.0.0 --port 5000

# Build docker image
docker build -t hoangkimkhanh1907/embedding-service:0.0.14 -f ./embedding/Dockerfile .

# Run docker container
docker run -p 5000:5000 hoangkimkhanh1907/embedding-service:0.0.14
```