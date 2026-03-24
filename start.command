#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

UV_DIR="$ROOT_DIR/.runtime/uv"
UV_BIN="$UV_DIR/uv"
UV_VERSION="0.6.17"

ARCH="$(uname -m)"
if [[ "$ARCH" == "arm64" ]]; then
  UV_PKG="uv-aarch64-apple-darwin.tar.gz"
else
  UV_PKG="uv-x86_64-apple-darwin.tar.gz"
fi
UV_URL="https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/${UV_PKG}"

mkdir -p "$UV_DIR"
if [[ ! -x "$UV_BIN" ]]; then
  echo "[INFO] uv をダウンロードしています..."
  curl -L "$UV_URL" -o "$UV_DIR/uv.tar.gz"
  tar -xzf "$UV_DIR/uv.tar.gz" -C "$UV_DIR"
  if [[ -x "$UV_DIR/uv-${ARCH}-apple-darwin/uv" ]]; then
    cp "$UV_DIR/uv-${ARCH}-apple-darwin/uv" "$UV_BIN"
  elif [[ -x "$UV_DIR/uv-x86_64-apple-darwin/uv" ]]; then
    cp "$UV_DIR/uv-x86_64-apple-darwin/uv" "$UV_BIN"
  elif [[ -x "$UV_DIR/uv-aarch64-apple-darwin/uv" ]]; then
    cp "$UV_DIR/uv-aarch64-apple-darwin/uv" "$UV_BIN"
  fi
  chmod +x "$UV_BIN"
fi

VENV_PY="$ROOT_DIR/.runtime/venv/bin/python"
if [[ ! -x "$VENV_PY" ]]; then
  echo "[INFO] Python 3.11 仮想環境を作成します..."
  "$UV_BIN" venv .runtime/venv --python 3.11
fi

echo "[INFO] 依存関係を同期します..."
"$UV_BIN" pip install --python .runtime/venv/bin/python -r requirements.txt

echo "[INFO] アプリを起動します..."
"$VENV_PY" converter.py --gui
