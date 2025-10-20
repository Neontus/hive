"""
FastAPI Backend for HyperSync Swap Data
Provides API endpoints for querying swap events from blockchain data
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv
import re
import hypersync

# Load environment variables
load_dotenv()

# HyperSync configuration
HYPERSYNC_URL = os.getenv("NEXT_PUBLIC_HYPERSYNC_URL", "https://sepolia.hypersync.xyz")
ENVIO_API_TOKEN = os.getenv("ENVIO_API_TOKEN")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize HyperSync client on startup and clean up on shutdown"""
    # Startup: Initialize client once
    app.state.hypersync_client = hypersync.HypersyncClient(
        hypersync.ClientConfig(
            url=HYPERSYNC_URL,
            bearer_token=ENVIO_API_TOKEN
        )
    )
    yield
    # Shutdown: cleanup if needed
    app.state.hypersync_client = None

app = FastAPI(title="HyperSync Swap API", version="1.0.0", lifespan=lifespan)

# Configure CORS to allow Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALL_CONTRACT_ADDRESSES = [
    "0xE03A1074c86CFeDd5C142C4F04F1a1536e203543",  # Sepolia PoolManager
]


def validate_ethereum_address(address: str) -> bool:
    """Validate Ethereum address format"""
    pattern = r"^0x[a-fA-F0-9]{40}$"
    return bool(re.match(pattern, address))


def serialize_hypersync_data(data):
    """
    Convert HyperSync data to JSON-serializable format
    Handles nested objects, lists, and large integers
    """
    if data is None:
        return None
    elif isinstance(data, (str, bool, type(None))):
        return data
    elif isinstance(data, int):
        # Convert large integers to strings to avoid precision loss in JSON
        return str(data) if data > 2**53 - 1 or data < -(2**53 - 1) else data
    elif isinstance(data, bytes):
        # Convert bytes to hex string with 0x prefix
        return '0x' + data.hex() if data else None
    elif isinstance(data, list):
        return [serialize_hypersync_data(item) for item in data]
    elif isinstance(data, dict):
        return {k: serialize_hypersync_data(v) for k, v in data.items()}
    elif hasattr(data, '__dict__'):
        # Convert objects to dicts
        return {k: serialize_hypersync_data(v) for k, v in data.__dict__.items() if not k.startswith('_')}
    else:
        # For HyperSync objects without __dict__, extract attributes using dir()
        try:
            obj_dict = {}
            for attr in dir(data):
                if not attr.startswith('_'):
                    try:
                        value = getattr(data, attr)
                        # Skip methods
                        if not callable(value):
                            obj_dict[attr] = serialize_hypersync_data(value)
                    except:
                        pass
            return obj_dict if obj_dict else str(data)
        except:
            return str(data)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "HyperSync Swap API",
        "version": "1.0.0",
        "hypersync_url": HYPERSYNC_URL
    }

@app.get("/api/swaps")
async def get_swaps(
    address: str = Query(..., description="Ethereum wallet address"),
    fromBlock: int = Query(9400000, description="Starting block number"),
):
    """Fetch swap events for a wallet address"""
    if not validate_ethereum_address(address):
        raise HTTPException(status_code=400, detail="Invalid Ethereum address format")

    try:
        swap_topic = "0x40e9cecb9f5f1f1c5b9c97dec2917b7ee92e57ba5563708daca94dd84ad7112f"
        contract_addresses = [addr.lower() for addr in ALL_CONTRACT_ADDRESSES]

        log_selection = hypersync.LogSelection(
            address=contract_addresses,
            topics=[[swap_topic]]
        )

        field_selection = hypersync.FieldSelection(
            block=[
                hypersync.BlockField.NUMBER,
                hypersync.BlockField.TIMESTAMP,
                hypersync.BlockField.HASH,
            ],
            transaction=[
                hypersync.TransactionField.BLOCK_NUMBER,
                hypersync.TransactionField.TRANSACTION_INDEX,
                hypersync.TransactionField.HASH,
                hypersync.TransactionField.FROM,
                hypersync.TransactionField.TO,
                hypersync.TransactionField.VALUE,
                hypersync.TransactionField.INPUT,
            ],
            log=[
                hypersync.LogField.BLOCK_NUMBER,
                hypersync.LogField.LOG_INDEX,
                hypersync.LogField.TRANSACTION_INDEX,
                hypersync.LogField.ADDRESS,
                hypersync.LogField.DATA,
                hypersync.LogField.TOPIC0,
                hypersync.LogField.TOPIC1,
                hypersync.LogField.TOPIC2,
                hypersync.LogField.TOPIC3,
            ]
        )

        query = hypersync.Query(
            logs=[log_selection],
            from_block=fromBlock,
            field_selection=field_selection
        )

        res = await app.state.hypersync_client.get(query)

        print(f"[API] Processing {len(res.data.logs)} logs for address {address}")

        user_address_lower = address.lower()
        filtered_logs = []

        # Create transaction lookup map: (block_number, transaction_index) -> transaction
        tx_lookup = {}
        for tx in res.data.transactions:
            if hasattr(tx, 'block_number') and hasattr(tx, 'transaction_index'):
                key = (tx.block_number, tx.transaction_index)
                tx_lookup[key] = tx

        # Match logs to transactions and filter by user address
        for log in res.data.logs:
            if not hasattr(log, 'block_number') or not hasattr(log, 'transaction_index'):
                continue

            key = (log.block_number, log.transaction_index)
            tx = tx_lookup.get(key)

            if tx is None:
                continue

            # HyperSync uses 'from_' because 'from' is a Python keyword
            tx_from = getattr(tx, 'from_', None)
            if isinstance(tx_from, bytes):
                tx_from = '0x' + tx_from.hex()

            if tx_from and tx_from.lower() == user_address_lower:
                filtered_logs.append(log)

        print(f"[API] Found {len(filtered_logs)} swaps")

        # Serialize and return all data
        return {
            "success": True,
            "logs": serialize_hypersync_data(filtered_logs),
            "blocks": serialize_hypersync_data(res.data.blocks),
            "transactions": serialize_hypersync_data(res.data.transactions),
            "metadata": {
                "total_logs": len(res.data.logs),
                "filtered_logs": len(filtered_logs),
                "total_transactions": len(res.data.transactions),
                "total_blocks": len(res.data.blocks),
                "from_block": fromBlock,
                "next_block": getattr(res, 'next_block', None),
                "archive_height": getattr(res, 'archive_height', None),
            }
        }

    except Exception as e:
        print(f"[API] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))




if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
