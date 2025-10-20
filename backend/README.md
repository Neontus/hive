# FastAPI Backend

Python backend for querying blockchain swap data using HyperSync.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Make sure your `.env` file in the root directory contains:
```
NEXT_PUBLIC_HYPERSYNC_URL=https://sepolia.hypersync.xyz
ENVIO_API_TOKEN=your_token_here
```

## Running the Server

Development mode with auto-reload:
```bash
uvicorn main:app --reload --port 8000
```

Or using Python directly:
```bash
python main.py
```

The API will be available at `http://localhost:8000`

## API Documentation

Once running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Endpoints

### GET /api/swaps
Fetch swap events for a wallet address.

**Query Parameters:**
- `address` (required): Ethereum wallet address
- `fromBlock` (optional): Starting block number (default: 7000000)

**Example:**
```bash
curl "http://localhost:8000/api/swaps?address=0xYourAddress&fromBlock=9000000"
```
