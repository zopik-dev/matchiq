# MatchIQ backend — production image (Python 3.12 slim, no GPU needed).
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv/backend

# Install the backend package (runtime deps only: fastapi, pydantic, uvicorn).
COPY backend/pyproject.toml ./
COPY backend/app ./app
RUN pip install --no-cache-dir . uvicorn

# Synthetic samples ship with the image so the demo works with zero setup.
COPY data/samples /srv/data/samples

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
