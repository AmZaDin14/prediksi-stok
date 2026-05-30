"""Prediksi Stok — AI-based inventory prediction system."""

from __future__ import annotations

import os

import uvicorn

from app.server import app


def main() -> None:
    port = int(os.environ.get("FASTAPI_PORT", "8765"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
