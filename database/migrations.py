"""Database schema initialization and migrations."""

import aiosqlite
import logging
import os
from pathlib import Path

logger = logging.getLogger('EMCBot.Database')


async def init_database(db_path: str = "database.db") -> None:
    """Initialize database schema."""
    
    logger.info(f"Initializing database at {os.path.abspath(db_path)}")
    
    # Ensure database directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    async with aiosqlite.connect(db_path) as db:
        # Create users table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                discord_id TEXT PRIMARY KEY,
                minecraft_uuid TEXT NOT NULL UNIQUE,
                minecraft_ign TEXT NOT NULL,
                town_uuid TEXT,
                town_name TEXT,
                nation_uuid TEXT,
                nation_name TEXT,
                county_uuid TEXT,
                emc_verified BOOLEAN NOT NULL DEFAULT 0,
                verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                verified_by TEXT
            )
        """)
        
        # Create indexes for users
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_minecraft_uuid ON users(minecraft_uuid)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_town_uuid ON users(town_uuid)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_nation_uuid ON users(nation_uuid)
        """)
        
        # Create counties table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS counties (
                county_uuid TEXT PRIMARY KEY,
                county_name TEXT NOT NULL,
                nation_uuid TEXT NOT NULL,
                nation_name TEXT NOT NULL,
                discord_role_id TEXT,
                flag_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_county_nation ON counties(nation_uuid)
        """)
        
        # Create county_towns table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS county_towns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                county_uuid TEXT NOT NULL,
                town_uuid TEXT NOT NULL,
                FOREIGN KEY (county_uuid) REFERENCES counties(county_uuid) ON DELETE CASCADE,
                UNIQUE(county_uuid, town_uuid)
            )
        """)
        
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_county_towns_uuid ON county_towns(town_uuid)
        """)
        
        # Create nation_cache table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS nation_cache (
                nation_uuid TEXT PRIMARY KEY,
                nation_name TEXT NOT NULL,
                last_scanned TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create town_cache table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS town_cache (
                town_uuid TEXT PRIMARY KEY,
                town_name TEXT NOT NULL,
                nation_uuid TEXT,
                mayor_uuid TEXT,
                board TEXT,
                residents TEXT,
                is_public BOOLEAN,
                is_open BOOLEAN,
                is_overclaimed BOOLEAN,
                is_for_sale BOOLEAN,
                has_overclaim_shield BOOLEAN,
                num_town_blocks INTEGER,
                num_residents INTEGER,
                balance REAL,
                last_scanned TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (nation_uuid) REFERENCES nation_cache(nation_uuid)
            )
        """)
        
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_town_nation ON town_cache(nation_uuid)
        """)
        
        # Create audit_log table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                action_type TEXT NOT NULL,
                actor_id TEXT,
                target_discord_id TEXT,
                target_minecraft_uuid TEXT,
                details TEXT,
                success BOOLEAN DEFAULT 1
            )
        """)
        
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action_type)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_target_discord ON audit_log(target_discord_id)
        """)
        
        await db.commit()
        logger.info("Database schema initialized successfully")


async def check_database_version(db_path: str = "database.db") -> str:
    """Check database schema version."""
    
    async with aiosqlite.connect(db_path) as db:
        # Check if all tables exist
        cursor = await db.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            ORDER BY name
        """)
        tables = await cursor.fetchall()
        
        expected_tables = {
            'audit_log', 'counties', 'county_towns', 
            'nation_cache', 'town_cache', 'users'
        }
        
        existing_tables = {table[0] for table in tables}
        
        if expected_tables.issubset(existing_tables):
            return "1.0"
        else:
            missing = expected_tables - existing_tables
            logger.warning(f"Missing tables: {missing}")
            return "incomplete"