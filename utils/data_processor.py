"""Helper functions for processing EarthMC API data."""

import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger('EMCBot.DataProcessor')


def prepare_town_for_cache(town_data: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare town data from API for database storage.
    
    The API returns:
    - board: string (town motto/message)
    - residents: list of objects [{'name': '...', 'uuid': '...'}, ...]
    
    We need to store:
    - board: string as-is (NOT JSON serialized)
    - residents: JSON list of UUID strings
    
    Args:
        town_data: Raw town data from API
        
    Returns:
        Processed town data ready for database
    """
    # Extract basic info
    town_uuid = town_data.get('uuid')
    town_name = town_data.get('name')
    
    # Extract nation info
    nation = town_data.get('nation', {})
    nation_uuid = nation.get('uuid') if isinstance(nation, dict) else None
    
    # Extract mayor info
    mayor = town_data.get('mayor', {})
    mayor_uuid = mayor.get('uuid') if isinstance(mayor, dict) else None
    
    # Board is a string (town motto), not a list
    board_message = town_data.get('board', '')
    
    # Extract resident UUIDs from list of objects
    residents_data = town_data.get('residents', [])
    resident_uuids = []
    
    if isinstance(residents_data, list):
        for resident in residents_data:
            if isinstance(resident, dict):
                uuid = resident.get('uuid')
                if uuid:
                    resident_uuids.append(uuid)
            elif isinstance(resident, str):
                # Already a UUID string
                resident_uuids.append(resident)
    
    # Extract status flags
    status = town_data.get('status', {})
    is_public = status.get('isPublic')
    is_open = status.get('isOpen')
    is_overclaimed = status.get('isOverClaimed')
    is_for_sale = status.get('isForSale')
    has_overclaim_shield = status.get('hasOverclaimShield')
    
    # Extract stats
    stats = town_data.get('stats', {})
    num_town_blocks = stats.get('numTownBlocks')
    num_residents = stats.get('numResidents')
    balance = stats.get('balance')
    
    return {
        'uuid': town_uuid,
        'name': town_name,
        'nation_uuid': nation_uuid,
        'mayor_uuid': mayor_uuid,
        'board': board_message or '',  # Ensure string, not None
        'residents': json.dumps(resident_uuids) if resident_uuids else '[]',  # Always valid JSON
        'is_public': is_public,
        'is_open': is_open,
        'is_overclaimed': is_overclaimed,
        'is_for_sale': is_for_sale,
        'has_overclaim_shield': has_overclaim_shield,
        'num_town_blocks': num_town_blocks,
        'num_residents': num_residents,
        'balance': balance
    }