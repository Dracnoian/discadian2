"""Data models for database tables."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    """User verification record."""
    discord_id: str
    minecraft_uuid: str
    minecraft_ign: str
    town_uuid: Optional[str] = None
    town_name: Optional[str] = None
    nation_uuid: Optional[str] = None
    nation_name: Optional[str] = None
    county_uuid: Optional[str] = None
    emc_verified: bool = False
    verified_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    verified_by: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'discord_id': self.discord_id,
            'minecraft_uuid': self.minecraft_uuid,
            'minecraft_ign': self.minecraft_ign,
            'town_uuid': self.town_uuid,
            'town_name': self.town_name,
            'nation_uuid': self.nation_uuid,
            'nation_name': self.nation_name,
            'county_uuid': self.county_uuid,
            'emc_verified': self.emc_verified,
            'verified_at': self.verified_at,
            'last_updated': self.last_updated,
            'verified_by': self.verified_by
        }


@dataclass
class County:
    """County definition."""
    county_uuid: str
    county_name: str
    nation_uuid: str
    nation_name: str
    discord_role_id: Optional[str] = None
    flag_url: Optional[str] = None
    created_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'county_uuid': self.county_uuid,
            'county_name': self.county_name,
            'nation_uuid': self.nation_uuid,
            'nation_name': self.nation_name,
            'discord_role_id': self.discord_role_id,
            'flag_url': self.flag_url,
            'created_at': self.created_at
        }


@dataclass
class NationCache:
    """Cached nation data."""
    nation_uuid: str
    nation_name: str
    last_scanned: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'nation_uuid': self.nation_uuid,
            'nation_name': self.nation_name,
            'last_scanned': self.last_scanned
        }


@dataclass
class TownCache:
    """Cached town data."""
    town_uuid: str
    town_name: str
    nation_uuid: Optional[str] = None
    mayor_uuid: Optional[str] = None
    board: Optional[str] = None  # JSON string
    residents: Optional[str] = None  # JSON string
    is_public: Optional[bool] = None
    is_open: Optional[bool] = None
    is_overclaimed: Optional[bool] = None
    is_for_sale: Optional[bool] = None
    has_overclaim_shield: Optional[bool] = None
    num_town_blocks: Optional[int] = None
    num_residents: Optional[int] = None
    balance: Optional[float] = None
    last_scanned: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'town_uuid': self.town_uuid,
            'town_name': self.town_name,
            'nation_uuid': self.nation_uuid,
            'mayor_uuid': self.mayor_uuid,
            'board': self.board,
            'residents': self.residents,
            'is_public': self.is_public,
            'is_open': self.is_open,
            'is_overclaimed': self.is_overclaimed,
            'is_for_sale': self.is_for_sale,
            'has_overclaim_shield': self.has_overclaim_shield,
            'num_town_blocks': self.num_town_blocks,
            'num_residents': self.num_residents,
            'balance': self.balance,
            'last_scanned': self.last_scanned
        }


@dataclass
class AuditLog:
    """Audit log entry."""
    id: Optional[int] = None
    timestamp: Optional[datetime] = None
    action_type: str = ""
    actor_id: Optional[str] = None
    target_discord_id: Optional[str] = None
    target_minecraft_uuid: Optional[str] = None
    details: Optional[str] = None  # JSON string
    success: bool = True

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'timestamp': self.timestamp,
            'action_type': self.action_type,
            'actor_id': self.actor_id,
            'target_discord_id': self.target_discord_id,
            'target_minecraft_uuid': self.target_minecraft_uuid,
            'details': self.details,
            'success': self.success
        }
