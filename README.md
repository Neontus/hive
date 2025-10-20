# Hive - Generate Signals w/ Tipping

A Web3 dApp built with Next.js, RainbowKit, wagmi, and a Python FastAPI backend for querying blockchain swap data.

## Architecture

- **Frontend**: Next.js with TypeScript, RainbowKit, and wagmi
- **Backend**: FastAPI (Python) for blockchain data queries via HyperSync
- **Network**: Base Sepolia testnet

## Quick Start

### 1. Setup Environment

Copy the example environment file and add your API tokens:

```bash
cp .env.example .env
```

Edit `.env` and add your tokens:
- `ENVIO_API_TOKEN`: Get from https://envio.dev/app/api-tokens
- `NEXT_PUBLIC_HYPERSYNC_URL`: HyperSync endpoint (default: https://sepolia.hypersync.xyz)
- `NEXT_PUBLIC_API_URL`: FastAPI backend URL (default: http://localhost:8000)

### 2. Start the Backend (Python FastAPI)

```bash
cd backend
./start.sh
```

Or manually:
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The backend will run on http://localhost:8000

### 3. Start the Frontend (Next.js)

In a new terminal:

```bash
yarn install
yarn dev
```

The frontend will run on http://localhost:3000

## Development

- Frontend development: `yarn dev`
- Backend development: `cd backend && uvicorn main:app --reload`
- Backend API docs: http://localhost:8000/docs

## Project Structure

```
├── backend/              # FastAPI Python backend
│   ├── main.py          # Main API server
│   ├── requirements.txt # Python dependencies
│   └── start.sh         # Startup script
├── src/
│   ├── pages/           # Next.js pages
│   ├── hooks/           # React hooks
│   ├── types/           # TypeScript types
│   └── wagmi.ts         # Wagmi configuration
└── ...
```