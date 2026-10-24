# Backend: Python 3.11 (main) + Node 22 for chrome-devtools-mcp (browser spike, Phase 2).
FROM node:22-bookworm-slim AS node

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    CHROME_DEVTOOLS_MCP_NO_USAGE_STATISTICS=1 \
    FIREBASE_SERVICE_ACCOUNT=/app/firebase-service-account.json

COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
    && npm install --global chrome-devtools-mcp@1.10.1 \
    && npm cache clean --force

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --retries 10 --timeout 60 -r requirements.txt
COPY . .

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=5 CMD \
    python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/market/health', timeout=3)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
