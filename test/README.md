```bash
docker compose -f test/docker-compose.yaml up -d
```

```bash
pytest test/test_embedding.py -s
pytest test/test_ingesting.py -s
pytest test/test_retriever.py -s
```