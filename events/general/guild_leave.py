import discord
from discord.ext import commands
import asyncio

GUILD_COLLECTIONS = [
    'guild_prefixes', 'guild_premium', 'automod_config', 'mod_config',
    'logging_config', 'verification_config', 'voicemaster_config', 'voicemaster_channels',
    'greetings_config', 'autorole_config', 'afk_config', 'ticket_config', 'active_tickets',
    'booster_config', 'leveling_config', 'customization_config', 'giveaways',
    'suggestions_config', 'starboard_config', 'app_configs', 'ss_checker_config',
    'music_config', 'invite_config', 'status_reward_config', 'social_alerts',
    'stats_config', 'antinuke_config', 'custom_commands', 'reaction_roles',
    'bump_config', 'birthday_config', 'counting_config', 'confession_config',
    'reputation_config', 'server_analytics', 'mod_notes', 'sticky_messages',
    'scheduled_messages',
]

USER_KEYED_COLLECTIONS = [
    'users_xp', 'booster_users', 'active_tickets_count', 'afk_users',
    'joined_members_map', 'status_reward_data', 'ss_hashes', 'mod_cases',
    'starboard_messages', 'submitted_apps', 'invite_data', 'suggestions',
    'reputation',
]


class GuildLeave(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        print(f'Bot left guild {guild.name} ({guild.id}). Cleaning up data...')

        music_cog = self.bot.get_cog('Music')
        if music_cog:
            lofi = music_cog._lofi_players.pop(guild.id, None)
            if lofi:
                try:
                    await lofi.stop()
                except Exception:
                    pass
            vc = guild.voice_client
            if vc:
                try:
                    await vc.disconnect(force=True)
                except Exception:
                    pass

        for collection in GUILD_COLLECTIONS:
            try:
                await self.db.delete_one(collection, {'_id': guild.id})
            except Exception as e:
                print(f'Guild leave cleanup: failed to delete {collection} for {guild.id}: {e}')

        for collection in USER_KEYED_COLLECTIONS:
            try:
                docs = await self.db.find(collection, {'guild_id': guild.id})
                for doc in docs:
                    await self.db.delete_one(collection, {'_id': doc['_id']})
            except Exception as e:
                print(f'Guild leave cleanup: failed to delete user docs in {collection} for {guild.id}: {e}')

        try:
            from utils.prefix_manager import PrefixManager
            if hasattr(self.bot, 'prefix_manager'):
                self.bot.prefix_manager._cache.pop(guild.id, None)
        except Exception:
            pass

        cog_caches = [
            ('AutoMod', '_heat_cache'),
            ('AntiNuke', '_action_cache'),
            ('InviteTracker', '_invite_cache'),
            ('Counting', '_cache'),
            ('CustomCommands', '_cache'),
            ('CustomCommands', '_groups'),
            ('ReactionRoles', '_cache'),
            ('ReputationSystem', '_msg_counter'),
        ]
        for cog_name, attr in cog_caches:
            cog = self.bot.get_cog(cog_name)
            if cog and hasattr(cog, attr):
                try:
                    getattr(cog, attr).pop(guild.id, None)
                except Exception:
                    pass

        print(f'Guild leave cleanup complete for {guild.name} ({guild.id}).')


async def setup(bot):
    await bot.add_cog(GuildLeave(bot))
