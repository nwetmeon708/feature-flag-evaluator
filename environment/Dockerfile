FROM python:3.11-slim

RUN pip install --no-cache-dir pytest

WORKDIR /app

COPY app/ /app/

ENV PYTHONPATH=/app
