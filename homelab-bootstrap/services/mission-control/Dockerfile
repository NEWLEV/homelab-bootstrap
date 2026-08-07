FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mission_control ./mission_control
COPY schemas ./schemas
COPY scripts ./scripts
COPY MISSION_CONTROL.md ./MISSION_CONTROL.md

RUN mkdir -p /data/mission-control \
    && chown -R 65532:65532 /app /data/mission-control

USER 65532:65532

CMD ["uvicorn", "mission_control.app:app", "--host", "0.0.0.0", "--port", "8020"]
