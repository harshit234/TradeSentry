FROM python:3.12-slim AS builder
WORKDIR /build
COPY pyproject.toml .
COPY models ./models
COPY rules ./rules
COPY dna ./dna
RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.12-slim
RUN useradd --create-home --uid 10001 appuser
WORKDIR /app
COPY --from=builder /install /usr/local
COPY models ./models
COPY rules ./rules
COPY dna ./dna
COPY apps/api ./apps/api
COPY db ./db
COPY scripts ./scripts
COPY fixtures ./fixtures
ENV PYTHONPATH=/app:/app/apps/api
USER appuser
EXPOSE 8000
CMD ["sh", "-c", "alembic -c db/alembic.ini upgrade head && uvicorn tradesentry_api.main:app --host 0.0.0.0 --port 8000"]
