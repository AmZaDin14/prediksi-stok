#!/usr/bin/env bash
# Setup Prediksi Stok — one-command initialization and startup.
set -e

cd "$(dirname "$0")"
echo "=== Prediksi Stok — Setup ==="

# --- 1. Check dependencies ---
command -v uv >/dev/null 2>&1 || { echo "Error: uv not found. Install it first."; exit 1; }
command -v node >/dev/null 2>&1 || { echo "Error: node not found. Install it first."; exit 1; }

# --- 2. Install Python dependencies ---
echo "[1/6] Installing Python dependencies..."
uv sync --quiet

# --- 3. Install Node dependencies ---
echo "[2/6] Installing WhatsApp bot dependencies..."
cd whatsapp-bot && npm install --silent && cd ..

# --- 4. Generate synthetic data and train models ---
echo "[3/6] Generating synthetic data and training models..."
uv run python -c "
from app.seeder import seed_synthetic_data
from app.synthetic_data import generate_synthetic_data
from app.predictor import train_all_products
import json, os

DB_PATH = os.environ.get('DB_PATH', 'data/prediksi.db')
PRODUCTS_FILE = os.environ.get('PRODUCTS_FILE', 'products.json')

# Create data directory
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# Seed database with synthetic sales data
seed_synthetic_data(DB_PATH, PRODUCTS_FILE, days=90)

# Load products
with open(PRODUCTS_FILE) as f:
    products = json.load(f)

if products:
    # Train Prophet models
    train_all_products(DB_PATH, PRODUCTS_FILE)
    print(f'Trained {len(products)} product model(s).')
else:
    print('No products found in products.json. Add products via dashboard.')
"

# --- 5. Start FastAPI server ---
echo "[4/6] Starting FastAPI server..."
PORT="${FASTAPI_PORT:-8765}"
DB_PATH="${DB_PATH:-data/prediksi.db}"
PRODUCTS_FILE="${PRODUCTS_FILE:-products.json}"

FASTAPI_PORT=$PORT DB_PATH=$DB_PATH PRODUCTS_FILE=$PRODUCTS_FILE \
    uv run uvicorn app.server:app --host 0.0.0.0 --port $PORT &
FASTAPI_PID=$!
echo "FastAPI server starting (PID: $FASTAPI_PID)..."

# Wait for FastAPI to be ready
for i in $(seq 1 15); do
    if curl -s "http://localhost:$PORT/health" >/dev/null 2>&1; then
        echo "FastAPI server ready on port $PORT."
        break
    fi
    if [ "$i" -eq 15 ]; then
        echo "Warning: FastAPI server may not have started in time."
    fi
    sleep 1
done

# --- 6. Start WhatsApp bot ---
echo "[5/6] Starting WhatsApp bot..."
cd whatsapp-bot
OWNER_NUMBER="${OWNER_NUMBER:-}" node index.js &
BOT_PID=$!
cd ..
echo "WhatsApp bot starting (PID: $BOT_PID)..."

# Wait for QR code
echo "[6/6] Waiting for QR code..."
for i in $(seq 1 30); do
    if [ -f data/qr.png ]; then
        echo "QR code generated! Scan with WhatsApp to connect."
        break
    fi
    if [ -f data/connection_status.json ]; then
        STATUS=$(python3 -c "import json; print(json.load(open('data/connection_status.json')).get('status', ''))")
        if [ "$STATUS" = "connected" ]; then
            echo "WhatsApp already connected!"
            break
        fi
    fi
    sleep 2
done

# --- Summary ---
echo ""
echo "=== Setup Complete ==="
echo ""
echo "FastAPI server:   http://localhost:$PORT"
echo "Dashboard:        streamlit run dashboard.py (run separately)"
echo "WhatsApp bot:     PID $BOT_PID"
echo ""
echo "If QR code was generated, it's saved at: data/qr.png"
echo "Open the dashboard and check 'Status WhatsApp' to see the QR code."
echo ""
echo "To stop: kill $FASTAPI_PID $BOT_PID"
echo "To run dashboard: uv run streamlit run dashboard.py"
