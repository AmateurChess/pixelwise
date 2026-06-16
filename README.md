#PixelWise - DHBW Full-Stack Projekt

# PixelWise – Feature Flags & Downtime Reduction

This repository extends PixelWise (Full Stack Handwerk, Block 4 & 5) with two methods
for zero-downtime model switching. The project report is available in the repository root.

## Methods

**Baseline** – standard uvicorn deployment from the course (systemctl restart, ~1.4s downtime)

**Method 1: Gunicorn Graceful Reload** – Gunicorn with 3 uvicorn workers, SIGHUP-based reload, 0 failed requests

**Method 2: In-Memory Hot Swap** – atomic model swap via threading.Lock, POST endpoint, 0–1 failed requests

## Switch between methods

```bash
cd /opt/pixelwise
bash deploy/switch-method.sh [baseline|gunicorn|hotswap]
```

## Check active method

```bash
bash deploy/status.sh
```

## Swap model at runtime (hotswap only)

```bash
curl -X POST http://localhost:8000/admin/swap-model \
  -H "Content-Type: application/json" \
  -H "x-api-key: <SECRET_API_KEY>" \
  -d '{"model_path": "/opt/pixelwise/models/digit_classifier_v1.pkl"}'
```

## Setup

```bash
bash setup-server.sh
```
Test-Trigger: Tue Jun 16 01:59:35 PM UTC 2026
