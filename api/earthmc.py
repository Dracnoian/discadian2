"""EarthMC API client."""

import aiohttp
import asyncio
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger('EMCBot.API')


class EarthMCAPI:
    """Client for EarthMC API."""
    
    def __init__(self, base_url: str, rate_limit: int = 180):
        """Initialize API client.
        
        Args:
            base_url: Base URL for the API
            rate_limit: Max requests per minute (default 180)
        """
        self.base_url = base_url.rstrip('/')
        self.rate_limit = rate_limit
        self.request_times: List[datetime] = []
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def _wait_for_rate_limit(self):
        """Wait if we're at the rate limit."""
        now = datetime.now()
        
        # Remove requests older than 1 minute
        self.request_times = [
            t for t in self.request_times 
            if now - t < timedelta(minutes=1)
        ]
        
        # If at limit, wait until oldest request is > 1 minute old
        if len(self.request_times) >= self.rate_limit:
            oldest = self.request_times[0]
            wait_time = 60 - (now - oldest).total_seconds()
            if wait_time > 0:
                logger.warning(f"Rate limit reached, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[Any, Any]]:
        """Make an API request with rate limiting and retry logic."""
        await self._wait_for_rate_limit()
        
        url = f"{self.base_url}{endpoint}"
        session = await self._get_session()
        
        # Log the request for debugging
        if 'json' in kwargs:
            logger.debug(f"API Request: {method} {url} with data: {kwargs['json']}")
        else:
            logger.debug(f"API Request: {method} {url}")
        
        for attempt in range(3):  # 3 attempts with exponential backoff
            try:
                self.request_times.append(datetime.now())
                
                async with session.request(method, url, **kwargs) as response:
                    if response.status == 429:  # Rate limited
                        retry_after = int(response.headers.get('Retry-After', 60))
                        logger.warning(f"Rate limited, retrying after {retry_after}s")
                        await asyncio.sleep(retry_after)
                        continue
                    
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 404:
                        logger.debug(f"Resource not found: {url}")
                        return None
                    else:
                        # Get response text for debugging
                        try:
                            error_text = await response.text()
                            logger.error(f"API error {response.status}: {url} - Response: {error_text[:200]}")
                        except:
                            logger.error(f"API error {response.status}: {url}")
                        
                        if attempt < 2:
                            await asyncio.sleep(2 ** attempt)  # Exponential backoff
                            continue
                        return None
                        
            except aiohttp.ClientError as e:
                logger.error(f"Request error: {e}")
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return None
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                return None
        
        return None
    
    async def _get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make a GET request."""
        return await self._request('GET', endpoint, params=params)
    
    async def _post(self, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict]:
        """Make a POST request."""
        # Log the exact data being sent
        import json as json_module
        if data:
            logger.debug(f"POST data (raw): {data}")
            logger.debug(f"POST data (JSON): {json_module.dumps(data)}")
        
        response = await self._request('POST', endpoint, json=data, headers={'Content-Type': 'application/json'})
        
        # Log response type and sample
        if response:
            logger.debug(f"POST response type: {type(response)}")
            if isinstance(response, dict):
                logger.debug(f"POST response has {len(response)} keys")
            elif isinstance(response, list):
                logger.debug(f"POST response has {len(response)} items")
        
        return response
    
    # ========== PLAYER ENDPOINTS ==========
    
    async def get_player_by_discord(self, discord_id: str) -> Optional[Dict]:
        """Get player data by Discord ID."""
        result = await self._post('/players', {'query': [discord_id]})
        if result and isinstance(result, list) and len(result) > 0:
            return result[0]
        return None
    
    async def get_player_by_username(self, username: str) -> Optional[Dict]:
        """Get player data by Minecraft username."""
        result = await self._post('/players', {'query': [username]})
        if result and isinstance(result, list) and len(result) > 0:
            return result[0]
        return None
    
    async def get_player_by_uuid(self, uuid: str) -> Optional[Dict]:
        """Get player data by Minecraft UUID."""
        result = await self._post('/players', {'query': [uuid]})
        if result and isinstance(result, list) and len(result) > 0:
            return result[0]
        return None
    
    async def get_players_by_uuids(self, uuids: List[str]) -> List[Dict]:
        """Get multiple players by UUIDs (batched)."""
        if not uuids:
            return []
        
        # Batch requests (100 per request)
        results = []
        for i in range(0, len(uuids), 100):
            batch = uuids[i:i+100]
            # Send UUIDs directly in query array (strings, not objects)
            batch_results = await self._post('/players', {'query': batch})
            
            if batch_results:
                # Handle different response formats
                if isinstance(batch_results, list):
                    results.extend(batch_results)
                elif isinstance(batch_results, dict):
                    logger.debug(f"Players API returned dict with {len(batch_results)} keys")
                    results.extend(batch_results.values())
        
        return results
    
    # ========== TOWN ENDPOINTS ==========
    
    async def get_town_by_name(self, town_name: str) -> Optional[Dict]:
        """Get town data by name."""
        # Send name directly as string, not as object
        result = await self._post('/towns', {'query': [town_name]})
        if result and isinstance(result, list) and len(result) > 0:
            return result[0]
        return None
    
    async def get_town_by_uuid(self, uuid: str) -> Optional[Dict]:
        """Get town data by UUID."""
        # Send UUID directly as string, not as object
        result = await self._post('/towns', {'query': [uuid]})
        if result and isinstance(result, list) and len(result) > 0:
            return result[0]
        return None
    
    async def get_towns_by_uuids(self, uuids: List[str]) -> List[Dict]:
        """Get multiple towns by UUIDs (batched)."""
        if not uuids:
            return []
        
        results = []
        for i in range(0, len(uuids), 100):
            batch = uuids[i:i+100]
            # Send UUIDs directly as strings, not as objects
            batch_results = await self._post('/towns', {'query': batch})
            
            if batch_results:
                # Detailed logging of response structure
                logger.info(f"Towns batch response type: {type(batch_results)}")
                logger.info(f"Towns batch response: {str(batch_results)[:500]}")
                
                # Handle different response formats
                if isinstance(batch_results, list):
                    # Response is already a list of town objects
                    logger.info(f"Processing {len(batch_results)} towns from list response")
                    for idx, item in enumerate(batch_results):
                        logger.debug(f"Town {idx} type: {type(item)}, value: {str(item)[:100]}")
                    results.extend(batch_results)
                elif isinstance(batch_results, dict):
                    # Response is a dict with UUIDs as keys, extract values
                    logger.info(f"Processing {len(batch_results)} towns from dict response")
                    for key, value in list(batch_results.items())[:3]:  # Log first 3
                        logger.debug(f"Dict key type: {type(key)}, value type: {type(value)}")
                        logger.debug(f"Key: {key}, Value: {str(value)[:100]}")
                    results.extend(batch_results.values())
                else:
                    logger.error(f"Unexpected towns API response type: {type(batch_results)}")
        
        logger.info(f"Returning {len(results)} total towns")
        if results:
            logger.info(f"First result type: {type(results[0])}, value: {str(results[0])[:200]}")
        
        return results
    
    async def get_towns_by_nation(self, nation_name: str) -> List[Dict]:
        """Get all towns in a nation."""
        # First get the nation to get town list
        nation = await self.get_nation_by_name(nation_name)
        if not nation or 'towns' not in nation:
            return []
        
        town_uuids = nation['towns']
        return await self.get_towns_by_uuids(town_uuids)
    
    # ========== NATION ENDPOINTS ==========
    
    async def get_nation_by_name(self, nation_name: str) -> Optional[Dict]:
        """Get nation data by name."""
        if not nation_name or not isinstance(nation_name, str):
            logger.error(f"Invalid nation name: {nation_name} (type: {type(nation_name)})")
            return None
        
        # Strip whitespace and ensure it's a string
        nation_name = str(nation_name).strip()
        
        if not nation_name:
            logger.error("Nation name is empty after stripping")
            return None
        
        logger.debug(f"Querying nation by name: '{nation_name}'")
        
        try:
            # Send name directly as string in query array
            result = await self._post('/nations', {'query': [nation_name]})
            
            if result and isinstance(result, list) and len(result) > 0:
                logger.debug(f"Found nation: {nation_name}")
                return result[0]
            
            logger.debug(f"Nation not found: {nation_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error querying nation {nation_name}: {e}")
            return None
    
    async def get_nation_by_uuid(self, uuid: str) -> Optional[Dict]:
        """Get nation data by UUID."""
        # Send UUID directly as string, not as object
        result = await self._post('/nations', {'query': [uuid]})
        if result and isinstance(result, list) and len(result) > 0:
            return result[0]
        return None
    
    async def get_nations_by_uuids(self, uuids: List[str]) -> List[Dict]:
        """Get multiple nations by UUIDs (batched)."""
        if not uuids:
            return []
        
        results = []
        for i in range(0, len(uuids), 100):
            batch = uuids[i:i+100]
            # Send UUIDs directly as strings, not as objects
            batch_results = await self._post('/nations', {'query': batch})
            
            if batch_results:
                # Handle different response formats
                if isinstance(batch_results, list):
                    results.extend(batch_results)
                elif isinstance(batch_results, dict):
                    logger.debug(f"Nations API returned dict with {len(batch_results)} keys")
                    results.extend(batch_results.values())
        
        return results
    
    async def get_all_nations(self) -> List[Dict]:
        """Get all nations."""
        result = await self._get('/nations')
        return result if result else []
    
    # ========== HEALTH CHECK ==========
    
    async def health_check(self) -> bool:
        """Check if API is available."""
        try:
            result = await self._get('/nations')
            return result is not None
        except Exception:
            return False