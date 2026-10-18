FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

RUN useradd --create-home civicon \
    && mkdir -p /tmp/civicon-uploads \
    && chown -R civicon:civicon /tmp/civicon-uploads

USER civicon
ENV CIVICON_UPLOAD_DIR=/tmp/civicon-uploads

# Cloud Run injects PORT=8080; default matches Cloud Run when env is unset locally.
ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
