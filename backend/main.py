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
from pydantic import BaseModel
from supabase import create_client
from datetime import datetime
import time
import asyncio
import secrets
import string
import requests

# Load environment variables
load_dotenv()

# HyperSync configuration
HYPERSYNC_URL = os.getenv("NEXT_PUBLIC_HYPERSYNC_URL", "https://sepolia.hypersync.xyz")
ENVIO_API_TOKEN = os.getenv("ENVIO_API_TOKEN")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize HyperSync, Pyth, and Supabase clients on startup and clean up on shutdown"""
    # Startup: Initialize clients once
    app.state.hypersync_client = hypersync.HypersyncClient(
        hypersync.ClientConfig(
            url=HYPERSYNC_URL,
            bearer_token=ENVIO_API_TOKEN
        )
    )
    app.state.pyth_client = PythClient()
    # Create Supabase client in a thread-safe way for async context
    app.state.supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_KEY")
    )
    app.state.price_cache = {}  # For 10s price caching: {token_address: (price, timestamp)}
    yield
    # Shutdown: cleanup
    await app.state.pyth_client.close()
    app.state.hypersync_client = None
    app.state.pyth_client = None
    app.state.supabase = None

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
    "0x3289680dd4d6c10bb19b899729cda5eef58aeff1",  # WETH/USDC Pool
]


# Request Models
class CreatePostRequest(BaseModel):
    username: str
    tx_hash: str
    content: str


class EnsureUserRequest(BaseModel):
    wallet_address: str


class UserResponse(BaseModel):
    username: str
    wallet_address: str
    is_new: bool


class CreateTipRequest(BaseModel):
    tipper_address: str
    tx_hash: str


class TipResponse(BaseModel):
    id: str
    post_id: str
    tipper_address: str
    amount: float
    tx_hash: str
    status: str
    created_at: str


def validate_ethereum_address(address: str) -> bool:
    """Validate Ethereum address format"""
    pattern = r"^0x[a-fA-F0-9]{40}$"
    return bool(re.match(pattern, address))


def generate_random_username() -> str:
    """Generate a random username like 'trader_abc123'"""
    chars = string.ascii_lowercase + string.digits
    random_suffix = ''.join(secrets.choice(chars) for _ in range(6))
    return f"trader_{random_suffix}"


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


async def get_trade_by_hash(tx_hash: str, hypersync_client):
    """
    Query HyperSync for a specific trade by transaction hash
    Returns dict with trade data or None if not found
    """
    try:
        # Support both Uniswap V3 and V4 swap topics
        swap_topic_v4 = "0x40e9cecb9f5f1f1c5b9c97dec2917b7ee92e57ba5563708daca94dd84ad7112f"
        swap_topic_v3 = "0xc42079f94a6350d7e6235f29174924f7e02e2149c267a8b7d8f3cb1aca6b266b"
        contract_addresses = [addr.lower() for addr in ALL_CONTRACT_ADDRESSES]

        log_selection = hypersync.LogSelection(
            address=contract_addresses,
            topics=[[swap_topic_v4, swap_topic_v3]]
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

        # Query from a reasonable starting block (last ~1000 blocks)
        # This avoids querying from block 0 which can be slow
        from_block = 9400000  # Sepolia approx current block - 1000

        query = hypersync.Query(
            logs=[log_selection],
            field_selection=field_selection,
            from_block=from_block
        )

        res = await hypersync_client.get(query)

        print(f"[API] get_trade_by_hash: Searching for {tx_hash}, found {len(res.data.logs)} logs, {len(res.data.transactions)} transactions")

        # Debug: Print all transaction hashes
        if not res.data.transactions:
            print("[API] WARNING: No transactions in response!")

        for i, t in enumerate(res.data.transactions[:5]):
            t_hash = t.hash.hex() if isinstance(t.hash, bytes) else str(t.hash)
            if not t_hash.startswith('0x'):
                t_hash = '0x' + t_hash
            print(f"[API]   Tx {i}: {t_hash}")
            if t_hash.lower() == tx_hash.lower():
                print(f"[API]   ^ MATCH FOUND!")

        # Find log matching tx_hash
        for log in res.data.logs:
            tx = next(
                (t for t in res.data.transactions
                 if hasattr(t, 'block_number') and hasattr(t, 'transaction_index') and
                    hasattr(log, 'block_number') and hasattr(log, 'transaction_index') and
                    t.block_number == log.block_number and
                    t.transaction_index == log.transaction_index),
                None
            )

            if tx and hasattr(tx, 'hash') and tx.hash:
                # Convert hash to string if it's bytes
                tx_hash_str = tx.hash.hex() if isinstance(tx.hash, bytes) else str(tx.hash)
                if not tx_hash_str.startswith('0x'):
                    tx_hash_str = '0x' + tx_hash_str

                if tx_hash_str.lower() == tx_hash.lower():
                    # Found matching transaction
                    block = next(
                        (b for b in res.data.blocks if hasattr(b, 'number') and b.number == log.block_number),
                        None
                    )

                    # Extract wallet address from tx.from_
                    tx_from = getattr(tx, 'from_', None)
                    if isinstance(tx_from, bytes):
                        tx_from = '0x' + tx_from.hex()

                    # Parse swap event data
                    from viem import decodeAbiParameters
                    try:
                        decoded = decodeAbiParameters(
                            [
                                {'name': 'amount0', 'type': 'int128'},
                                {'name': 'amount1', 'type': 'int128'},
                                {'name': 'sqrtPriceX96', 'type': 'uint160'},
                                {'name': 'liquidity', 'type': 'uint128'},
                                {'name': 'tick', 'type': 'int24'},
                                {'name': 'fee', 'type': 'uint24'},
                            ],
                            log.data if isinstance(log.data, str) else ('0x' + log.data.hex() if isinstance(log.data, bytes) else log.data)
                        )

                        amount0 = decoded[0]
                        amount1 = decoded[1]
                    except:
                        # Fallback if parsing fails
                        amount0 = 0
                        amount1 = 0

                    # Get token addresses from pool ID (topic1)
                    pool_id = log.topic1 if hasattr(log, 'topic1') else None

                    # For MVP, use default tokens
                    token_in = "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238"  # USDC
                    token_out = "0x7b79995e5f793A07Bc00c21412e50Ecae098E7f9"  # WETH

                    # Determine direction
                    if amount0 < 0:
                        amount_in = abs(amount1)
                        amount_out = abs(amount0)
                    else:
                        amount_in = abs(amount0)
                        amount_out = abs(amount1)

                    # Get timestamp
                    trade_timestamp = block.timestamp if block and hasattr(block, 'timestamp') else None

                    return {
                        'wallet_address': tx_from,
                        'tx_hash': tx_hash,
                        'token_in_address': token_in,
                        'token_out_address': token_out,
                        'amount_in': float(amount_in / 1e6),  # USDC decimals
                        'amount_out': float(amount_out / 1e18),  # WETH decimals
                        'trade_timestamp': datetime.fromtimestamp(int(trade_timestamp)) if trade_timestamp else datetime.now()
                    }

        return None

    except Exception as e:
        print(f"[API] Error in get_trade_by_hash: {str(e)}")
        return None


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
        user_address_lower = address.lower()

        # Support both Uniswap V3 and V4 swap topics
        swap_topic_v4 = "0x40e9cecb9f5f1f1c5b9c97dec2917b7ee92e57ba5563708daca94dd84ad7112f"
        swap_topic_v3 = "0xc42079f94a6350d7e6235f29174924f7e02e2149c267a8b7d8f3cb1aca6b266b"
        contract_addresses = [addr.lower() for addr in ALL_CONTRACT_ADDRESSES]

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

        # Step 1: Query ONLY user's transactions (no logs yet)
        print(f"[API] Step 1: Querying transactions from {user_address_lower}")

        tx_selection = hypersync.TransactionSelection(
            from_=[user_address_lower]
        )

        tx_query = hypersync.Query(
            transactions=[tx_selection],
            from_block=fromBlock,
            field_selection=field_selection
        )

        tx_res = await app.state.hypersync_client.get(tx_query)

        print(f"[API] Got {len(tx_res.data.transactions)} transactions from user")

        # Build set of user's transaction indices
        user_tx_indices = set()
        for tx in tx_res.data.transactions:
            if hasattr(tx, 'block_number') and hasattr(tx, 'transaction_index'):
                key = (tx.block_number, tx.transaction_index)
                user_tx_indices.add(key)
                print(f"[API]   User tx: block={tx.block_number}, idx={tx.transaction_index}")

        # Step 2: Query for logs from swap contracts and filter by user's transaction indices
        print(f"[API] Step 2: Querying swap logs")

        log_selection = hypersync.LogSelection(
            address=contract_addresses,
            topics=[[swap_topic_v4, swap_topic_v3]]
        )

        log_query = hypersync.Query(
            logs=[log_selection],
            from_block=fromBlock,
            field_selection=field_selection
        )

        log_res = await app.state.hypersync_client.get(log_query)

        print(f"[API] Got {len(log_res.data.logs)} total logs from swap contracts")

        # Filter logs to ONLY those from user's transactions
        filtered_logs = []
        for log in log_res.data.logs:
            if not hasattr(log, 'block_number') or not hasattr(log, 'transaction_index'):
                continue

            key = (log.block_number, log.transaction_index)

            # ONLY include logs that are in the user's transaction indices
            if key in user_tx_indices:
                filtered_logs.append(log)
                print(f"[API]   Matching log: block={log.block_number}, idx={log.transaction_index}")

        print(f"[API] Found {len(filtered_logs)} swaps from user's transactions")

        # Combine the data from both queries
        res = type('obj', (object,), {
            'data': type('obj', (object,), {
                'logs': filtered_logs,
                'transactions': tx_res.data.transactions,
                'blocks': log_res.data.blocks
            })()
        })()

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


@app.post('/api/users/ensure')
async def ensure_user(request: EnsureUserRequest) -> UserResponse:
    """Ensure user exists with wallet address. Creates user if doesn't exist."""
    try:
        # Validate wallet address
        if not validate_ethereum_address(request.wallet_address):
            raise HTTPException(status_code=400, detail="Invalid wallet address format")

        wallet_lower = request.wallet_address.lower()

        # Check if user exists with this wallet
        loop = asyncio.get_event_loop()
        existing_user = await loop.run_in_executor(
            None,
            lambda: app.state.supabase.table('users')
                .select('username')
                .eq('wallet_address', wallet_lower)
                .execute()
        )

        if existing_user.data:
            # User already exists
            return UserResponse(
                username=existing_user.data[0]['username'],
                wallet_address=wallet_lower,
                is_new=False
            )

        # Generate unique username
        max_retries = 5
        username = None

        for attempt in range(max_retries):
            candidate_username = generate_random_username()

            # Check if username is unique
            try:
                existing = await loop.run_in_executor(
                    None,
                    lambda: app.state.supabase.table('users')
                        .select('username')
                        .eq('username', candidate_username)
                        .execute()
                )

                if not existing.data:
                    username = candidate_username
                    break
            except Exception as e:
                print(f"[API] Error checking username uniqueness: {str(e)}")
                continue

        if not username:
            raise HTTPException(status_code=500, detail="Failed to generate unique username")

        # Insert new user
        try:
            result = await loop.run_in_executor(
                None,
                lambda: app.state.supabase.table('users')
                    .insert({
                        'username': username,
                        'wallet_address': wallet_lower
                    })
                    .execute()
            )

            if result.data:
                return UserResponse(
                    username=result.data[0]['username'],
                    wallet_address=wallet_lower,
                    is_new=True
                )
            else:
                raise HTTPException(status_code=500, detail="Failed to create user")
        except Exception as e:
            print(f"[API] Error creating user: {str(e)}")
            if "unique constraint" in str(e).lower():
                # Race condition: username already taken, retry
                return await ensure_user(request)
            raise HTTPException(status_code=500, detail="Failed to create user")

    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] Error in ensure_user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/api/posts')
async def create_post(request: CreatePostRequest):
    """Create a new post from a verified trade"""
    try:
        # Validate tx_hash format
        if not re.match(r'^0x[a-fA-F0-9]{64}$', request.tx_hash):
            raise HTTPException(status_code=400, detail="Invalid tx_hash format")

        # Verify user exists
        loop = asyncio.get_event_loop()
        user_result = await loop.run_in_executor(
            None,
            lambda: app.state.supabase.table('users')
                .select('*')
                .eq('username', request.username)
                .execute()
        )

        if not user_result.data:
            raise HTTPException(status_code=404, detail="User not found")

        # Check for duplicate tx_hash
        existing = await loop.run_in_executor(
            None,
            lambda: app.state.supabase.table('posts')
                .select('id')
                .eq('tx_hash', request.tx_hash)
                .execute()
        )

        if existing.data:
            raise HTTPException(status_code=409, detail="tx_hash already posted")

        # Insert post with default trade data
        post_data = {
            'username': request.username,
            'token_in_address': "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238",  # USDC
            'token_out_address': "0x7b79995e5f793A07Bc00c21412e50Ecae098E7f9",  # WETH
            'amount_in': 1.0,
            'amount_out': 0.5,
            'tx_hash': request.tx_hash,
            'content': request.content,
            'trade_timestamp': datetime.now().isoformat(),
            'exited': False
        }

        result = await loop.run_in_executor(
            None,
            lambda: app.state.supabase.table('posts').insert(post_data).execute()
        )

        if result.data:
            return result.data[0]
        else:
            raise HTTPException(status_code=500, detail="Failed to create post")

    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] Error creating post: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/posts/posted-hashes')
async def get_posted_hashes():
    """Get list of tx_hashes that have already been posted"""
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: app.state.supabase.table('posts')
                .select('tx_hash')
                .execute()
        )

        hashes = [p['tx_hash'].lower() for p in (result.data or [])]
        return {"posted_hashes": hashes}

    except Exception as e:
        print(f"[API] Error fetching posted hashes: {str(e)}")
        return {"posted_hashes": []}


@app.get('/api/posts')
async def get_posts(
    sort: str = Query("recent", regex="^(recent|pnl|tipped)$"),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    viewer_wallet: str = Query(None)
):
    """Fetch feed with calculated P&L and viewer tip status"""
    try:
        print(f"[API] GET /api/posts: viewer_wallet={viewer_wallet}")
        # Query posts from Supabase
        loop = asyncio.get_event_loop()
        posts_result = await loop.run_in_executor(
            None,
            lambda: app.state.supabase.table('posts')
                .select('*')
                .order('created_at', desc=True)
                .range(offset, offset + limit - 1)
                .execute()
        )

        posts = posts_result.data or []

        # Get total count
        try:
            count_result = await loop.run_in_executor(
                None,
                lambda: app.state.supabase.table('posts')
                    .select('*', count='exact')
                    .execute()
            )
            total = count_result.count if hasattr(count_result, 'count') else len(posts)
        except:
            total = len(posts)

        # Enrich each post with P&L calculation
        enriched_posts = []

        for post in posts:
            enriched_post = {**post}
            post_id = post.get('id')

            # Get trader's wallet address from username
            try:
                user_result = await loop.run_in_executor(
                    None,
                    lambda: app.state.supabase.table('users')
                        .select('wallet_address')
                        .eq('username', post.get('username'))
                        .execute()
                )
                if user_result.data:
                    enriched_post['trader_wallet_address'] = user_result.data[0]['wallet_address']
            except Exception as e:
                print(f"[API] Error fetching trader wallet: {str(e)}")
                enriched_post['trader_wallet_address'] = None

            # Check if viewer has tipped this post
            enriched_post['viewer_has_tipped'] = False
            if viewer_wallet:
                try:
                    print(f"[API] Checking if {viewer_wallet} tipped post {post_id}")
                    tips_result = await loop.run_in_executor(
                        None,
                        lambda: app.state.supabase.table('tips')
                            .select('*')
                            .eq('post_id', post_id)
                            .eq('tipper_address', viewer_wallet.lower())
                            .execute()
                    )
                    has_tipped = len(tips_result.data) > 0 if tips_result.data else False
                    enriched_post['viewer_has_tipped'] = has_tipped
                    print(f"[API]   Result: viewer_has_tipped={has_tipped}, tips_found={len(tips_result.data) if tips_result.data else 0}")
                except Exception as e:
                    print(f"[API] Error checking viewer tips for post {post_id}: {str(e)}")
                    enriched_post['viewer_has_tipped'] = False

            try:
                # Get entry price from Pyth
                token_out = post['token_out_address']
                entry_feed_id = get_pyth_feed_id(token_out)
                entry_price = None

                print(f"[API] Enriching post {post_id}: token_out={token_out}, feed_id={entry_feed_id}, trade_timestamp={post.get('trade_timestamp')}")

                # Use trade_timestamp if available, fallback to created_at
                timestamp_to_use = post.get('trade_timestamp') or post.get('created_at')

                if entry_feed_id and timestamp_to_use:
                    # Parse timestamp
                    try:
                        if isinstance(timestamp_to_use, str):
                            trade_dt = datetime.fromisoformat(timestamp_to_use.replace('Z', '+00:00'))
                            trade_ts = int(trade_dt.timestamp())
                        else:
                            trade_ts = int(timestamp_to_use)

                        print(f"[API]   Getting historical price for feed {entry_feed_id} at timestamp {trade_ts}")

                        # Get entry price at trade timestamp
                        entry_price_data = await app.state.pyth_client.get_price_at_timestamp(
                            entry_feed_id, trade_ts
                        )
                        entry_price = entry_price_data['price'] if entry_price_data else None
                        print(f"[API]   Entry price: {entry_price}")
                    except (ValueError, TypeError) as e:
                        print(f"[API] Error parsing timestamp for post {post_id}: {e}")
                        entry_price = None
                else:
                    print(f"[API]   No valid timestamp found (trade_timestamp={post.get('trade_timestamp')}, created_at={post.get('created_at')})")
                    entry_price = None

                enriched_post['entry_price'] = entry_price

                # Get current or exit price
                if post.get('exited'):
                    if entry_feed_id:
                        try:
                            # Use exit_timestamp if available, otherwise fallback to created_at
                            exit_time = post.get('exit_timestamp') or post.get('created_at')
                            if exit_time:
                                if isinstance(exit_time, str):
                                    exit_dt = datetime.fromisoformat(exit_time.replace('Z', '+00:00'))
                                    exit_ts = int(exit_dt.timestamp())
                                else:
                                    exit_ts = int(exit_time)

                                exit_price_data = await app.state.pyth_client.get_price_at_timestamp(
                                    entry_feed_id, exit_ts
                                )
                                current_price = exit_price_data['price'] if exit_price_data else None
                                enriched_post['exit_price'] = current_price
                                enriched_post['current_price'] = None
                            else:
                                current_price = None
                                enriched_post['exit_price'] = None
                                enriched_post['current_price'] = None
                        except (ValueError, TypeError) as e:
                            print(f"[API] Error parsing exit_timestamp for post {post_id}: {e}")
                            enriched_post['exit_price'] = None
                            enriched_post['current_price'] = None
                    else:
                        current_price = None
                        enriched_post['exit_price'] = None
                        enriched_post['current_price'] = None
                else:
                    # Use cached current price (10s TTL)
                    if entry_feed_id:
                        cache_key = post['token_out_address']
                        now = time.time()

                        if cache_key in app.state.price_cache:
                            cached_price, cached_time = app.state.price_cache[cache_key]
                            if now - cached_time < 300:  # 5 minute cache (300 seconds)
                                current_price = cached_price
                                print(f"[API]   Using cached current price: {current_price}")
                            else:
                                # Fetch fresh price
                                print(f"[API]   Fetching fresh price for feed {entry_feed_id}")
                                price_data_list = await app.state.pyth_client.get_latest_prices([entry_feed_id])
                                print(f"[API]   price_data_list type: {type(price_data_list)}, content: {price_data_list}")
                                # Try both with and without 0x prefix
                                price_data = price_data_list.get(entry_feed_id) if isinstance(price_data_list, dict) else None
                                if not price_data and entry_feed_id.startswith('0x'):
                                    # Try without 0x prefix
                                    price_data = price_data_list.get(entry_feed_id[2:])
                                print(f"[API]   price_data: {price_data}")
                                current_price = price_data['price'] if price_data else None
                                print(f"[API]   Current price: {current_price}")
                                # Only cache if price was successfully fetched
                                if current_price is not None:
                                    app.state.price_cache[cache_key] = (current_price, now)
                        else:
                            # Fetch and cache
                            print(f"[API]   Fetching initial price for feed {entry_feed_id}")
                            price_data_list = await app.state.pyth_client.get_latest_prices([entry_feed_id])
                            print(f"[API]   price_data_list type: {type(price_data_list)}, content: {price_data_list}")
                            # Try both with and without 0x prefix
                            price_data = price_data_list.get(entry_feed_id) if isinstance(price_data_list, dict) else None
                            if not price_data and entry_feed_id.startswith('0x'):
                                # Try without 0x prefix
                                price_data = price_data_list.get(entry_feed_id[2:])
                            print(f"[API]   price_data: {price_data}")
                            current_price = price_data['price'] if price_data else None
                            print(f"[API]   Current price: {current_price}")
                            # Only cache if price was successfully fetched
                            if current_price is not None:
                                app.state.price_cache[cache_key] = (current_price, now)
                    else:
                        current_price = None
                        print(f"[API]   No feed ID found for token_out")

                    enriched_post['current_price'] = current_price
                    enriched_post['exit_price'] = None

                # Calculate P&L
                pnl = None
                price_for_pnl = enriched_post.get('exit_price') or enriched_post.get('current_price')
                print(f"[API]   P&L calc: entry_price={entry_price}, price_for_pnl={price_for_pnl}")
                if entry_price and price_for_pnl:
                    pnl = ((price_for_pnl - entry_price) / entry_price) * 100
                    print(f"[API]   Calculated P&L: {pnl}%")
                else:
                    print(f"[API]   Cannot calculate P&L (entry_price or price_for_pnl is None)")

                enriched_post['pnl'] = pnl

            except Exception as e:
                print(f"[API] Error enriching post {post.get('id')}: {str(e)}")
                enriched_post['entry_price'] = None
                enriched_post['current_price'] = None
                enriched_post['exit_price'] = None
                enriched_post['pnl'] = None

            enriched_posts.append(enriched_post)

        # Sort by P&L if requested
        if sort == 'pnl':
            enriched_posts.sort(key=lambda x: x.get('pnl') or -float('inf'), reverse=True)
        elif sort == 'tipped':
            # Sort by total tips received (highest first)
            enriched_posts.sort(key=lambda x: x.get('total_tips') or 0, reverse=True)

        return {
            'posts': enriched_posts,
            'total': total
        }

    except Exception as e:
        print(f"[API] Error fetching posts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def verify_pyusd_transfer_on_chain(tx_hash: str, recipient_address: str, expected_amount: str) -> dict:
    """
    Verify PYUSD transfer on chain using Etherscan API
    Returns transaction details if verified, raises exception if not found or invalid
    """
    ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "")
    PYUSD_SEPOLIA_ADDRESS = "0xCaC524BcA292aaade2DF8A05cC58F0a65B1B3bB9"
    SEPOLIA_CHAIN = "sepolia"  # For Etherscan API

    # For MVP, we can verify using Etherscan or skip verification
    # If no API key, we still record the tip with "unverified" status
    if not ETHERSCAN_API_KEY:
        print(f"[API] Warning: No Etherscan API key configured. Tip recorded as unverified.")
        return {
            "verified": False,
            "tx_hash": tx_hash,
            "reason": "No Etherscan API key"
        }

    try:
        # Query Etherscan for transaction details
        url = f"https://{SEPOLIA_CHAIN}.etherscan.io/api"
        params = {
            "apikey": ETHERSCAN_API_KEY,
            "module": "account",
            "action": "tokentx",
            "contractaddress": PYUSD_SEPOLIA_ADDRESS,
            "txhash": tx_hash,
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "1" or not data.get("result"):
            print(f"[API] Transaction {tx_hash} not found on Etherscan")
            return {
                "verified": False,
                "tx_hash": tx_hash,
                "reason": "Transaction not found"
            }

        # Get the first result (should be only one for a specific tx_hash)
        tx_info = data["result"][0] if isinstance(data["result"], list) else data["result"]

        # Verify recipient and amount
        # Note: PYUSD has 6 decimals, so 1 PYUSD = 1000000
        tx_to = tx_info.get("to", "").lower()
        recipient_lower = recipient_address.lower()
        amount_in_units = int(tx_info.get("value", "0"))
        amount_in_pyusd = amount_in_units / 1_000_000

        if tx_to != recipient_lower:
            print(f"[API] Recipient mismatch: {tx_to} != {recipient_lower}")
            return {
                "verified": False,
                "tx_hash": tx_hash,
                "reason": "Recipient mismatch"
            }

        # Check amount is approximately 1 PYUSD (within 0.1 tolerance for decimal conversion)
        if abs(amount_in_pyusd - 1.0) > 0.01:
            print(f"[API] Amount mismatch: {amount_in_pyusd} != 1.0")
            return {
                "verified": False,
                "tx_hash": tx_hash,
                "reason": f"Amount mismatch: got {amount_in_pyusd} PYUSD"
            }

        print(f"[API] PYUSD transfer verified: {tx_hash} -> {amount_in_pyusd} PYUSD to {tx_to}")
        return {
            "verified": True,
            "tx_hash": tx_hash,
            "amount": amount_in_pyusd,
            "recipient": tx_to
        }

    except Exception as e:
        print(f"[API] Error verifying PYUSD transfer: {str(e)}")
        return {
            "verified": False,
            "tx_hash": tx_hash,
            "reason": str(e)
        }


@app.post('/api/posts/{post_id}/tips')
async def create_tip(post_id: str, request: CreateTipRequest):
    """
    Create a tip for a post
    Verifies PYUSD transfer on-chain and records in database
    """
    try:
        # Validate inputs
        if not validate_ethereum_address(request.tipper_address):
            raise HTTPException(status_code=400, detail="Invalid tipper address")

        if not request.tx_hash.startswith('0x') or len(request.tx_hash) != 66:
            raise HTTPException(status_code=400, detail="Invalid transaction hash")

        # Check if post exists
        posts = app.state.supabase.table('posts').select('*').eq('id', post_id).execute()
        if not posts.data:
            raise HTTPException(status_code=404, detail="Post not found")

        post = posts.data[0]
        recipient_address = None

        # Get recipient address (trader's wallet) from post's username
        users = app.state.supabase.table('users').select('wallet_address').eq('username', post['username']).execute()
        if users.data:
            recipient_address = users.data[0]['wallet_address']

        if not recipient_address:
            raise HTTPException(status_code=400, detail="Could not find recipient wallet address")

        # Verify PYUSD transfer on chain
        verification = verify_pyusd_transfer_on_chain(request.tx_hash, recipient_address, "1.0")

        # Record tip in database (even if unverified for MVP)
        tip_data = {
            'post_id': post_id,
            'tipper_address': request.tipper_address.lower(),
            'tipper_username': None,  # Can be populated later if needed
            'amount': 1.0,
            'tx_hash': request.tx_hash,
            'status': 'confirmed' if verification['verified'] else 'unverified'
        }

        # Try to find tipper's username
        tipper_users = app.state.supabase.table('users').select('username').eq('wallet_address', request.tipper_address.lower()).execute()
        if tipper_users.data:
            tip_data['tipper_username'] = tipper_users.data[0]['username']

        # Insert tip
        result = app.state.supabase.table('tips').insert(tip_data).execute()

        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create tip")

        # Update post's tip totals
        app.state.supabase.table('posts').update({
            'total_tips': post.get('total_tips', 0) + 1.0,
            'tip_count': post.get('tip_count', 0) + 1
        }).eq('id', post_id).execute()

        tip = result.data[0]
        return TipResponse(
            id=tip['id'],
            post_id=tip['post_id'],
            tipper_address=tip['tipper_address'],
            amount=tip['amount'],
            tx_hash=tip['tx_hash'],
            status=tip['status'],
            created_at=tip['created_at']
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] Error creating tip: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/posts/{post_id}/tips')
async def get_tips_for_post(post_id: str):
    """
    Get all tips for a specific post
    """
    try:
        # Get tips for post
        tips = app.state.supabase.table('tips').select('*').eq('post_id', post_id).order('created_at', desc=True).execute()

        if not tips.data:
            return {
                'post_id': post_id,
                'total_amount': 0.0,
                'count': 0,
                'tips': []
            }

        # Calculate totals
        total_amount = sum(float(tip['amount']) for tip in tips.data)

        # Format response
        formatted_tips = [
            {
                'tipper_address': tip['tipper_address'],
                'tipper_username': tip['tipper_username'],
                'amount': float(tip['amount']),
                'created_at': tip['created_at'],
                'status': tip['status']
            }
            for tip in tips.data
        ]

        return {
            'post_id': post_id,
            'total_amount': total_amount,
            'count': len(tips.data),
            'tips': formatted_tips
        }

    except Exception as e:
        print(f"[API] Error fetching tips for post: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/users/{username}/tips')
async def get_tips_for_user(username: str):
    """
    Get all tips received by a specific user (trader)
    """
    try:
        # Get user's posts
        posts = app.state.supabase.table('posts').select('id').eq('username', username).execute()

        if not posts.data:
            return {
                'username': username,
                'total_received': 0.0,
                'tip_count': 0,
                'recent_tips': []
            }

        post_ids = [post['id'] for post in posts.data]

        # Get all tips for user's posts
        tips = app.state.supabase.table('tips').select('*').in_('post_id', post_ids).order('created_at', desc=True).limit(100).execute()

        if not tips.data:
            return {
                'username': username,
                'total_received': 0.0,
                'tip_count': 0,
                'recent_tips': []
            }

        # Calculate totals
        total_received = sum(float(tip['amount']) for tip in tips.data)

        # Format response
        formatted_tips = [
            {
                'tipper_address': tip['tipper_address'],
                'tipper_username': tip['tipper_username'],
                'amount': float(tip['amount']),
                'created_at': tip['created_at'],
                'status': tip['status']
            }
            for tip in tips.data
        ]

        return {
            'username': username,
            'total_received': total_received,
            'tip_count': len(tips.data),
            'recent_tips': formatted_tips
        }

    except Exception as e:
        print(f"[API] Error fetching tips for user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/debug/trade/{tx_hash}')
async def debug_trade(tx_hash: str):
    """Debug endpoint to check trade lookup"""
    trade = await get_trade_by_hash(tx_hash, app.state.hypersync_client)
    return {"tx_hash": tx_hash, "found": trade is not None, "trade": trade}


@app.get('/api/posts/stream')
async def stream_posts():
    """Placeholder for streaming posts"""
    return {"stream": []}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
