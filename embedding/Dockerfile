FROM python:3.9-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY embedding/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY ./embedding /app/embedding

EXPOSE 5000

CMD ["uvicorn", "embedding.main:app", "--host", "0.0.0.0", "--port", "5000"]