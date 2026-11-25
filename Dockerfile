FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && addgroup --system app \
    && adduser --system --ingroup app app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY data/.gitkeep ./data/.gitkeep
COPY storage/snapshots/.gitkeep ./storage/snapshots/.gitkeep

RUN mkdir -p /app/data /app/storage/snapshots \
    && chown -R app:app /app

USER app

EXPOSE 8000

CMD ["sh", "-c", "python -m app.db.seed && exec uvicorn app.main:app --host 0.0.0.0 --port \"${PORT:-8000}\""]
