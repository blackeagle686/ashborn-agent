# ── Ashborn Landing Page — Docker Image ───────────────────────────────────
# Multi-stage build for minimal final image size
# ──────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --target=/app/deps -r requirements.txt

# ── Production image ─────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Copy installed dependencies
COPY --from=builder /app/deps /app/deps
ENV PYTHONPATH="/app/deps"

# Copy application
COPY app.py .
COPY static/ static/

EXPOSE 3000

CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "3000"]
