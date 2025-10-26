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
]


# Request Models
class CreatePostRequest(BaseModel):
    username: str
    tx_hash: str
    content: str


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


async def get_trade_by_hash(tx_hash: str, hypersync_client):
    """
    Query HyperSync for a specific trade by transaction hash
    Returns dict with trade data or None if not found
    """
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
            field_selection=field_selection
        )

        res = await hypersync_client.get(query)

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

            if tx and hasattr(tx, 'hash') and tx.hash and tx.hash.lower() == tx_hash.lower():
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
async def create_post(request: CreatePostRequest):
    """Create a new post from a verified trade"""
    try:
        # Validate tx_hash format
        if not re.match(r'^0x[a-fA-F0-9]{64}$', request.tx_hash):
            raise HTTPException(status_code=400, detail="Invalid tx_hash format")

        # Query Supabase for user's wallet address
        try:
            loop = asyncio.get_event_loop()
            user_result = await loop.run_in_executor(
                None,
                lambda: app.state.supabase.table('users')
                    .select('wallet_address')
                    .eq('username', request.username)
                    .execute()
            )

            if not user_result.data:
                raise HTTPException(status_code=404, detail="User not found")

            user_wallet = user_result.data[0]['wallet_address'].lower()
        except Exception as e:
            print(f"[API] Error querying user: {str(e)}")
            raise HTTPException(status_code=404, detail="User not found")

        # Get trade data from HyperSync
        trade = await get_trade_by_hash(request.tx_hash, app.state.hypersync_client)

        if not trade:
            raise HTTPException(status_code=404, detail="Trade not found (wait 60s for indexing)")

        # Validate wallet match
        trade_wallet = trade['wallet_address'].lower() if trade['wallet_address'] else None
        if not trade_wallet or trade_wallet != user_wallet:
            raise HTTPException(status_code=403, detail="Trade wallet doesn't match user")

        # Check for duplicate tx_hash
        try:
            loop = asyncio.get_event_loop()
            existing = await loop.run_in_executor(
                None,
                lambda: app.state.supabase.table('posts')
                    .select('id')
                    .eq('tx_hash', request.tx_hash)
                    .execute()
            )

            if existing.data:
                raise HTTPException(status_code=409, detail="tx_hash already posted")
        except Exception as e:
            if "409" not in str(e):
                print(f"[API] Error checking duplicate: {str(e)}")

        # Insert post
        post_data = {
            'username': request.username,
            'token_in_address': trade['token_in_address'],
            'token_out_address': trade['token_out_address'],
            'amount_in': trade['amount_in'],
            'amount_out': trade['amount_out'],
            'tx_hash': request.tx_hash,
            'content': request.content,
            'trade_timestamp': trade['trade_timestamp'].isoformat(),
            'exited': False
        }

        loop = asyncio.get_event_loop()
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


@app.get('/api/posts')
async def get_posts(
    sort: str = Query("recent", regex="^(recent|pnl)$"),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0)
):
    """Fetch feed with calculated P&L"""
    try:
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

            try:
                # Get entry price from Pyth
                entry_feed_id = get_pyth_feed_id(post['token_out_address'])

                if entry_feed_id:
                    # Parse trade_timestamp
                    if isinstance(post['trade_timestamp'], str):
                        trade_dt = datetime.fromisoformat(post['trade_timestamp'].replace('Z', '+00:00'))
                        trade_ts = int(trade_dt.timestamp())
                    else:
                        trade_ts = int(post['trade_timestamp'])

                    # Get entry price at trade timestamp
                    entry_price_data = await app.state.pyth_client.get_price_at_timestamp(
                        entry_feed_id, trade_ts
                    )
                    entry_price = entry_price_data['price'] if entry_price_data else None
                else:
                    entry_price = None

                enriched_post['entry_price'] = entry_price

                # Get current or exit price
                if post.get('exited'):
                    if post.get('exit_timestamp') and entry_feed_id:
                        if isinstance(post['exit_timestamp'], str):
                            exit_dt = datetime.fromisoformat(post['exit_timestamp'].replace('Z', '+00:00'))
                            exit_ts = int(exit_dt.timestamp())
                        else:
                            exit_ts = int(post['exit_timestamp'])

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
                else:
                    # Use cached current price (10s TTL)
                    if entry_feed_id:
                        cache_key = post['token_out_address']
                        now = time.time()

                        if cache_key in app.state.price_cache:
                            cached_price, cached_time = app.state.price_cache[cache_key]
                            if now - cached_time < 10:  # 10 second cache
                                current_price = cached_price
                            else:
                                # Fetch fresh price
                                price_data_list = await app.state.pyth_client.get_latest_prices([entry_feed_id])
                                price_data = price_data_list.get(entry_feed_id) if isinstance(price_data_list, dict) else None
                                current_price = price_data['price'] if price_data else None
                                app.state.price_cache[cache_key] = (current_price, now)
                        else:
                            # Fetch and cache
                            price_data_list = await app.state.pyth_client.get_latest_prices([entry_feed_id])
                            price_data = price_data_list.get(entry_feed_id) if isinstance(price_data_list, dict) else None
                            current_price = price_data['price'] if price_data else None
                            app.state.price_cache[cache_key] = (current_price, now)
                    else:
                        current_price = None

                    enriched_post['current_price'] = current_price
                    enriched_post['exit_price'] = None

                # Calculate P&L
                pnl = None
                price_for_pnl = enriched_post.get('exit_price') or enriched_post.get('current_price')
                if entry_price and price_for_pnl:
                    pnl = ((price_for_pnl - entry_price) / entry_price) * 100

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

        return {
            'posts': enriched_posts,
            'total': total
        }

    except Exception as e:
        print(f"[API] Error fetching posts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/api/posts/stream')
async def stream_posts():
    """Placeholder for streaming posts"""
    return {"stream": []}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
