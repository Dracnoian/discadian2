"""Periodic scanning cog."""

import discord
from discord.ext import commands, tasks
import logging
import time
from typing import Dict, List, Any
import json

from utils import (
    create_notification_embed,
    determine_roles,
    format_nickname,
    is_main_nation,
    compare_lists,
    detect_milestone
)
from utils.roles import update_roles
from utils.nicknames import set_nickname
from utils.data_processor import prepare_town_for_cache

logger = logging.getLogger('EMCBot.Scanner')


class ScannerCog(commands.Cog):
    """Periodic scanning tasks."""
    
    def __init__(self, bot):
        self.bot = bot
        self.user_scan_task.start()
        self.nation_scan_task.start()
        
    def cog_unload(self):
        """Stop tasks when cog is unloaded."""
        self.user_scan_task.cancel()
        self.nation_scan_task.cancel()
    
    @tasks.loop(seconds=10800)  # 3 hours
    async def user_scan_task(self):
        """Periodic user scan task."""
        try:
            await self.run_user_scan()
        except Exception as e:
            logger.error(f"Error in user scan task: {e}", exc_info=True)
    
    @user_scan_task.before_loop
    async def before_user_scan(self):
        """Wait until bot is ready before starting task."""
        await self.bot.wait_until_ready()
        logger.info("User scan task started")
    
    @tasks.loop(seconds=10)  # 3 hours
    async def nation_scan_task(self):
        """Periodic nation scan task."""
        try:
            await self.run_nation_scan()
        except Exception as e:
            logger.error(f"Error in nation scan task: {e}", exc_info=True)
    
    @nation_scan_task.before_loop
    async def before_nation_scan(self):
        """Wait until bot is ready before starting task."""
        await self.bot.wait_until_ready()
        logger.info("Nation scan task started")
    
    async def run_user_scan(self) -> Dict[str, Any]:
        """Run user verification scan."""
        logger.info("Starting user scan...")
        start_time = time.time()
        changes_detected = 0
        
        try:
            # Get all verified users from database
            users = await self.bot.db.get_all_verified_users()
            logger.info(f"Scanning {len(users)} verified users")
            
            # Get current EMC data for all users
            uuids = [user['minecraft_uuid'] for user in users]
            current_data = await self.bot.batch_handler.get_all_verified_player_data(uuids)
            
            # Create lookup dict
            current_lookup = {p['uuid']: p for p in current_data}
            
            # Check each user for changes
            for user in users:
                mc_uuid = user['minecraft_uuid']
                discord_id = user['discord_id']
                
                # Get current EMC data
                current = current_lookup.get(mc_uuid)
                
                if not current:
                    # Player no longer exists on EMC (unlikely)
                    logger.warning(f"Player {user['minecraft_ign']} no longer on EMC")
                    continue
                
                # Check for changes
                changed = await self._check_user_changes(user, current)
                
                if changed:
                    changes_detected += 1
                    await self._update_user(discord_id, current)
            
            duration = time.time() - start_time
            logger.info(f"User scan complete: {len(users)} scanned, {changes_detected} changes in {duration:.2f}s")
            
            return {
                'scanned': len(users),
                'changes': changes_detected,
                'duration': duration
            }
            
        except Exception as e:
            logger.error(f"Error in user scan: {e}", exc_info=True)
            return {
                'scanned': 0,
                'changes': 0,
                'duration': 0
            }
    
    async def _check_user_changes(self, stored_user: dict, current_data: dict) -> bool:
        """Check if user data has changed."""
        # Get current town/nation
        current_town = current_data.get('town', {})
        current_nation = current_data.get('nation', {})
        
        current_town_uuid = current_town.get('uuid')
        current_nation_uuid = current_nation.get('uuid')
        
        # Check if changed
        changed = (
            stored_user.get('town_uuid') != current_town_uuid or
            stored_user.get('nation_uuid') != current_nation_uuid
        )
        
        return changed
    
    async def _update_user(self, discord_id: str, player_data: dict):
        """Update a user's data and roles."""
        try:
            member = self.bot.guild.get_member(int(discord_id))
            if not member:
                logger.warning(f"Could not find member {discord_id}")
                return
            
            # Get stored data
            stored_user = await self.bot.db.get_user_by_discord(discord_id)
            
            # Extract current data
            town = player_data.get('town', {})
            nation = player_data.get('nation', {})
            
            town_uuid = town.get('uuid')
            town_name = town.get('name')
            nation_uuid = nation.get('uuid')
            nation_name = nation.get('name')
            minecraft_ign = player_data.get('name')
            
            # Determine old and new roles
            old_role_ids = determine_roles(
                stored_user.get('nation_name'),
                stored_user.get('town_uuid'),
                self.bot.config,
                stored_user.get('county_uuid')
            )
            
            new_role_ids = determine_roles(
                nation_name,
                town_uuid,
                self.bot.config
            )
            
            # Get county if in main nation
            county_uuid = None
            if is_main_nation(nation_name, self.bot.config) and town_uuid:
                county_data = await self.bot.db.get_county_for_town(town_uuid)
                if county_data:
                    county_uuid = county_data.get('county_uuid')
            
            # Update roles
            await update_roles(member, old_role_ids, new_role_ids, self.bot.guild)
            
            # Update nickname
            nickname_text = format_nickname(
                minecraft_ign,
                town_name,
                nation_name,
                is_main_nation(nation_name, self.bot.config)
            )
            await set_nickname(member, nickname_text)
            
            # Update database
            updates = {
                'minecraft_ign': minecraft_ign,
                'town_uuid': town_uuid,
                'town_name': town_name,
                'nation_uuid': nation_uuid,
                'nation_name': nation_name,
                'county_uuid': county_uuid
            }
            await self.bot.db.update_user(discord_id, updates)
            
            # Log to audit
            await self.bot.db.add_audit_log({
                'action_type': 'scan_update',
                'actor_id': None,
                'target_discord_id': discord_id,
                'target_minecraft_uuid': stored_user['minecraft_uuid'],
                'details': {
                    'old_town': stored_user.get('town_name'),
                    'new_town': town_name,
                    'old_nation': stored_user.get('nation_name'),
                    'new_nation': nation_name
                },
                'success': True
            })
            
            logger.info(f"Updated user {minecraft_ign}: {stored_user.get('town_name')} → {town_name}")
            
        except Exception as e:
            logger.error(f"Error updating user {discord_id}: {e}", exc_info=True)
    
    async def run_nation_scan(self) -> Dict[str, Any]:
        """Run nation/town scan."""
        logger.info("Starting nation scan...")
        start_time = time.time()
        changes_detected = 0
        
        try:
            # Get main nations from config
            main_nations = self.bot.config.get('main_nations', [])
            
            if not main_nations:
                logger.warning("No main nations configured - skipping nation scan")
                return {
                    'scanned': 0,
                    'changes': 0,
                    'duration': 0
                }
            
            towns_scanned = 0
            
            for nation_config in main_nations:
                # Validate nation config
                if not isinstance(nation_config, dict):
                    logger.error(f"Invalid nation config: {nation_config} (type: {type(nation_config)})")
                    continue
                
                nation_name = nation_config.get('name')
                
                # Validate nation name
                if not nation_name:
                    logger.warning("Nation name is empty or missing - skipping")
                    continue
                
                if not isinstance(nation_name, str):
                    logger.error(f"Nation name is not a string: {nation_name} (type: {type(nation_name)})")
                    continue
                
                nation_name = nation_name.strip()
                
                if not nation_name:
                    logger.warning("Nation name is empty after stripping - skipping")
                    continue
                
                logger.info(f"Processing nation: '{nation_name}'")
                
                try:
                    # Get current nation data
                    logger.debug(f"Querying nation: {nation_name}")
                    nation_data = await self.bot.api.get_nation_by_name(nation_name)
                    
                    if not nation_data:
                        logger.warning(f"Could not find nation {nation_name} - it may not exist on the server")
                        continue
                    
                    nation_uuid = nation_data.get('uuid')
                    if not nation_uuid:
                        logger.warning(f"Nation {nation_name} has no UUID")
                        continue
                    
                    # Update nation cache
                    await self.bot.db.upsert_nation_cache({
                        'uuid': nation_uuid,
                        'name': nation_name
                    })
                    
                    # Get all towns in nation - extract UUIDs from town objects
                    town_data_list = nation_data.get('towns', [])
                    
                    # Extract UUID strings from town objects
                    # The API may return town objects like {"uuid": "...", "name": "..."}
                    # or just UUID strings, so we handle both cases
                    town_uuids = []
                    for town in town_data_list:
                        if isinstance(town, dict):
                            # Town is an object with uuid field
                            uuid = town.get('uuid')
                            if uuid:
                                town_uuids.append(uuid)
                        elif isinstance(town, str):
                            # Town is already a UUID string
                            town_uuids.append(town)
                    
                    towns_scanned += len(town_uuids)
                    
                    if not town_uuids:
                        logger.info(f"Nation {nation_name} has no towns")
                        continue
                    
                    logger.debug(f"Querying {len(town_uuids)} towns for {nation_name}")
                    
                    # Batch query all towns - now with proper UUID strings
                    current_towns = await self.bot.api.get_towns_by_uuids(town_uuids)
                    
                    if not current_towns:
                        logger.warning(f"Could not get town data for {nation_name}")
                        continue
                    
                    # Check each town for changes
                    for town_data in current_towns:
                        try:
                            # Defensive check: ensure town_data is a dict
                            if not isinstance(town_data, dict):
                                logger.error(f"Town data is not a dict! Type: {type(town_data)}, Value: {str(town_data)[:200]}")
                                continue
                            
                            town_uuid = town_data.get('uuid')
                            if not town_uuid:
                                logger.warning(f"Town data has no uuid: {str(town_data)[:200]}")
                                continue
                            
                            town_name = town_data.get('name', 'unknown')
                            
                            # Get cached town data
                            cached = await self.bot.db.get_town_cache(town_uuid)
                            
                            # Detect changes
                            changes = self._detect_town_changes(cached, town_data)
                            
                            if changes:
                                changes_detected += 1
                                await self._send_notifications(town_data, changes)
                            
                            # Update cache - use data processor to format correctly
                            processed_town_data = prepare_town_for_cache(town_data)
                            await self.bot.db.upsert_town_cache(processed_town_data)
                        except Exception as e:
                            town_name = town_data.get('name', 'unknown') if isinstance(town_data, dict) else str(town_data)[:50]
                            logger.error(f"Error processing town {town_name}: {e}")
                            logger.error(f"Town data type: {type(town_data)}, value: {str(town_data)[:200]}")
                            continue
                    
                except Exception as e:
                    logger.error(f"Error scanning nation {nation_name}: {e}", exc_info=True)
                    continue
            
            duration = time.time() - start_time
            logger.info(f"Nation scan complete: {towns_scanned} towns scanned, {changes_detected} changes in {duration:.2f}s")
            
            return {
                'scanned': towns_scanned,
                'changes': changes_detected,
                'duration': duration
            }
            
        except Exception as e:
            logger.error(f"Error in nation scan: {e}", exc_info=True)
            return {
                'scanned': 0,
                'changes': 0,
                'duration': time.time() - start_time
            }
    
    def _detect_town_changes(self, cached: dict, current: dict) -> Dict[str, Any]:
        """Detect changes in town data."""
        if not cached:
            return {}  # New town, don't send notifications
        
        changes = {}
        
        # Government changes
        current_mayor = current.get('mayor', {})
        current_mayor_uuid = current_mayor.get('uuid') if isinstance(current_mayor, dict) else None
        
        if cached.get('mayor_uuid') != current_mayor_uuid:
            changes['mayor'] = (
                cached.get('mayor_uuid'),
                current_mayor_uuid
            )
        
        # Board changes - Note: 'board' in API is a string (town motto/message)
        # Actual board members might be in a different field or not provided
        # Skip board member tracking for now as API structure differs from expected
        
        # Resident changes
        cached_residents = cached.get('residents', [])
        
        # Handle different cached formats safely
        if isinstance(cached_residents, str):
            # Cached data is a JSON string, parse it
            import json
            
            # Check if empty, whitespace, or None
            if not cached_residents or not cached_residents.strip():
                cached_residents = []
            else:
                try:
                    cached_residents = json.loads(cached_residents)
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Failed to parse cached residents JSON: {e}")
                    logger.debug(f"Cached residents value: '{cached_residents}'")
                    cached_residents = []
        elif cached_residents is None:
            cached_residents = []
        
        # Ensure cached_residents is a list
        if not isinstance(cached_residents, list):
            logger.warning(f"Cached residents not a list: {type(cached_residents)}")
            cached_residents = []
        
        # MIGRATION: Handle old cached format where residents were full objects
        # Extract UUIDs from old format if needed
        migrated_cached = []
        for item in cached_residents:
            if isinstance(item, dict):
                # Old format: full resident object
                uuid = item.get('uuid')
                if uuid and isinstance(uuid, str):
                    migrated_cached.append(uuid)
            elif isinstance(item, str):
                # New format: UUID string
                migrated_cached.append(item)
        cached_residents = migrated_cached
        
        # Extract resident UUIDs from current data
        current_residents_data = current.get('residents', [])
        current_residents = []
        
        if isinstance(current_residents_data, list):
            for r in current_residents_data:
                if isinstance(r, dict):
                    uuid = r.get('uuid')
                    if uuid and isinstance(uuid, str):
                        current_residents.append(uuid)
                elif isinstance(r, str):
                    current_residents.append(r)
        
        # Final defensive check: ensure all items are strings
        cached_residents = [str(x) for x in cached_residents if x]
        current_residents = [str(x) for x in current_residents if x]
        
        try:
            resident_diff = compare_lists(cached_residents, current_residents)
            
            if resident_diff['added']:
                changes['residents_added'] = resident_diff['added']
            if resident_diff['removed']:
                changes['residents_removed'] = resident_diff['removed']
        except TypeError as e:
            if 'unhashable' in str(e):
                logger.error(f"Unhashable type error in residents comparison")
                logger.error(f"Cached residents types: {[type(x).__name__ for x in cached_residents[:5]]}")
                logger.error(f"Current residents types: {[type(x).__name__ for x in current_residents[:5]]}")
            else:
                raise
        except Exception as e:
            logger.error(f"Error comparing residents: {e}")
        
        # Status changes
        status = current.get('status', {})
        for key in ['isPublic', 'isOpen', 'isOverClaimed', 'isForSale', 'hasOverclaimShield']:
            snake_key = key[0].lower() + ''.join(['_' + c.lower() if c.isupper() else c for c in key[1:]])
            if cached.get(snake_key) != status.get(key):
                changes[snake_key] = (cached.get(snake_key), status.get(key))
        
        # Milestone changes
        stats = current.get('stats', {})
        thresholds = self.bot.config.get('thresholds', {})
        
        # Population milestone
        old_pop = cached.get('num_residents', 0)
        new_pop = stats.get('numResidents', 0)
        pop_milestone = detect_milestone(old_pop, new_pop, thresholds.get('population', []))
        if pop_milestone:
            changes['population'] = pop_milestone
        
        # Balance milestone
        old_balance = cached.get('balance', 0)
        new_balance = stats.get('balance', 0)
        balance_milestone = detect_milestone(old_balance, new_balance, thresholds.get('balance', []))
        if balance_milestone:
            changes['balance'] = balance_milestone
        
        return changes
    
    async def _send_notifications(self, town_data: dict, changes: Dict[str, Any]):
        """Send notifications for town changes."""
        try:
            # Categorize changes
            government_changes = {}
            status_changes = {}
            milestone_changes = {}
            
            for key, value in changes.items():
                if key in ['mayor', 'board_added', 'board_removed', 'residents_added', 'residents_removed']:
                    government_changes[key] = value
                elif key in ['is_public', 'is_open', 'is_overclaimed', 'is_for_sale', 'has_overclaim_shield']:
                    status_changes[key] = value
                elif key in ['population', 'balance']:
                    milestone_changes[key] = value
            
            # Send government notifications
            if government_changes:
                embed = create_notification_embed('government', town_data, government_changes, self.bot.config)
                if embed:
                    channel = await self.bot.get_notification_channel('government')
                    if channel:
                        await channel.send(embed=embed)
            
            # Send status notifications
            if status_changes:
                embed = create_notification_embed('status', town_data, status_changes, self.bot.config)
                if embed:
                    channel = await self.bot.get_notification_channel('status')
                    if channel:
                        await channel.send(embed=embed)
            
            # Send milestone notifications
            if milestone_changes:
                embed = create_notification_embed('milestone', town_data, milestone_changes, self.bot.config)
                if embed:
                    channel = await self.bot.get_notification_channel('milestones')
                    if channel:
                        await channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error sending notifications: {e}", exc_info=True)


async def setup(bot):
    """Set up the cog."""
    await bot.add_cog(ScannerCog(bot))