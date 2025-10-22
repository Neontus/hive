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
from pyth_client import PythClient
from price_feeds import get_pyth_feed_id, get_token_symbol, is_supported_token

# Load environment variables
load_dotenv()

# HyperSync configuration
HYPERSYNC_URL = os.getenv("NEXT_PUBLIC_HYPERSYNC_URL", "https://sepolia.hypersync.xyz")
ENVIO_API_TOKEN = os.getenv("ENVIO_API_TOKEN")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize HyperSync and Pyth clients on startup and clean up on shutdown"""
    # Startup: Initialize clients once
    app.state.hypersync_client = hypersync.HypersyncClient(
        hypersync.ClientConfig(
            url=HYPERSYNC_URL,
            bearer_token=ENVIO_API_TOKEN
        )
    )
    app.state.pyth_client = PythClient()
    yield
    # Shutdown: cleanup
    await app.state.pyth_client.close()
    app.state.hypersync_client = None
    app.state.pyth_client = None

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


def extract_token_addresses_from_pool_id(pool_id: bytes) -> tuple:
    """
    Extract token addresses from Uniswap V4 pool ID
    Pool ID is a hash that contains token0, token1, fee, and other params

    For MVP: This is a simplified extraction. In production, you'd decode the pool ID
    or query the PoolManager contract to get the actual token addresses.

    Returns:
        (token0_address, token1_address) or (None, None) if unable to extract
    """
    # TODO: For hackathon MVP, we'll need to either:
    # 1. Decode the pool ID structure (complex)
    # 2. Query the PoolManager contract for pool info
    # 3. Parse from transaction input data
    #
    # For now, returning None to handle gracefully
    return (None, None)


async def enrich_swap_with_prices(swap_log, block_timestamp, pyth_client: PythClient) -> dict:
    """
    Enrich swap log data with entry prices from Pyth

    Args:
        swap_log: Serialized swap log data
        block_timestamp: Unix timestamp of the block (can be int, hex string, or string)
        pyth_client: Pyth client instance

    Returns:
        Enriched swap data with price information
    """
    enriched = swap_log.copy() if isinstance(swap_log, dict) else {}

    # Convert timestamp to integer if it's a hex string or string
    if isinstance(block_timestamp, str):
        if block_timestamp.startswith('0x'):
            # Hex string
            timestamp_int = int(block_timestamp, 16)
        else:
            # Regular string number
            timestamp_int = int(block_timestamp)
    else:
        timestamp_int = int(block_timestamp)

    # Extract token addresses from swap log
    # For Uniswap V4, topic1 typically contains the pool ID
    # We'll try to extract tokens from the pool ID or transaction data
    token0, token1 = extract_token_addresses_from_pool_id(
        swap_log.get('topic1') if isinstance(swap_log, dict) else None
    )

    # For MVP: Use hardcoded common test tokens if extraction fails
    # This allows the feature to work while we refine token extraction
    if not token0 or not token1:
        # Default to WETH and USDC for demonstration
        token0 = "0x7b79995e5f793A07Bc00c21412e50Ecae098E7f9"  # WETH on Sepolia
        token1 = "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238"  # USDC on Sepolia

    # Get Pyth feed IDs
    feed_id_0 = get_pyth_feed_id(token0) if token0 else None
    feed_id_1 = get_pyth_feed_id(token1) if token1 else None

    # Fetch prices at swap timestamp
    price_data_0 = None
    price_data_1 = None

    if feed_id_0:
        price_data_0 = await pyth_client.get_price_at_timestamp(feed_id_0, timestamp_int)

    if feed_id_1:
        price_data_1 = await pyth_client.get_price_at_timestamp(feed_id_1, timestamp_int)

    # Add price data to enriched swap
    enriched['token0_address'] = token0
    enriched['token1_address'] = token1
    enriched['token0_symbol'] = get_token_symbol(token0) if token0 else "UNKNOWN"
    enriched['token1_symbol'] = get_token_symbol(token1) if token1 else "UNKNOWN"
    enriched['entry_price_token0_usd'] = price_data_0['price'] if price_data_0 else None
    enriched['entry_price_token1_usd'] = price_data_1['price'] if price_data_1 else None
    enriched['block_timestamp'] = timestamp_int

    return enriched


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

        # Create block lookup map for timestamps
        block_lookup = {}
        for block in res.data.blocks:
            if hasattr(block, 'number') and hasattr(block, 'timestamp'):
                block_lookup[block.number] = block.timestamp

        # Serialize swap logs
        serialized_logs = serialize_hypersync_data(filtered_logs)

        # Enrich swaps with price data
        enriched_swaps = []
        for i, log in enumerate(serialized_logs if isinstance(serialized_logs, list) else []):
            block_number = log.get('block_number')
            block_timestamp = block_lookup.get(block_number)

            if block_timestamp:
                try:
                    enriched_swap = await enrich_swap_with_prices(
                        log,
                        block_timestamp,
                        app.state.pyth_client
                    )
                    enriched_swaps.append(enriched_swap)
                except Exception as e:
                    print(f"[API] Error enriching swap {i}: {e}")
                    # Fallback: include swap without price data
                    enriched_swaps.append(log)
            else:
                # No timestamp available, include without enrichment
                enriched_swaps.append(log)

        print(f"[API] Enriched {len(enriched_swaps)} swaps with price data")

        # Return enriched data
        return {
            "success": True,
            "swaps": enriched_swaps,  # Changed from 'logs' to 'swaps' for clarity
            "blocks": serialize_hypersync_data(res.data.blocks),
            "transactions": serialize_hypersync_data(res.data.transactions),
            "metadata": {
                "total_logs": len(res.data.logs),
                "filtered_swaps": len(filtered_logs),
                "enriched_swaps": len(enriched_swaps),
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

@app.get('/api/prices/current')
async def get_current_prices(
    tokens: str = Query(..., description="Comma-separated token addresses")
):
    """
    Fetch current USD prices for multiple token addresses

    Args:
        tokens: Comma-separated list of token addresses (e.g., "0xabc...,0xdef...")

    Returns:
        Dictionary mapping token addresses to current price data
    """
    try:
        # Parse token addresses
        token_list = [addr.strip() for addr in tokens.split(',') if addr.strip()]

        if not token_list:
            raise HTTPException(status_code=400, detail="No token addresses provided")

        # Get Pyth feed IDs for each token
        feed_id_map = {}  # Maps feed_id -> token_address
        token_to_feed = {}  # Maps token_address -> feed_id

        for token_addr in token_list:
            if not validate_ethereum_address(token_addr):
                print(f"[API] Invalid token address: {token_addr}")
                continue

            feed_id = get_pyth_feed_id(token_addr)
            if feed_id:
                feed_id_map[feed_id] = token_addr
                token_to_feed[token_addr] = feed_id

        if not feed_id_map:
            return {
                "success": True,
                "prices": {},
                "message": "No supported tokens found"
            }

        # Fetch latest prices from Pyth
        price_results = await app.state.pyth_client.get_latest_prices(
            list(feed_id_map.keys())
        )

        # Build response mapping token addresses to prices
        prices = {}
        for feed_id, price_data in price_results.items():
            token_addr = feed_id_map.get(feed_id)
            if token_addr:
                if price_data:
                    prices[token_addr] = {
                        "usd_price": price_data['price'],
                        "timestamp": price_data['timestamp'],
                        "symbol": get_token_symbol(token_addr),
                        "confidence": price_data.get('conf')
                    }
                else:
                    prices[token_addr] = None

        # Include tokens that weren't found in feed_id_map
        for token_addr in token_list:
            if token_addr not in prices:
                prices[token_addr] = None

        return {
            "success": True,
            "prices": prices,
            "total_tokens_requested": len(token_list),
            "total_prices_returned": len([p for p in prices.values() if p is not None])
        }

    except Exception as e:
        print(f"[API] Error fetching current prices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/api/posts')
async def post_trade():
    """Placeholder for creating a post"""
    return {"message": "Post created successfully"}

@app.get('/api/posts')
async def get_posts():
    """Placeholder for fetching posts"""
    return {"posts": []}

@app.get('/api/posts/stream')
async def stream_posts():
    """Placeholder for streaming posts"""
    return {"stream": []}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
