# Intelix batch client — minimal Python image, non-root user, unbuffered logs.
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

# Default scan dir; mount a host directory at /app/files for real inputs (see README).
RUN mkdir -p /app/files /app/reports /app/logs

RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

# Extra CLI args append after this (e.g. `docker run … image --max-per-type 5`).
ENTRYPOINT ["python", "src/main.py"]
CMD []
