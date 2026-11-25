FROM python:3.11-slim

# ── env ──────────────────────────────────────────────
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=Asia/Dhaka

WORKDIR /app

# ── system packages ─────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        tzdata \
    && rm -rf /var/lib/apt/lists/*

# ── python deps (cache layer) ───────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── app code ────────────────────────────────────────
COPY . .

# data folder (token_cache.json, devices.json এখানে যাবে)
RUN mkdir -p /app/data

# Railway $PORT দেয়; VPS-এ ডিফল্ট 5018
ENV PORT=5018
EXPOSE 5018

# ── healthcheck ─────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT}/" || exit 1

# ── run ─────────────────────────────────────────────
CMD ["python", "-u", "app.py"]