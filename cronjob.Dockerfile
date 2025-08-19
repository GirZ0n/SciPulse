FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app:/app/lib:/app/packages

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY lib/requirements.txt /app/lib/requirements.txt
RUN pip install -r /app/lib/requirements.txt

COPY . /app

CMD ["python","packages/bot/post_papers/__main__.py"]