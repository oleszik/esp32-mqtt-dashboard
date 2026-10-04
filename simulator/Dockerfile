FROM python:3.12.10-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml ./
COPY simulator ./simulator
RUN pip install --no-cache-dir . && useradd --create-home --uid 10001 simulator
USER simulator
ENTRYPOINT ["python", "-m", "simulator"]

