"""Batch query handler for efficient API requests."""

import logging
from typing import List, Dict, Any
from .earthmc import EarthMCAPI

logger = logging.getLogger('EMCBot.API.Batch')


class BatchQueryHandler:
    """Handles batch queries to the EarthMC API."""
    
    def __init__(self, api_client: EarthMCAPI):
        """Initialize batch handler."""
        self.api = api_client
        self.batch_size = 100
    
    async def batch_player_queries(self, player_identifiers: List[Dict[str, str]]) -> List[Dict]:
        """Batch query players.
        
        Args:
            player_identifiers: List of dicts with 'uuid', 'name', or 'discord' keys
            
        Returns:
            List of player data dictionaries
        """
        if not player_identifiers:
            return []
        
        results = []
        for i in range(0, len(player_identifiers), self.batch_size):
            batch = player_identifiers[i:i+self.batch_size]
            logger.debug(f"Querying player batch {i//self.batch_size + 1} ({len(batch)} players)")
            
            batch_results = await self.api._post('/players', {'query': batch})
            if batch_results:
                results.extend(batch_results)
        
        logger.info(f"Queried {len(player_identifiers)} players, got {len(results)} results")
        return results
    
    async def batch_town_queries(self, town_identifiers: List[Dict[str, str]]) -> List[Dict]:
        """Batch query towns.
        
        Args:
            town_identifiers: List of dicts with 'uuid' or 'name' keys
            
        Returns:
            List of town data dictionaries
        """
        if not town_identifiers:
            return []
        
        results = []
        for i in range(0, len(town_identifiers), self.batch_size):
            batch = town_identifiers[i:i+self.batch_size]
            logger.debug(f"Querying town batch {i//self.batch_size + 1} ({len(batch)} towns)")
            
            batch_results = await self.api._post('/towns', {'query': batch})
            if batch_results:
                results.extend(batch_results)
        
        logger.info(f"Queried {len(town_identifiers)} towns, got {len(results)} results")
        return results
    
    async def batch_nation_queries(self, nation_identifiers: List[Dict[str, str]]) -> List[Dict]:
        """Batch query nations.
        
        Args:
            nation_identifiers: List of dicts with 'uuid' or 'name' keys
            
        Returns:
            List of nation data dictionaries
        """
        if not nation_identifiers:
            return []
        
        results = []
        for i in range(0, len(nation_identifiers), self.batch_size):
            batch = nation_identifiers[i:i+self.batch_size]
            logger.debug(f"Querying nation batch {i//self.batch_size + 1} ({len(batch)} nations)")
            
            batch_results = await self.api._post('/nations', {'query': batch})
            if batch_results:
                results.extend(batch_results)
        
        logger.info(f"Queried {len(nation_identifiers)} nations, got {len(results)} results")
        return results
    
    async def get_all_verified_player_data(self, minecraft_uuids: List[str]) -> List[Dict]:
        """Get data for all verified players by UUID.
        
        Args:
            minecraft_uuids: List of Minecraft UUIDs
            
        Returns:
            List of player data dictionaries
        """
        queries = [{'uuid': uuid} for uuid in minecraft_uuids]
        return await self.batch_player_queries(queries)
    
    async def get_all_nation_towns(self, nation_uuid: str) -> List[Dict]:
        """Get all towns in a nation.
        
        Args:
            nation_uuid: Nation UUID
            
        Returns:
            List of town data dictionaries
        """
        # First get nation data
        nation = await self.api.get_nation_by_uuid(nation_uuid)
        if not nation or 'towns' not in nation:
            return []
        
        # Then batch query all towns
        town_queries = [{'uuid': uuid} for uuid in nation['towns']]
        return await self.batch_town_queries(town_queries)
