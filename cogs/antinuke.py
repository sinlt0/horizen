import discord
from discord.ext import commands
import collections
import time
import datetime

class AntiNuke(commands.Cog):
    category = 'config'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager
        self.nuke_cache = collections.defaultdict(lambda: collections.defaultdict(list))

    async def get_config(self, guild_id):
        return await self.bot.get_config('automod_config', guild_id)

    async def update_config(self, guild_id, data):
        await self.bot.update_config('automod_config', guild_id, data)

    async def get_quarantine_role(self, guild):
        config = await self.get_config(guild.id)
        role_id = config.get('quarantine_role_id')
        role = guild.get_role(role_id) if role_id else None
        if not role:
            role = discord.utils.get(guild.roles, name="Horizen Quarantine")
            if not role:
                try:
                    role = await guild.create_role(name="Horizen Quarantine", color=discord.Color.dark_grey(), reason="Anti-Nuke: Quarantine system setup")
                    try: await role.edit(position=guild.me.top_role.position - 1)
                    except: pass
                    for channel in guild.channels:
                        try: await channel.set_permissions(role, view_channel=False, connect=False)
                        except: continue
                except: return None
            await self.update_config(guild.id, {'quarantine_role_id': role.id})
        return role

    async def check_nuke(self, guild, user, action_type):
        config = await self.get_config(guild.id)
        if not config.get('antinuke_enabled'): return
        if await self.bot.is_extra_owner(user): return
        if await self.bot.is_whitelisted(guild, user, module='antinuke'): return
        
        now = time.time()
        self.nuke_cache[guild.id][user.id] = [t for t in self.nuke_cache[guild.id][user.id] if now - t < 10]
        self.nuke_cache[guild.id][user.id].append(now)
        
        limit_key = f'antinuke_limit_{action_type.lower().replace(" ", "_")}'
        limit = config.get(limit_key, 3)
        
        if len(self.nuke_cache[guild.id][user.id]) >= limit:
            await self.bot.punish_user(guild, user, f"Exceeded {action_type} limit ({limit} in 10s)")

    @commands.group(name='antinuke', aliases=['an'], invoke_without_command=True, help='Configure Wick-level Anti-Nuke protection.')
    @commands.has_permissions(administrator=True)
    async def antinuke_group(self, ctx):
        config = await self.get_config(ctx.guild.id)
        status = '✅ Enabled' if config.get('antinuke_enabled') else '❌ Disabled'
        punishment = config.get('antinuke_punishment', 'quarantine').capitalize()
        panic = '🚨 ACTIVE' if config.get('panic_mode') else '🛡️ Normal'
        
        desc = f"**Status:** {status}\n**Punishment:** {punishment}\n**Server State:** {panic}\n\n**Limits (Actions per 10s):**\n"
        actions = [
            ('Mass Ban', 'mass_ban'), ('Mass Kick', 'mass_kick'), 
            ('Mass Role Delete', 'mass_role_delete'), ('Mass Role Create', 'mass_role_create'),
            ('Mass Channel Delete', 'mass_channel_delete'), ('Mass Channel Create', 'mass_channel_create'),
            ('Mass Webhook Update', 'mass_webhook_update'), ('Bot Add', 'bot_add'),
            ('Mass Emoji Delete', 'mass_emoji_delete'), ('Dangerous Perms', 'dangerous_perms')
        ]
        for label, key in actions:
            l = config.get(f'antinuke_limit_{key}', 3)
            desc += f"• {label}: `{l}`\n"
            
        await ctx.embed(desc, title="Anti-Nuke Dashboard")

    @antinuke_group.command(name='toggle', help='Enable or disable Anti-Nuke protection.')
    @commands.has_permissions(administrator=True)
    async def antinuke_toggle(self, ctx):
        config = await self.get_config(ctx.guild.id)
        new_state = not config.get('antinuke_enabled', False)
        await self.update_config(ctx.guild.id, {'antinuke_enabled': new_state})
        await ctx.success(f"Anti-Nuke has been **{'enabled' if new_state else 'disabled'}**.")

    @antinuke_group.command(name='punishment', help='Set punishment (quarantine/ban).')
    @commands.has_permissions(administrator=True)
    async def antinuke_punishment(self, ctx, p_type: str):
        if p_type.lower() not in ['quarantine', 'ban']: return await ctx.error("Use `quarantine` or `ban`.")
        await self.update_config(ctx.guild.id, {'antinuke_punishment': p_type.lower()})
        await ctx.success(f"Anti-Nuke punishment set to **{p_type.lower()}**.")

    @antinuke_group.command(name='limit', help='Set sensitivity for specific actions.')
    @commands.has_permissions(administrator=True)
    async def antinuke_limit(self, ctx, action: str, limit: int):
        valid = ['ban', 'kick', 'role_delete', 'role_create', 'channel_delete', 'channel_create', 'webhook', 'emoji_delete', 'bot_add', 'dangerous_perms']
        if action.lower() not in valid: return await ctx.error(f"Invalid action. Use: {', '.join(valid)}")
        
        key = f"antinuke_limit_mass_{action.lower()}"
        if action.lower() == 'webhook': key = "antinuke_limit_mass_webhook_update"
        elif action.lower() == 'bot_add': key = "antinuke_limit_bot_add"
        elif action.lower() == 'dangerous_perms': key = "antinuke_limit_dangerous_perms"
        
        await self.update_config(ctx.guild.id, {key: limit})
        await ctx.success(f"Limit for **{action}** set to `{limit}`.")

    @antinuke_group.command(name='panic', help='Toggle server-wide Panic Mode.')
    @commands.has_permissions(administrator=True, manage_guild=True)
    async def antinuke_panic(self, ctx, status: bool):
        await self.update_config(ctx.guild.id, {'panic_mode': status})
        if status:
            await ctx.warning("🚨 **PANIC MODE ACTIVATED** 🚨\nLocking down @everyone permissions...")
            try: await ctx.guild.default_role.edit(permissions=discord.Permissions.none(), reason="Anti-Nuke: Panic Mode Activated")
            except: await ctx.error("Failed to edit @everyone permissions.")
        else:
            await ctx.success("🛡️ Panic Mode deactivated.")

    @antinuke_group.command(name='vanity', help='Enable or disable Vanity URL protection.')
    @commands.has_permissions(administrator=True, manage_guild=True)
    async def antinuke_vanity(self, ctx, status: bool):
        await self.update_config(ctx.guild.id, {'vanity_protection': status})
        await ctx.success(f"Vanity URL protection {'enabled' if status else 'disabled'}.")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if not member.bot: return
        config = await self.get_config(member.guild.id)
        if not config.get('antinuke_enabled'): return
        moderator = None
        try:
            async for entry in member.guild.audit_logs(limit=1, action=discord.AuditLogAction.bot_add):
                if entry.target.id == member.id:
                    moderator = entry.user
                    break
        except: pass
        if moderator: await self.check_nuke(member.guild, moderator, "Bot Add")

    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        config = await self.get_config(after.id)
        if not config.get('antinuke_enabled'): return
        if config.get('vanity_protection') and before.vanity_url_code:
            if before.vanity_url_code != after.vanity_url_code:
                moderator = None
                try:
                    async for entry in after.audit_logs(limit=1, action=discord.AuditLogAction.guild_update):
                        if (discord.utils.utcnow() - entry.created_at).total_seconds() < 10:
                            moderator = entry.user
                            break
                except: pass
                if moderator and not await self.bot.is_extra_owner(moderator):
                    try:
                        await after.edit(vanity_code=before.vanity_url_code, reason="Anti-Nuke: Unauthorized vanity change")
                        await self.bot.punish_user(after, moderator, "Unauthorized Vanity URL Change")
                    except: pass

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if len(before.roles) >= len(after.roles): return
        config = await self.get_config(after.guild.id)
        if not config.get('antinuke_enabled'): return
        new_roles = [r for r in after.roles if r not in before.roles]
        dangerous = ['administrator', 'manage_guild', 'manage_roles', 'manage_channels', 'ban_members', 'kick_members']
        for role in new_roles:
            if any(getattr(role.permissions, p, False) for p in dangerous):
                moderator = None
                try:
                    async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_role_update):
                        if entry.target.id == after.id:
                            moderator = entry.user
                            break
                except: pass
                if moderator and not await self.bot.is_extra_owner(moderator):
                    await self.check_nuke(after.guild, moderator, "Dangerous Perms")
                    try: await after.remove_roles(role, reason="Anti-Nuke: Unauthorized dangerous permission grant")
                    except: pass

async def setup(bot):
    await bot.add_cog(AntiNuke(bot))
