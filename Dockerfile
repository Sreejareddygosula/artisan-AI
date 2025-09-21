# Dockerfile for Cloud Run
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

# Cloud Run provides $PORT
ENV PORT=8080

CMD gunicorn -w 2 -b 0.0.0.0:$PORT app:app