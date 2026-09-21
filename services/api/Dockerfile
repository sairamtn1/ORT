FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY services/api/pyproject.toml /app/pyproject.toml
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir \
      "fastapi>=0.141.1" "uvicorn[standard]>=0.53.0" "sqlalchemy>=2.0.54" \
      "asyncpg>=0.31.0" "pydantic-settings>=2.15.0" "PyJWT>=2.14.0" \
      "pwdlib[argon2]>=0.3.1" "alembic>=1.20.0"
COPY services/api/app /app/app

RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]