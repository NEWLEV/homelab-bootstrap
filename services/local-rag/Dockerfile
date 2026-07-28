FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

RUN mkdir -p /data/chroma \
    && chown -R 65532:65532 /app /data/chroma

USER 65532:65532

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
