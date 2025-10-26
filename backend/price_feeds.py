"""
Token address to Pyth price feed ID mapping for Ethereum Sepolia
Pyth feed IDs are network-agnostic and work across all chains
"""

from typing import Optional

# Pyth price feed IDs for major assets
# These IDs are the same across all networks (Ethereum, Base, Arbitrum, etc.)
PYTH_PRICE_FEEDS = {
    # ETH/USD
    "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2": "0xff61491a931112ddf1bd8147cd1b641375f79f5825126d665480874634fd0ace",  # WETH (mainnet address)
    "0x7b79995e5f793A07Bc00c21412e50Ecae098E7f9": "0xff61491a931112ddf1bd8147cd1b641375f79f5825126d665480874634fd0ace",  # WETH on Sepolia

    # USDC/USD
    "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48": "0xeaa020c61cc479712813461ce153894a96a6c00b21ed0cfc2798d1f9a9e9c94a",  # USDC (mainnet)
    "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238": "0xeaa020c61cc479712813461ce153894a96a6c00b21ed0cfc2798d1f9a9e9c94a",  # USDC on Sepolia

    # USDT/USD
    "0xdAC17F958D2ee523a2206206994597C13D831ec7": "0x2b89b9dc8fdf9f34709a5b106b472f0f39bb6ca9ce04b0fd7f2e971688e2e53b",  # USDT (mainnet)
    "0xaA8E23Fb1079EA71e0a56F48a2aA51851D8433D0": "0x2b89b9dc8fdf9f34709a5b106b472f0f39bb6ca9ce04b0fd7f2e971688e2e53b",  # USDT on Sepolia

    # DAI/USD
    "0x6B175474E89094C44Da98b954EedeAC495271d0F": "0xb0948a5e5313200c632b51bb5ca32f6de0d36e9950a942d19751e833f70dabfd",  # DAI (mainnet)
    "0xFF34B3d4Aee8ddCd6F9AFFFB6Fe49bD371b8a357": "0xb0948a5e5313200c632b51bb5ca32f6de0d36e9950a942d19751e833f70dabfd",  # DAI on Sepolia

    # WBTC/USD
    "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599": "0xe62df6c8b4a85fe1a67db44dc12de5db330f7ac66b72dc658afedf0f4a415b43",  # WBTC (mainnet)
    "0x29f2D40B0605204364af54EC677bD022dA425d03": "0xe62df6c8b4a85fe1a67db44dc12de5db330f7ac66b72dc658afedf0f4a415b43",  # WBTC on Sepolia
}

# Token symbol mapping for display purposes
TOKEN_SYMBOLS = {
    "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2": "WETH",
    "0x7b79995e5f793A07Bc00c21412e50Ecae098E7f9": "WETH",
    "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48": "USDC",
    "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238": "USDC",
    "0xdAC17F958D2ee523a2206206994597C13D831ec7": "USDT",
    "0xaA8E23Fb1079EA71e0a56F48a2aA51851D8433D0": "USDT",
    "0x6B175474E89094C44Da98b954EedeAC495271d0F": "DAI",
    "0xFF34B3d4Aee8ddCd6F9AFFFB6Fe49bD371b8a357": "DAI",
    "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599": "WBTC",
    "0x29f2D40B0605204364af54EC677bD022dA425d03": "WBTC",
}


def get_pyth_feed_id(token_address: str) -> Optional[str]:
    """
    Get Pyth price feed ID for a given token address

    Args:
        token_address: Ethereum token contract address (case-insensitive)

    Returns:
        Pyth feed ID string, or None if token not supported
    """
    # Normalize address to checksum format for lookup
    normalized_address = token_address if token_address.startswith("0x") else f"0x{token_address}"

    # Try exact match first
    if normalized_address in PYTH_PRICE_FEEDS:
        return PYTH_PRICE_FEEDS[normalized_address]

    # Try case-insensitive match
    for addr, feed_id in PYTH_PRICE_FEEDS.items():
        if addr.lower() == normalized_address.lower():
            return feed_id

    return None


def get_token_symbol(token_address: str) -> str:
    """
    Get token symbol for a given address

    Args:
        token_address: Ethereum token contract address

    Returns:
        Token symbol string, or shortened address if unknown
    """
    normalized_address = token_address if token_address.startswith("0x") else f"0x{token_address}"

    # Try exact match
    if normalized_address in TOKEN_SYMBOLS:
        return TOKEN_SYMBOLS[normalized_address]

    # Try case-insensitive match
    for addr, symbol in TOKEN_SYMBOLS.items():
        if addr.lower() == normalized_address.lower():
            return symbol

    # Return shortened address if unknown
    return f"{normalized_address[:6]}...{normalized_address[-4:]}"


def is_supported_token(token_address: str) -> bool:
    """
    Check if a token has a Pyth price feed available

    Args:
        token_address: Ethereum token contract address

    Returns:
        True if token is supported, False otherwise
    """
    return get_pyth_feed_id(token_address) is not None
