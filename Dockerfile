# Growth OS: one container serving the API and the built web app on port 8000.
#   docker compose up --build        then open http://localhost:8000

# --- Build the React app ---------------------------------------------------
FROM node:22-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# --- Python runtime --------------------------------------------------------
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    SEED_ON_START=1

WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
# FastAPI serves ../frontend/dist relative to the backend folder.
COPY --from=frontend /app/frontend/dist /app/frontend/dist

RUN useradd --create-home --uid 10001 growthos && chown -R growthos /app
USER growthos

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/api/health')"

# SEED_ON_START=1 loads fresh demo data on every start (set 0 to keep data).
CMD ["sh", "-c", "if [ \"$SEED_ON_START\" = \"1\" ]; then python -m app.seed; fi; exec uvicorn app.main:app --host 0.0.0.0 --port \"$PORT\""]
