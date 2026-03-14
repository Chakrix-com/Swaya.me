#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="${1:-selenium-arm}"

echo "[info] Installing Indic-capable Noto fonts in container: ${CONTAINER_NAME}"
sudo docker exec -u 0 "${CONTAINER_NAME}" bash -lc "
  mkdir -p /var/lib/apt/lists/partial &&
  apt-get update -qq &&
  apt-get install -y --no-install-recommends \
    fonts-noto-core \
    fonts-noto-extra \
    fonts-noto-cjk \
    fonts-noto-ui-core
"

echo "[info] Verifying key script fonts"
sudo docker exec -u 0 "${CONTAINER_NAME}" bash -lc "
  fc-list | egrep -i 'Noto Sans (Devanagari|Tamil|Telugu|Kannada|Bengali|Gujarati)' | head -n 30
"

echo "[ok] Font setup complete for ${CONTAINER_NAME}"
