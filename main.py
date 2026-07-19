import discord
from discord.ext import commands, tasks
import os
import asyncio
import threading
import ssl
import datetime
import aiohttp
import random
import traceback

os.environ.setdefault('JISHAKU_HIDE', 'True')
os.environ.setdefault('JISHAKU_NO_UNDERSCORE', 'True')
os.environ.setdefault('JISHAKU_NO_DM_TRACEBACK', 'True')
os.environ.setdefault('JISHAKU_RETAIN', 'True')
os.environ.setdefault('JISHAKU_FORCE_PAGINATOR', 'True')

try:
    import certifi
    ca_file = certifi.where()
except ImportError:
    ca_file = None

try:
    orig_sslc = ssl.create_default_context
    def patched_sslc(*args, **kwargs):
        if ca_file and 'cafile' not in kwargs:
            kwargs['cafile'] = ca_file
        context = orig_sslc(*args, **kwargs)
        context.options |= ssl.OP_NO_SSLv2
        context.options |= ssl.OP_NO_SSLv3
        context.options |= ssl.OP_NO_TLSv1
        context.options |= ssl.OP_NO_TLSv1_1
        try: context.set_ciphers('DEFAULT@SECLEVEL=1')
        except: pass
        return context
    ssl.create_default_context = patched_sslc
except Exception as e:
    print(f"Warning: SSL Patch failed: {e}")

from website.app import run_server
from utils.config import Config
from utils.database import DatabaseManager
from utils.prefix_manager import PrefixManager
from utils.emoji_loader import EmojiManager
from utils.embed_manager import EmbedManager, send_success, send_failure, send_error, send_warning, send_info, send_embed
from utils.dev_manager import DevManager
from utils.premium_manager import PremiumManager
from utils.logger import Logger

Logger.setup()

class AdvancedBot(commands.Bot):

    def __init__(self):
        super().__init__(
            command_prefix=self.get_prefix, 
            intents=discord.Intents.all(), 
            help_command=None, 
            case_insensitive=True,
            strip_after_prefix=True
        )
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        self.prefix_manager = PrefixManager(self.db_manager)
        self.dev_manager = DevManager()
        self._base_owner_ids = set()
        self.premium_manager = PremiumManager(self.db_manager)
        self.emoji_manager = EmojiManager()
        self.e = self.emoji_manager.e
        self.embed_manager = EmbedManager(self)
        self.session = None
        self.uptime = discord.utils.utcnow()
        self._config_cache = {}
        self.change_status.start()
        self._website_started = False

    async def get_config(self, collection, guild_id):
        key = f"{collection}:{guild_id}"
        if key in self._config_cache:
            return self._config_cache[key]
        
        data = await self.db_manager.find_one(collection, {'_id': guild_id})
        self._config_cache[key] = data or {}
        return self._config_cache[key]

    async def update_config(self, collection, guild_id, data, upsert=True):
        await self.db_manager.update_one(collection, {'_id': guild_id}, data, upsert=upsert)
        self.invalidate_config(collection, guild_id)

    def invalidate_config(self, collection, guild_id):
        self._config_cache.pop(f"{collection}:{guild_id}", None)

    async def setup_hook(self):
        await self.db_manager.initialize()
        await self.prefix_manager.initialize_cache()
        self.emoji_manager.load_emojis()
        self.session = aiohttp.ClientSession(headers={'User-Agent': self.config.USER_AGENT})

        owner_ids = await self.refresh_owner_ids()
        print(f'Owner/Dev IDs with elevated access: {owner_ids}')

        try:
            await self.load_extension('jishaku')
            print('Loaded extension: jishaku (owner-only debug/eval tools)')
        except Exception as e:
            print(f'Failed to load jishaku: {e}')

        await self._load_modules('cogs')
        await self._load_modules('events')
        
        from cogs.suggestions import SuggestionVoteView
        from cogs.applications import AppReviewView
        from cogs.ss_checker import SSReviewView
        from cogs.verification import VerificationView
        from cogs.voicemaster import VoiceMasterView
        from cogs.tickets import TicketPanelView, TicketControlView
        
        self.add_view(SuggestionVoteView(self))
        self.add_view(AppReviewView(self))
        self.add_view(SSReviewView(self))
        self.add_view(VerificationView())
        self.add_view(VoiceMasterView())
        self.add_view(TicketPanelView(self))
        self.add_view(TicketControlView(self))

        print(f'Total commands loaded: {self.count_all_commands()}')
        try: await self.tree.sync()
        except Exception as e: print(f'Failed to sync commands: {e}')

    async def refresh_owner_ids(self):
        if not self._base_owner_ids:
            try:
                app_info = await self.application_info()
                if app_info.team:
                    self._base_owner_ids = {m.id for m in app_info.team.members}
                else:
                    self._base_owner_ids = {app_info.owner.id}
            except Exception as e:
                print(f'Failed to fetch application owner info: {e}')
                self._base_owner_ids = set()

        self.owner_id = None
        self.owner_ids = self._base_owner_ids | self.dev_manager.dev_ids
        return self.owner_ids

    def count_all_commands(self):
        total = 0
        def walk(cmd_list):
            nonlocal total
            for cmd in cmd_list:
                total += 1
                if isinstance(cmd, commands.Group):
                    walk(cmd.commands)
        walk(self.commands)
        return total

    async def _load_modules(self, directory):
        if not os.path.exists(directory): return
        for root, dirs, files in os.walk(directory):
            for filename in files:
                if filename.endswith('.py') and (not filename.startswith('__')):
                    relative_path = os.path.relpath(os.path.join(root, filename), '.')
                    module_path = relative_path.replace(os.path.sep, '.')[:-3]
                    try:
                        await self.load_extension(module_path)
                        print(f'Loaded extension: {module_path}')
                    except Exception as e:
                        print(f'Failed to load extension {module_path}: {e}')

    async def close(self):
        if self.session: await self.session.close()
        if self.db_manager: await self.db_manager.close()
        await super().close()

    @tasks.loop(minutes=5)
    async def change_status(self):
        await self.wait_until_ready()
        guild_count = len(self.guilds)
        user_count = sum((guild.member_count for guild in self.guilds))
        activities = [
            discord.Streaming(name='!help | @horizen', url='https://twitch.tv/discord'), 
            discord.Activity(type=discord.ActivityType.watching, name=f'{guild_count} Guilds | {user_count} Users'), 
            discord.Activity(type=discord.ActivityType.listening, name=f'{self.config.DEFAULT_PREFIX}help | @Horizen')
        ]
        await self.change_presence(activity=random.choice(activities))

    async def get_prefix(self, message):
        prefixes = [f'<@!{self.user.id}> ', f'<@{self.user.id}> ']
        if not message.guild:
            prefixes.append(self.config.DEFAULT_PREFIX)
            return prefixes
        guild_prefix = await self.prefix_manager.get_prefix(message.guild.id)
        if guild_prefix: prefixes.append(guild_prefix)
        category_prefixes = await self.prefix_manager.get_all_category_prefixes(message.guild.id)
        prefixes.extend(category_prefixes)
        if await self.prefix_manager.is_no_prefix_user(message.author.id): prefixes.append('')
        seen = set()
        unique = []
        for p in prefixes:
            if p not in seen:
                seen.add(p)
                unique.append(p)
        return unique

    async def get_context(self, message, *, cls=commands.Context):
        context = await super().get_context(message, cls=cls)
        context.e = self.e
        context.success = lambda desc, title='Success', **kwargs: send_success(context, desc, title, **kwargs)
        context.failure = lambda desc, title='Failed', **kwargs: send_failure(context, desc, title, **kwargs)
        context.error = lambda desc, title='Error', **kwargs: send_error(context, desc, title, **kwargs)
        context.warning = lambda desc, title='Warning', **kwargs: send_warning(context, desc, title, **kwargs)
        context.info = lambda desc, title='Information', **kwargs: send_info(context, desc, title, **kwargs)
        context.embed = lambda desc, title=None, color=None, emoji=None, **kwargs: send_embed(context, desc, title, color, emoji, **kwargs)
        context.is_extra_owner = lambda: self.is_extra_owner(context.author)
        async def is_premium():
            status, _ = await self.premium_manager.get_premium_status(message.guild.id) if message.guild else (False, None)
            return status
        context.is_premium = is_premium
        if message.guild and context.valid and context.command:
            used_prefix = await self._get_used_prefix(message, context)
            if used_prefix is not None:
                if not await self._is_prefix_valid_for_command(message.guild.id, used_prefix, context.command):
                    context.valid = False
        return context

    async def _get_used_prefix(self, message, context):
        content = message.content
        user_id = self.user.id
        for m in [f'<@!{user_id}> ', f'<@{user_id}> ']:
            if content.startswith(m): return m
        guild_prefix = await self.prefix_manager.get_prefix(message.guild.id)
        category_prefixes = await self.prefix_manager.get_all_category_prefixes(message.guild.id)
        all_p = ([guild_prefix] if guild_prefix else []) + category_prefixes
        if await self.prefix_manager.is_no_prefix_user(message.author.id): all_p.append('')
        all_p.sort(key=len, reverse=True)
        for p in all_p:
            if p == '' or content.startswith(p): return p
        return None

    async def _is_prefix_valid_for_command(self, guild_id, prefix, command):
        if prefix is None or prefix in [f'<@!{self.user.id}> ', f'<@{self.user.id}> ']: return True
        guild_prefix = await self.prefix_manager.get_prefix(guild_id)
        if prefix == guild_prefix: return True
        cog = command.cog
        command_category = getattr(cog, 'category', None) if cog else None
        category_for_prefix = await self.prefix_manager.get_category_for_prefix(guild_id, prefix)
        if category_for_prefix: return command_category == category_for_prefix
        if prefix == '': return True
        return False

    async def is_extra_owner(self, member: discord.Member):
        if not member.guild: return False
        if member.id == member.guild.owner_id: return True
        config = await self.db_manager.find_one('automod_config', {'_id': member.guild.id})
        return member.id in (config or {}).get('extra_owners', [])

    async def is_whitelisted(self, guild, author, channel=None, module=None):
        if author.id == guild.owner_id: return True
        config = await self.db_manager.find_one('automod_config', {'_id': guild.id})
        if not config: return False
        if author.id in config.get('extra_owners', []) or author.id in config.get('whitelist_global_users', []): return True
        if any(r.id in config.get('whitelist_global_roles', []) for r in author.roles): return True
        if channel and channel.id in config.get('whitelist_global_channels', []): return True
        if module:
            spec = config.get('whitelist_specific', {}).get(module, {})
            if author.id in spec.get('users', []) or any(r.id in spec.get('roles', []) for r in author.roles): return True
            if channel and channel.id in spec.get('channels', []): return True
        return False

    async def punish_user(self, guild, user, reason, punishment=None):
        config = await self.db_manager.find_one('automod_config', {'_id': guild.id})
        if not config: return
        punishment = punishment or config.get('antinuke_punishment', 'quarantine')
        if punishment == 'ban':
            try: await guild.ban(user, reason=f"Horizen Security: {reason}")
            except: pass
        elif punishment == 'quarantine':
            role = guild.get_role(config.get('quarantine_role_id'))
            if role:
                try:
                    removable = [r for r in user.roles if r.name != "@everyone" and not r.managed and r < guild.me.top_role]
                    await user.remove_roles(*removable, reason=f"Horizen Security: {reason}")
                    await user.add_roles(role, reason=f"Horizen Security: {reason}")
                    log_cog = self.get_cog('Logging')
                    if log_cog:
                        embed = discord.Embed(title="🚨 Security Action: Quarantined", description=f"**User:** {user.mention}\n**Reason:** {reason}", color=discord.Color.red(), timestamp=discord.utils.utcnow())
                        await log_cog.log_antinuke(guild, embed)
                except: pass
        elif punishment == 'mute':
            try:
                await user.timeout(discord.utils.utcnow() + datetime.timedelta(minutes=30), reason=f"Horizen Security: {reason}")
                log_cog = self.get_cog('Logging')
                if log_cog:
                    embed = discord.Embed(title="🚨 Security Action: Timeout", description=f"**User:** {user.mention}\n**Reason:** {reason}", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
                    await log_cog.log_automod(guild, embed)
            except: pass

    async def signal_security_event(self, guild, event_type, details):
        if event_type == 'raid_detected':
            if self.get_cog('AntiNuke'):
                await self.db_manager.update_one('automod_config', {'_id': guild.id}, {'panic_mode': True}, upsert=True)
                log_cog = self.get_cog('Logging')
                if log_cog:
                    embed = discord.Embed(title="🚨 PANIC MODE ACTIVATED", description=f"**Reason:** Raid detected by AutoMod Heat Algorithm\n**Details:** {details}", color=discord.Color.dark_red(), timestamp=discord.utils.utcnow())
                    await log_cog.log_antinuke(guild, embed)

    async def signal_verification_success(self, member): self.dispatch('verification_success', member)

    @staticmethod
    def is_owner_or_extra():
        async def predicate(ctx):
            if not ctx.guild: return False
            if await ctx.bot.is_extra_owner(ctx.author): return True
            raise commands.CheckFailure("This command is restricted to the Server Owner and Extra Owners.")
        return commands.check(predicate)

    @staticmethod
    def is_dev():
        async def predicate(ctx):
            if await ctx.bot.is_owner(ctx.author) or ctx.bot.dev_manager.is_dev(ctx.author.id, ctx.bot): return True
            raise commands.NotOwner('This command is restricted to bot developers.')
        return commands.check(predicate)

    async def on_command_error(self, ctx, error):
        if isinstance(error, (commands.CommandNotFound, commands.NotOwner, commands.MissingPermissions, commands.CheckFailure, commands.MissingRequiredArgument, commands.BadArgument)):
            if isinstance(error, commands.CommandNotFound): return
            return await ctx.error(str(error), title='Access Denied' if isinstance(error, (commands.NotOwner, commands.CheckFailure)) else 'Error')
        print(f'Ignoring exception in command {ctx.command}:')
        traceback.print_exception(type(error), error, error.__traceback__)
        try: await ctx.error('An unexpected error occurred.')
        except: pass

    async def on_error(self, event_method, *args, **kwargs):
        print(f'Error in {event_method}:')
        traceback.print_exc()

    async def on_ready(self):
        if not self._website_started:
            print("Spawning website server thread...")
            threading.Thread(target=run_server, args=(self,), daemon=True).start()
            self._website_started = True
        CLR_CYAN, CLR_GREEN, CLR_BLUE, CLR_BOLD, CLR_RESET = '\x1b[36m', '\x1b[32m', '\x1b[34m', '\x1b[1m', '\x1b[0m'
        bot_user, bot_id = str(self.user), str(self.user.id)
        guild_count, cmd_count = len(self.guilds), self.count_all_commands()
        db_type = self.db_manager.primary_type.upper() if self.db_manager else 'UNKNOWN'
        width = 60
        border = '+' + '-' * (width - 2) + '+'
        print('\n' + CLR_CYAN + CLR_BOLD + border + CLR_RESET)
        print(CLR_CYAN + CLR_BOLD + '| ' + ' ' * ((width - 26) // 2) + 'H O R I Z E N   S Y S T E M S' + ' ' * ((width - 25) // 2) + '|' + CLR_RESET)
        print(CLR_CYAN + CLR_BOLD + border + CLR_RESET)
        print(f'{CLR_BLUE}| {CLR_BOLD}ACCOUNT INFO{CLR_RESET}' + ' ' * (width - 15) + CLR_BLUE + '|')
        print(f'|  - Name:     {bot_user:<42} |')
        print(f'|  - ID:       {bot_id:<42} |')
        print(f'|  - Guilds:   {guild_count:<42} |')
        print(f'|  - Commands: {cmd_count:<42} |')
        print(CLR_CYAN + border + CLR_RESET)
        print(f'{CLR_BLUE}| {CLR_BOLD}DATABASE STATUS{CLR_RESET}' + ' ' * (width - 18) + CLR_BLUE + '|')
        print(f'|  - Primary:  {db_type:<42} |')
        sqlite_status = 'Connected' if self.db_manager and self.db_manager.sqlite_conn else 'Disconnected'
        mariadb_status = 'Connected' if self.db_manager and self.db_manager.mariadb_pool else 'Disconnected'
        mongo_status = f'{len(self.db_manager.mongodb_clusters)} Clusters' if self.db_manager else 'Disconnected'
        print(f'|  - SQLite:   {sqlite_status:<42} |')
        print(f'|  - MariaDB:  {mariadb_status:<42} |')
        print(f'|  - MongoDB:  {mongo_status:<42} |')
        print(CLR_CYAN + border + CLR_RESET)
        print(f'{CLR_GREEN}| {CLR_BOLD}SYSTEM READY AND OPERATIONAL{CLR_RESET}' + ' ' * (width - 31) + CLR_GREEN + '|' + CLR_RESET)
        print(CLR_CYAN + border + CLR_RESET + '\n')

async def main():
    async with AdvancedBot() as bot:
        await bot.start(bot.config.DISCORD_TOKEN)

if __name__ == '__main__':
    try:
        import uvloop
        uvloop.install()
        print('uvloop installed — using accelerated event loop.')
    except ImportError:
        print('uvloop not available — using default asyncio event loop.')
    asyncio.run(main())
