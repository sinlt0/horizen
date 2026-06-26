import discord
from discord.ext import commands
import re
import collections
import time
import datetime

class AutoMod(commands.Cog):
    category = 'config'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager
        self.message_cache = collections.defaultdict(list)
        self.duplicate_cache = collections.defaultdict(lambda: collections.deque(maxlen=3))
        self.violation_tracker = collections.defaultdict(list)
        self.heat_tracker = collections.defaultdict(float)
        self.last_heat_update = collections.defaultdict(float)


    async def get_config(self, guild_id):
        return await self.bot.get_config('automod_config', guild_id)

    async def log_automod(self, message, reason):
        log_cog = self.bot.get_cog('Logging')
        if log_cog:
            embed = discord.Embed(
                title='AutoMod Action', 
                description=f'**User:** {message.author.mention} ({message.author.id})\n**Channel:** {message.channel.mention}\n**Reason:** {reason}', 
                color=discord.Color.orange(), 
                timestamp=discord.utils.utcnow()
            )
            await log_cog.log_automod(message.guild, embed)

    async def apply_action(self, message, action, reason):
        await self.bot.punish_user(message.guild, message.author, reason, punishment=action)
        try: await message.delete()
        except: pass
        if action in ['warn', 'mute']:
            try: await message.channel.send(f"{message.author.mention}, you have been handled for: **{reason}**.", delete_after=10)
            except: pass

    @commands.group(name='automod', invoke_without_command=True, help='Configure the advanced AutoMod system.')
    @commands.has_permissions(administrator=True)
    async def automod_group(self, ctx):
        config = await self.get_config(ctx.guild.id)
        desc = "**Bot-Level Filters:**\n"
        keys = ['links', 'invites', 'caps', 'spam', 'badwords', 'stickers', 'zalgo', 'ghostping', 'newaccount', 'images', 'mentions', 'duplicate', 'heat']
        for key in keys:
            status = '✅' if config.get(f'{key}_enabled') else '❌'
            desc += f"{status} {key.capitalize()}\n"
        await ctx.embed(desc, title='AutoMod Configuration')

    @automod_group.command(name='heat', help='Enable or disable the Wick-style Heat Algorithm.')
    @commands.has_permissions(administrator=True)
    async def automod_heat(self, ctx, status: bool):
        await self.bot.update_config('automod_config', ctx.guild.id, {'heat_enabled': status})
        await ctx.success(f"Heat Algorithm {'enabled' if status else 'disabled'}.")

    @automod_group.command(name='links', help='Enable/disable link protection.')
    @commands.has_permissions(administrator=True)
    async def automod_links(self, ctx, status: bool, action: str = 'delete'):
        await self.bot.update_config('automod_config', ctx.guild.id, {'links_enabled': status, 'links_action': action})
        await ctx.success(f"Link protection {'enabled' if status else 'disabled'}.")

    @automod_group.command(name='invites', help='Enable/disable invite protection.')
    @commands.has_permissions(administrator=True)
    async def automod_invites(self, ctx, status: bool, action: str = 'delete'):
        await self.bot.update_config('automod_config', ctx.guild.id, {'invites_enabled': status, 'invites_action': action})
        await ctx.success(f"Invite protection {'enabled' if status else 'disabled'}.")

    @automod_group.command(name='duplicate', help='Enable or disable anti-duplicate protection.')
    @commands.has_permissions(administrator=True)
    async def automod_duplicate(self, ctx, status: bool, action: str = 'delete'):
        await self.bot.update_config('automod_config', ctx.guild.id, {'duplicate_enabled': status, 'duplicate_action': action})
        await ctx.success(f"Anti-duplicate protection {'enabled' if status else 'disabled'}.")

    @automod_group.command(name='caps', help='Enable or disable excessive caps protection.')
    @commands.has_permissions(administrator=True)
    async def automod_caps(self, ctx, status: bool, action: str = 'delete'):
        await self.bot.update_config('automod_config', ctx.guild.id, {'caps_enabled': status, 'caps_action': action})
        await ctx.success(f"Caps protection {'enabled' if status else 'disabled'}.")

    @automod_group.command(name='spam', help='Enable or disable anti-spam protection.')
    @commands.has_permissions(administrator=True)
    async def automod_spam(self, ctx, status: bool):
        await self.bot.update_config('automod_config', ctx.guild.id, {'spam_enabled': status})
        await ctx.success(f"Anti-spam protection {'enabled' if status else 'disabled'}.")

    @automod_group.command(name='ghostping', help='Enable or disable ghost ping detection.')
    @commands.has_permissions(administrator=True)
    async def automod_ghostping(self, ctx, status: bool):
        await self.bot.update_config('automod_config', ctx.guild.id, {'ghostping_enabled': status})
        await ctx.success(f"Ghost ping detection {'enabled' if status else 'disabled'}.")

    @automod_group.command(name='zalgo', help='Enable or disable zalgo text protection.')
    @commands.has_permissions(administrator=True)
    async def automod_zalgo(self, ctx, status: bool, action: str = 'delete'):
        await self.bot.update_config('automod_config', ctx.guild.id, {'zalgo_enabled': status, 'zalgo_action': action})
        await ctx.success(f"Zalgo protection {'enabled' if status else 'disabled'}.")

    @automod_group.command(name='stickers', help='Enable or disable sticker spam protection.')
    @commands.has_permissions(administrator=True)
    async def automod_stickers(self, ctx, status: bool, action: str = 'delete'):
        await self.bot.update_config('automod_config', ctx.guild.id, {'stickers_enabled': status, 'stickers_action': action})
        await ctx.success(f"Sticker protection {'enabled' if status else 'disabled'}.")

    @automod_group.command(name='newaccount', help='Protect from new accounts (age in days).')
    @commands.has_permissions(administrator=True)
    async def automod_newaccount(self, ctx, status: bool, days: int = 7):
        await self.bot.update_config('automod_config', ctx.guild.id, {'newaccount_enabled': status, 'newaccount_days': days})
        await ctx.success(f"New account protection {'enabled' if status else 'disabled'} (Minimum age: {days} days).")

    @automod_group.command(name='images', help='Limit images/attachments per message.')
    @commands.has_permissions(administrator=True)
    async def automod_images(self, ctx, status: bool, limit: int = 5):
        await self.bot.update_config('automod_config', ctx.guild.id, {'images_enabled': status, 'images_limit': limit})
        await ctx.success(f"Image limit {'enabled' if status else 'disabled'} (Limit: {limit}).")

    @automod_group.command(name='mentions', help='Bot-level mention limit protection.')
    @commands.has_permissions(administrator=True)
    async def automod_mentions(self, ctx, status: bool, limit: int = 5, action: str = 'delete'):
        await self.bot.update_config('automod_config', ctx.guild.id, {'mentions_enabled': status, 'mentions_limit': limit, 'mentions_action': action})
        await ctx.success(f"Mention protection {'enabled' if status else 'disabled'} (Limit: {limit}).")

    @automod_group.command(name='badwords', help='Manage the bad words list.')
    @commands.has_permissions(administrator=True)
    async def automod_badwords(self, ctx, *, words: str = None):
        config = await self.get_config(ctx.guild.id)
        bw = config.get('badwords', [])
        if not words: return await ctx.info(f"Current bad words: {', '.join(bw) if bw else 'None'}")
        new_words = [w.strip().lower() for w in words.split(',')]
        for w in new_words:
            if w in bw: bw.remove(w)
            else: bw.append(w)
        await self.bot.update_config('automod_config', ctx.guild.id, {'badwords': bw, 'badwords_enabled': True})
        await ctx.success("Bad words list updated.")

    @automod_group.command(name='native', help='Configure Discord native AutoMod rules.')
    @commands.has_permissions(administrator=True, manage_guild=True)
    async def automod_native(self, ctx, rule_type: str, *, keywords: str = None):
        rule_type = rule_type.lower()
        if rule_type == 'spam':
            await ctx.guild.create_automod_rule(name='Horizen Native Spam Filter', event_type=discord.AutoModRuleEventType.message_send, trigger_type=discord.AutoModRuleTriggerType.spam, actions=[discord.AutoModRuleAction(type=discord.AutoModRuleActionType.block_message)])
            await ctx.success("Created native Discord spam filter.")
        elif rule_type == 'mentions':
            await ctx.guild.create_automod_rule(name='Horizen Native Mention Filter', event_type=discord.AutoModRuleEventType.message_send, trigger_type=discord.AutoModRuleTriggerType.mention_spam, trigger_metadata=discord.AutoModTriggerMetadata(mention_total_limit=5), actions=[discord.AutoModRuleAction(type=discord.AutoModRuleActionType.block_message)])
            await ctx.success("Created native Discord mention filter.")
        elif rule_type == 'keyword':
            if not keywords: return await ctx.error("Please provide keywords separated by commas.")
            kw_list = [k.strip() for k in keywords.split(',')]
            await ctx.guild.create_automod_rule(name='Horizen Native Keyword Filter', event_type=discord.AutoModRuleEventType.message_send, trigger_type=discord.AutoModRuleTriggerType.keyword, trigger_metadata=discord.AutoModTriggerMetadata(keyword_filter=kw_list), actions=[discord.AutoModRuleAction(type=discord.AutoModRuleActionType.block_message)])
            await ctx.success(f"Created native keyword filter for: {', '.join(kw_list)}")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild: return
        if message.author.guild_permissions.manage_messages: return
        config = await self.get_config(message.guild.id)
        if not config: return
        if await self.bot.is_whitelisted(message.guild, message.author, message.channel): return
        content = message.content.lower()

        if config.get('heat_enabled'):
            now = time.time()
            elapsed = now - self.last_heat_update[message.author.id]
            self.heat_tracker[message.author.id] = max(0.0, self.heat_tracker[message.author.id] - (elapsed * 5.0))
            self.last_heat_update[message.author.id] = now
            added_heat = 10.0
            if message.mentions: added_heat += len(message.mentions) * 15.0
            if 'http' in content: added_heat += 20.0
            if len(message.content) > 200: added_heat += 15.0
            self.heat_tracker[message.author.id] += added_heat
            if self.heat_tracker[message.author.id] >= 100.0:
                self.heat_tracker[message.author.id] = 0.0
                await self.bot.signal_security_event(message.guild, 'raid_detected', f"User {message.author} reached 100% Heat.")
                return await self.apply_action(message, 'mute', 'Excessive Activity (Heat)')

        if config.get('newaccount_enabled') and not await self.bot.is_whitelisted(message.guild, message.author, message.channel, 'newaccount'):
            age = (discord.utils.utcnow() - message.author.created_at).days
            if age < config.get('newaccount_days', 7):
                return await self.apply_action(message, 'delete', f'Account too young ({age} days)')
        if config.get('images_enabled') and not await self.bot.is_whitelisted(message.guild, message.author, message.channel, 'images'):
            if len(message.attachments) > config.get('images_limit', 5):
                return await self.apply_action(message, 'delete', 'Too many attachments')
        if config.get('mentions_enabled') and not await self.bot.is_whitelisted(message.guild, message.author, message.channel, 'mentions'):
            if (len(message.mentions) + len(message.role_mentions)) > config.get('mentions_limit', 5):
                return await self.apply_action(message, config.get('mentions_action', 'delete'), 'Too many mentions')
        if config.get('invites_enabled') and not await self.bot.is_whitelisted(message.guild, message.author, message.channel, 'invites'):
            if 'discord.gg/' in content or 'discord.com/invite/' in content:
                codes = re.findall(r'(?:discord\.gg/|discord\.com/invite/)([a-zA-Z0-9-]+)', content)
                whitelisted = config.get('whitelist_invites', [])
                if any(c not in whitelisted for c in codes):
                    return await self.apply_action(message, config.get('invites_action', 'delete'), 'Sending Invites')
        if config.get('links_enabled') and not await self.bot.is_whitelisted(message.guild, message.author, message.channel, 'links'):
            urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', content)
            if urls:
                whitelisted = config.get('whitelist_links', [])
                if any(not any(w in u for w in whitelisted) for u in urls):
                    return await self.apply_action(message, config.get('links_action', 'delete'), 'Sending Links')
        if config.get('caps_enabled') and not await self.bot.is_whitelisted(message.guild, message.author, message.channel, 'caps'):
            if len(message.content) > 10 and sum(1 for c in message.content if c.isupper()) / len(message.content) > 0.7:
                return await self.apply_action(message, config.get('caps_action', 'delete'), 'Excessive Caps')
        if config.get('badwords_enabled') and not await self.bot.is_whitelisted(message.guild, message.author, message.channel, 'badwords'):
            for word in config.get('badwords', []):
                if word in content:
                    return await self.apply_action(message, 'delete', 'Prohibited Words')
        if config.get('zalgo_enabled') and not await self.bot.is_whitelisted(message.guild, message.author, message.channel, 'zalgo'):
            if re.search(r'[\u0300-\u036F\u0483-\u0489\u1DC0-\u1DFF\u20D0-\u20FF\uFE20-\uFE2F]{3,}', message.content):
                return await self.apply_action(message, config.get('zalgo_action', 'delete'), 'Zalgo Text')
        if config.get('stickers_enabled') and not await self.bot.is_whitelisted(message.guild, message.author, message.channel, 'stickers'):
            if message.stickers:
                return await self.apply_action(message, config.get('stickers_action', 'delete'), 'Sending Stickers')
        if config.get('duplicate_enabled') and not await self.bot.is_whitelisted(message.guild, message.author, message.channel, 'duplicate'):
            if len(message.content) > 10:
                self.duplicate_cache[message.author.id].append(message.content)
                if len(self.duplicate_cache[message.author.id]) == 3 and len(set(self.duplicate_cache[message.author.id])) == 1:
                    return await self.apply_action(message, config.get('duplicate_action', 'delete'), 'Duplicate Messages')
        if config.get('spam_enabled') and not await self.bot.is_whitelisted(message.guild, message.author, message.channel, 'spam'):
            now = time.time()
            self.message_cache[message.author.id] = [t for t in self.message_cache[message.author.id] if now - t < 5]
            self.message_cache[message.author.id].append(now)
            if len(self.message_cache[message.author.id]) > 5:
                return await self.apply_action(message, 'mute', 'Spamming Messages')

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot or not message.guild: return
        if not message.mentions: return
        config = await self.get_config(message.guild.id)
        if config.get('ghostping_enabled') and not await self.bot.is_whitelisted(message.guild, message.author, message.channel, 'ghostping'):
            embed = discord.Embed(title='Ghost Ping Detected', description=f'**User:** {message.author.mention}\n**Pings:** {" ".join(m.mention for m in message.mentions)}', color=discord.Color.red(), timestamp=discord.utils.utcnow())
            await message.channel.send(embed=embed, delete_after=15)

async def setup(bot):
    await bot.add_cog(AutoMod(bot))
