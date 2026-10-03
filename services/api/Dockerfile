FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY services/api/pyproject.toml /app/pyproject.toml
COPY services/api/app /app/app
COPY services/api/migrations /app/migrations
COPY services/api/alembic.ini /app/alembic.ini
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

CMD ["sh", "-c", "alembic -c /app/alembic.ini upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]