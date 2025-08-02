### Traces

#### Automatic tracing

```shell
opentelemetry-instrument uvicorn trace_automatic:app
```
#### Manual tracing

```shell
uvicorn trace_manual:app
```

### Logs

Run ELK stack with `Filebeat`
```shell
cd elk
docker compose -f elk-docker-compose.yml -f extensions/filebeat/filebeat-compose.yml up -d
```

Quickly run a container so that `Filebeat` can collect logs from it
```shell
cd instrument
docker build -t foo -f logs/Dockerfile . && docker run -p 8000:8000 --name demo-logs foo
```

### Metrics
Run the OCR app to demonstrate metrics
```shell
cd instrument
docker build -t foo-metrics -f metrics/Dockerfile . && docker run -p 8000:8000 --name demo-metrics foo-metrics
```

Open another terminal to call the OCR endpoint periodically
```shell
cd instrument/metrics
python client.py
```

Now execute the following query `ocr_request_counter_total` in Prometheus at `http://localhost:9090`