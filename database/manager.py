"""Database manager for all database operations."""

import aiosqlite
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from .models import User, County, TownCache, NationCache, AuditLog

logger = logging.getLogger('EMCBot.Database')


class DatabaseManager:
    """Manages all database operations."""
    
    def __init__(self, db_path: str = "./discadian/database.db"):
        """Initialize database manager."""
        self.db_path = db_path
        
    async def _execute(self, query: str, params: tuple = ()) -> aiosqlite.Cursor:
        """Execute a query."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(query, params)
            await db.commit()
            return cursor
    
    async def _fetchone(self, query: str, params: tuple = ()) -> Optional[dict]:
        """Execute query and fetch one result."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, params)
            row = await cursor.fetchone()
            return dict(row) if row else None
    
    async def _fetchall(self, query: str, params: tuple = ()) -> List[dict]:
        """Execute query and fetch all results."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    # ========== USER OPERATIONS ==========
    
    async def add_user(self, user_data: dict) -> bool:
        """Add a new user to the database."""
        try:
            query = """
                INSERT INTO users (
                    discord_id, minecraft_uuid, minecraft_ign, town_uuid, town_name,
                    nation_uuid, nation_name, county_uuid, emc_verified, verified_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                user_data['discord_id'],
                user_data['minecraft_uuid'],
                user_data['minecraft_ign'],
                user_data.get('town_uuid'),
                user_data.get('town_name'),
                user_data.get('nation_uuid'),
                user_data.get('nation_name'),
                user_data.get('county_uuid'),
                user_data.get('emc_verified', False),
                user_data.get('verified_by')
            )
            await self._execute(query, params)
            logger.info(f"Added user {user_data['discord_id']} ({user_data['minecraft_ign']})")
            return True
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            return False
    
    async def get_user_by_discord(self, discord_id: str) -> Optional[dict]:
        """Get user by Discord ID."""
        query = "SELECT * FROM users WHERE discord_id = ?"
        return await self._fetchone(query, (discord_id,))
    
    async def get_user_by_uuid(self, minecraft_uuid: str) -> Optional[dict]:
        """Get user by Minecraft UUID."""
        query = "SELECT * FROM users WHERE minecraft_uuid = ?"
        return await self._fetchone(query, (minecraft_uuid,))
    
    async def update_user(self, discord_id: str, updates: dict) -> bool:
        """Update user information."""
        try:
            # Build UPDATE query dynamically
            set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
            set_clause += ", last_updated = CURRENT_TIMESTAMP"
            
            query = f"UPDATE users SET {set_clause} WHERE discord_id = ?"
            params = tuple(updates.values()) + (discord_id,)
            
            await self._execute(query, params)
            logger.info(f"Updated user {discord_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating user {discord_id}: {e}")
            return False
    
    async def delete_user(self, discord_id: str) -> bool:
        """Delete a user from the database."""
        try:
            query = "DELETE FROM users WHERE discord_id = ?"
            await self._execute(query, (discord_id,))
            logger.info(f"Deleted user {discord_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting user {discord_id}: {e}")
            return False
    
    async def get_all_verified_users(self) -> List[dict]:
        """Get all verified users."""
        query = "SELECT * FROM users ORDER BY verified_at DESC"
        return await self._fetchall(query)
    
    async def get_users_by_town(self, town_uuid: str) -> List[dict]:
        """Get all users in a specific town."""
        query = "SELECT * FROM users WHERE town_uuid = ?"
        return await self._fetchall(query, (town_uuid,))
    
    async def get_users_by_nation(self, nation_uuid: str) -> List[dict]:
        """Get all users in a specific nation."""
        query = "SELECT * FROM users WHERE nation_uuid = ?"
        return await self._fetchall(query, (nation_uuid,))
    
    async def get_users_by_county(self, county_uuid: str) -> List[dict]:
        """Get all users in a specific county."""
        query = "SELECT * FROM users WHERE county_uuid = ?"
        return await self._fetchall(query, (county_uuid,))
    
    # ========== COUNTY OPERATIONS ==========
    
    async def add_county(self, county_data: dict) -> bool:
        """Add a new county."""
        try:
            query = """
                INSERT INTO counties (
                    county_uuid, county_name, nation_uuid, nation_name,
                    discord_role_id, flag_url
                ) VALUES (?, ?, ?, ?, ?, ?)
            """
            params = (
                county_data['county_uuid'],
                county_data['county_name'],
                county_data['nation_uuid'],
                county_data['nation_name'],
                county_data.get('discord_role_id'),
                county_data.get('flag_url')
            )
            await self._execute(query, params)
            logger.info(f"Added county {county_data['county_name']}")
            return True
        except Exception as e:
            logger.error(f"Error adding county: {e}")
            return False
    
    async def get_county(self, county_uuid: str) -> Optional[dict]:
        """Get county by UUID."""
        query = "SELECT * FROM counties WHERE county_uuid = ?"
        return await self._fetchone(query, (county_uuid,))
    
    async def get_counties_by_nation(self, nation_uuid: str) -> List[dict]:
        """Get all counties in a nation."""
        query = "SELECT * FROM counties WHERE nation_uuid = ?"
        return await self._fetchall(query, (nation_uuid,))
    
    async def add_town_to_county(self, county_uuid: str, town_uuid: str) -> bool:
        """Add a town to a county."""
        try:
            query = """
                INSERT OR IGNORE INTO county_towns (county_uuid, town_uuid)
                VALUES (?, ?)
            """
            await self._execute(query, (county_uuid, town_uuid))
            logger.info(f"Added town {town_uuid} to county {county_uuid}")
            return True
        except Exception as e:
            logger.error(f"Error adding town to county: {e}")
            return False
    
    async def remove_town_from_county(self, county_uuid: str, town_uuid: str) -> bool:
        """Remove a town from a county."""
        try:
            query = "DELETE FROM county_towns WHERE county_uuid = ? AND town_uuid = ?"
            await self._execute(query, (county_uuid, town_uuid))
            logger.info(f"Removed town {town_uuid} from county {county_uuid}")
            return True
        except Exception as e:
            logger.error(f"Error removing town from county: {e}")
            return False
    
    async def get_county_for_town(self, town_uuid: str) -> Optional[dict]:
        """Get the county that a town belongs to."""
        query = """
            SELECT c.* FROM counties c
            JOIN county_towns ct ON c.county_uuid = ct.county_uuid
            WHERE ct.town_uuid = ?
        """
        return await self._fetchone(query, (town_uuid,))
    
    async def get_towns_in_county(self, county_uuid: str) -> List[str]:
        """Get all town UUIDs in a county."""
        query = "SELECT town_uuid FROM county_towns WHERE county_uuid = ?"
        results = await self._fetchall(query, (county_uuid,))
        return [row['town_uuid'] for row in results]
    
    # ========== NATION CACHE OPERATIONS ==========
    
    async def upsert_nation_cache(self, nation_data: dict) -> bool:
        """Insert or update nation cache."""
        try:
            query = """
                INSERT INTO nation_cache (nation_uuid, nation_name)
                VALUES (?, ?)
                ON CONFLICT(nation_uuid) DO UPDATE SET
                    nation_name = excluded.nation_name,
                    last_scanned = CURRENT_TIMESTAMP
            """
            await self._execute(query, (nation_data['uuid'], nation_data['name']))
            return True
        except Exception as e:
            logger.error(f"Error upserting nation cache: {e}")
            return False
    
    async def get_nation_cache(self, nation_uuid: str) -> Optional[dict]:
        """Get cached nation data."""
        query = "SELECT * FROM nation_cache WHERE nation_uuid = ?"
        return await self._fetchone(query, (nation_uuid,))
    
    async def get_all_nation_caches(self) -> List[dict]:
        """Get all cached nations."""
        query = "SELECT * FROM nation_cache"
        return await self._fetchall(query)
    
    # ========== TOWN CACHE OPERATIONS ==========
    
    async def upsert_town_cache(self, town_data: dict) -> bool:
        """Insert or update town cache."""
        try:
            query = """
                INSERT INTO town_cache (
                    town_uuid, town_name, nation_uuid, mayor_uuid, board, residents,
                    is_public, is_open, is_overclaimed, is_for_sale, has_overclaim_shield,
                    num_town_blocks, num_residents, balance
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(town_uuid) DO UPDATE SET
                    town_name = excluded.town_name,
                    nation_uuid = excluded.nation_uuid,
                    mayor_uuid = excluded.mayor_uuid,
                    board = excluded.board,
                    residents = excluded.residents,
                    is_public = excluded.is_public,
                    is_open = excluded.is_open,
                    is_overclaimed = excluded.is_overclaimed,
                    is_for_sale = excluded.is_for_sale,
                    has_overclaim_shield = excluded.has_overclaim_shield,
                    num_town_blocks = excluded.num_town_blocks,
                    num_residents = excluded.num_residents,
                    balance = excluded.balance,
                    last_scanned = CURRENT_TIMESTAMP
            """
            params = (
                town_data.get('uuid'),
                town_data.get('name'),
                town_data.get('nation_uuid'),  # ← Already extracted
                town_data.get('mayor_uuid'),  # ← Already extracted
                town_data.get('board'),  # ← Already a string (not JSON)
                town_data.get('residents'),  # ← Already JSON string of UUIDs
                town_data.get('is_public'),  # ← Already extracted
                town_data.get('is_open'),
                town_data.get('is_overclaimed'),
                town_data.get('is_for_sale'),
                town_data.get('has_overclaim_shield'),
                town_data.get('num_town_blocks'),
                town_data.get('num_residents'),
                town_data.get('balance')
            )
            await self._execute(query, params)
            return True
        except Exception as e:
            logger.error(f"Error upserting town cache: {e}")
            return False
    
    async def get_town_cache(self, town_uuid: str) -> Optional[dict]:
        """Get cached town data."""
        result = await self._fetchone("SELECT * FROM town_cache WHERE town_uuid = ?", (town_uuid,))
        if result:
            # Parse JSON fields
            if result.get('board'):
                result['board'] = json.loads(result['board'])
            if result.get('residents'):
                result['residents'] = json.loads(result['residents'])
        return result
    
    async def get_towns_by_nation_cache(self, nation_uuid: str) -> List[dict]:
        """Get all cached towns in a nation."""
        results = await self._fetchall(
            "SELECT * FROM town_cache WHERE nation_uuid = ?",
            (nation_uuid,)
        )
        # Parse JSON fields for each result
        for result in results:
            if result.get('board'):
                result['board'] = json.loads(result['board'])
            if result.get('residents'):
                result['residents'] = json.loads(result['residents'])
        return results
    
    async def get_all_town_caches(self) -> List[dict]:
        """Get all cached towns."""
        results = await self._fetchall("SELECT * FROM town_cache")
        # Parse JSON fields for each result
        for result in results:
            if result.get('board'):
                result['board'] = json.loads(result['board'])
            if result.get('residents'):
                result['residents'] = json.loads(result['residents'])
        return results
    
    async def delete_town_cache(self, town_uuid: str) -> bool:
        """Delete town from cache."""
        try:
            await self._execute("DELETE FROM town_cache WHERE town_uuid = ?", (town_uuid,))
            return True
        except Exception as e:
            logger.error(f"Error deleting town cache: {e}")
            return False
    
    # ========== AUDIT LOG OPERATIONS ==========
    
    async def add_audit_log(self, log_data: dict) -> bool:
        """Add an audit log entry."""
        try:
            query = """
                INSERT INTO audit_log (
                    action_type, actor_id, target_discord_id, target_minecraft_uuid,
                    details, success
                ) VALUES (?, ?, ?, ?, ?, ?)
            """
            params = (
                log_data['action_type'],
                log_data.get('actor_id'),
                log_data.get('target_discord_id'),
                log_data.get('target_minecraft_uuid'),
                json.dumps(log_data.get('details', {})),
                log_data.get('success', True)
            )
            await self._execute(query, params)
            return True
        except Exception as e:
            logger.error(f"Error adding audit log: {e}")
            return False
    
    async def get_audit_logs(self, limit: int = 100, action_type: Optional[str] = None) -> List[dict]:
        """Get audit logs with optional filtering."""
        if action_type:
            query = """
                SELECT * FROM audit_log 
                WHERE action_type = ?
                ORDER BY timestamp DESC 
                LIMIT ?
            """
            results = await self._fetchall(query, (action_type, limit))
        else:
            query = "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?"
            results = await self._fetchall(query, (limit,))
        
        # Parse JSON details
        for result in results:
            if result.get('details'):
                result['details'] = json.loads(result['details'])
        return results
    
    async def get_user_audit_logs(self, discord_id: str, limit: int = 50) -> List[dict]:
        """Get audit logs for a specific user."""
        query = """
            SELECT * FROM audit_log 
            WHERE target_discord_id = ?
            ORDER BY timestamp DESC 
            LIMIT ?
        """
        results = await self._fetchall(query, (discord_id, limit))
        
        # Parse JSON details
        for result in results:
            if result.get('details'):
                result['details'] = json.loads(result['details'])
        return results
