"""
Pyth Network HTTP API Client
Provides async methods to fetch historical and current price data from Pyth's Hermes API
"""

import httpx
from typing import Optional, Dict, List

PYTH_HERMES_URL = "https://hermes.pyth.network"


class PythClient:
    """Client for interacting with Pyth Network's Hermes HTTP API"""

    def __init__(self, base_url: str = PYTH_HERMES_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=10.0)

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

    async def get_price_at_timestamp(
        self,
        feed_id: str,
        timestamp: int
    ) -> Optional[Dict[str, any]]:
        """
        Fetch historical price for a given feed ID at a specific timestamp

        Args:
            feed_id: Pyth price feed ID (e.g., "0xff61491a931112ddf1bd8147cd1b641375f79f5825126d665480874634fd0ace")
            timestamp: Unix timestamp in seconds

        Returns:
            Dict with 'price', 'expo', 'conf' fields, or None if unavailable
        """
        try:
            url = f"{self.base_url}/v2/updates/price/{timestamp}"
            params = {"ids[]": feed_id}

            response = await self.client.get(url, params=params)
            response.raise_for_status()

            data = response.json()

            # Parse Pyth response structure
            if "parsed" in data and len(data["parsed"]) > 0:
                price_feed = data["parsed"][0]
                price_data = price_feed.get("price", {})

                # Pyth returns price as integer with exponent
                # Actual price = price * 10^expo
                raw_price = int(price_data.get("price", 0))
                expo = int(price_data.get("expo", 0))
                conf = int(price_data.get("conf", 0))

                actual_price = raw_price * (10 ** expo)

                return {
                    "price": actual_price,
                    "expo": expo,
                    "conf": conf,
                    "timestamp": timestamp,
                    "feed_id": feed_id
                }

            return None

        except httpx.HTTPStatusError as e:
            print(f"[Pyth] HTTP error fetching price at timestamp {timestamp}: {e}")
            return None
        except Exception as e:
            print(f"[Pyth] Error fetching price at timestamp {timestamp}: {e}")
            return None

    async def get_latest_prices(
        self,
        feed_ids: List[str]
    ) -> Dict[str, Optional[Dict[str, any]]]:
        """
        Fetch latest prices for multiple feed IDs

        Args:
            feed_ids: List of Pyth price feed IDs

        Returns:
            Dict mapping feed_id -> price data (or None if unavailable)
        """
        if not feed_ids:
            return {}

        try:
            url = f"{self.base_url}/v2/updates/price/latest"
            # Pyth API expects multiple ids[] params
            params = [("ids[]", feed_id) for feed_id in feed_ids]

            response = await self.client.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            results = {}

            # Parse Pyth response structure
            if "parsed" in data:
                for price_feed in data["parsed"]:
                    feed_id = price_feed.get("id")
                    price_data = price_feed.get("price", {})

                    raw_price = int(price_data.get("price", 0))
                    expo = int(price_data.get("expo", 0))
                    conf = int(price_data.get("conf", 0))
                    publish_time = int(price_feed.get("metadata", {}).get("publish_time", 0))

                    actual_price = raw_price * (10 ** expo)

                    results[feed_id] = {
                        "price": actual_price,
                        "expo": expo,
                        "conf": conf,
                        "timestamp": publish_time,
                        "feed_id": feed_id
                    }

            # Fill in None for any missing feeds
            for feed_id in feed_ids:
                if feed_id not in results:
                    results[feed_id] = None

            return results

        except httpx.HTTPStatusError as e:
            print(f"[Pyth] HTTP error fetching latest prices: {e}")
            return {feed_id: None for feed_id in feed_ids}
        except Exception as e:
            print(f"[Pyth] Error fetching latest prices: {e}")
            return {feed_id: None for feed_id in feed_ids}


async def create_pyth_client() -> PythClient:
    """Factory function to create a Pyth client instance"""
    return PythClient()
