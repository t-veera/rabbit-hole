FROM python:3.12-slim

# tesseract-ocr: OCR fallback for scanned PDF uploads with no text layer
# (services/fulltext.py's extract_text_for_upload). Everything else in the
# app works without it — this is the one dependency that needs an OS
# package, not just a pip install, so it has to be baked in here rather
# than left to requirements.txt.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8420

CMD ["sh", "-c", "python -m alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8420"]
