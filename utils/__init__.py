"""Utility functions module."""

from .embeds import (
    create_verification_embed,
    create_notification_embed,
    create_purge_confirmation_embed,
    create_scan_status_embed
)
from .roles import determine_roles, get_county_roles
from .nicknames import format_nickname
from .validators import (
    validate_discord_id,
    validate_minecraft_username,
    sanitize_nickname
)
from .helpers import (
    format_timestamp,
    parse_timestamp,
    get_avatar_url,
    detect_milestone,
    compare_lists,
    is_main_nation,
    is_allied_nation,
    get_nation_flag_url
)

__all__ = [
    'create_verification_embed',
    'create_notification_embed',
    'create_purge_confirmation_embed',
    'create_scan_status_embed',
    'determine_roles',
    'get_county_roles',
    'format_nickname',
    'validate_discord_id',
    'validate_minecraft_username',
    'sanitize_nickname',
    'format_timestamp',
    'parse_timestamp',
    'get_avatar_url',
    'detect_milestone',
    'compare_lists',
    'is_main_nation',
    'is_allied_nation',
    'get_nation_flag_url'
]