import discord
from discord.ext import commands
import aiohttp
import datetime

class Logging(commands.Cog):
    category = "logging"

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager
        self.invite_cache = {}
        self.bot.loop.create_task(self._cache_all_invites())

    async def _cache_all_invites(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            try:
                self.invite_cache[guild.id] = await guild.invites()
            except: pass

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        if invite.guild.id not in self.invite_cache: self.invite_cache[invite.guild.id] = []
        self.invite_cache[invite.guild.id].append(invite)
        embed = discord.Embed(title="Invite Created", color=discord.Color.green(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Code", value=f"`{invite.code}`")
        embed.add_field(name="Creator", value=f"{invite.inviter.mention if invite.inviter else 'Unknown'}")
        await self._send_log(invite.guild, 'invites', embed)

    async def on_invite_delete(self, invite):
        if invite.guild.id in self.invite_cache:
            self.invite_cache[guild.id] = [i for i in self.invite_cache[guild.id] if i.code != invite.code]
        embed = discord.Embed(title="Invite Deleted", color=discord.Color.red(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Code", value=f"`{invite.code}`")
        await self._send_log(invite.guild, 'invites', embed)

    async def get_config(self, guild_id):
        return await self.bot.get_config('logging_config', guild_id)

    async def update_config(self, guild_id, data):
        await self.bot.update_config('logging_config', guild_id, data)

    async def _send_log(self, guild, event_type, embed):
        if not guild: return
        config = await self.get_config(guild.id)
        if not config or not config.get("events"): return
        
        evt = config["events"].get(event_type)
        if not evt or not evt.get("enabled", True): return
        
        webhook_url = evt.get("webhook_url")
        if not webhook_url: return

        try:
            webhook = discord.Webhook.from_url(webhook_url, session=self.bot.session)
            await webhook.send(embed=embed, username="Horizen Logging", avatar_url=self.bot.user.display_avatar.url)
        except: pass

    async def log_mod(self, guild, embed): await self._send_log(guild, 'mod', embed)
    async def log_antinuke(self, guild, embed): await self._send_log(guild, 'antinuke', embed)
    async def log_automod(self, guild, embed): await self._send_log(guild, 'automod', embed)
    async def log_tickets(self, guild, embed, file=None): 
        if not guild: return
        config = await self.get_config(guild.id)
        if not config or not config.get("events"): return
        evt = config["events"].get('tickets')
        if not evt or not evt.get("enabled", True) or not evt.get("webhook_url"): return
        try:
            webhook = discord.Webhook.from_url(evt['webhook_url'], session=self.bot.session)
            await webhook.send(embed=embed, file=file, username="Horizen Logging", avatar_url=self.bot.user.display_avatar.url)
        except: pass
    
    async def log_apps(self, guild, embed): await self._send_log(guild, 'apps', embed)
    async def log_giveaways(self, guild, embed): await self._send_log(guild, 'giveaways', embed)
    async def log_suggestions(self, guild, embed): await self._send_log(guild, 'suggestions', embed)
    async def log_verification(self, guild, embed): await self._send_log(guild, 'verification', embed)

    # --- Message Events ---
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot or not message.guild: return
        embed = discord.Embed(title="Message Deleted", color=discord.Color.red(), timestamp=discord.utils.utcnow())
        embed.set_author(name=f"{message.author}", icon_url=message.author.display_avatar.url)
        embed.add_field(name="Channel", value=message.channel.mention)
        embed.add_field(name="Content", value=message.content[:1024] or "No text content", inline=False)
        embed.set_footer(text=f"User ID: {message.author.id}")
        await self._send_log(message.guild, 'messages', embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot or not before.guild or before.content == after.content: return
        embed = discord.Embed(title="Message Edited", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
        embed.set_author(name=f"{before.author}", icon_url=before.author.display_avatar.url)
        embed.add_field(name="Channel", value=before.channel.mention)
        embed.add_field(name="Before", value=before.content[:1024], inline=False)
        embed.add_field(name="After", value=after.content[:1024], inline=False)
        embed.set_footer(text=f"User ID: {before.author.id}")
        await self._send_log(before.guild, 'messages', embed)

    # --- Member Events ---
    @commands.Cog.listener()
    async def on_member_join(self, member):
        inviter_text = "Unknown"
        if member.guild.id in self.invite_cache:
            try:
                new_invites = await member.guild.invites()
                for old in self.invite_cache[member.guild.id]:
                    for new in new_invites:
                        if old.code == new.code and new.uses > old.uses:
                            inviter_text = f"{new.inviter.mention} ({new.code})"
                            break
                self.invite_cache[member.guild.id] = new_invites
            except: pass

        embed = discord.Embed(title="Member Joined", color=discord.Color.green(), timestamp=discord.utils.utcnow())
        embed.set_author(name=f"{member}", icon_url=member.display_avatar.url)
        embed.add_field(name="Account Created", value=f"<t:{int(member.created_at.timestamp())}:R>")
        embed.add_field(name="Invited By", value=inviter_text)
        embed.set_footer(text=f"Member ID: {member.id}")
        await self._send_log(member.guild, 'members', embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        embed = discord.Embed(title="Member Left", color=discord.Color.red(), timestamp=discord.utils.utcnow())
        embed.set_author(name=f"{member}", icon_url=member.display_avatar.url)
        roles = [r.mention for r in member.roles if not r.is_default()]
        if roles: embed.add_field(name="Roles", value=" ".join(roles[:20]))
        embed.set_footer(text=f"Member ID: {member.id}")
        await self._send_log(member.guild, 'members', embed)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        # Boost Events
        if not before.premium_since and after.premium_since:
            embed = discord.Embed(title="New Server Boost", color=0xf472b6, timestamp=discord.utils.utcnow())
            embed.set_author(name=f"{after}", icon_url=after.display_avatar.url)
            embed.description = f"{after.mention} has boosted the server! ✨"
            await self._send_log(after.guild, 'boosts', embed)

        if before.nick != after.nick:
            embed = discord.Embed(title="Nickname Changed", color=discord.Color.blue(), timestamp=discord.utils.utcnow())
            embed.set_author(name=f"{after}", icon_url=after.display_avatar.url)
            embed.add_field(name="Before", value=before.nick or "None")
            embed.add_field(name="After", value=after.nick or "None")
            await self._send_log(after.guild, 'members', embed)
        
        if before.roles != after.roles:
            added = [r.mention for r in after.roles if r not in before.roles]
            removed = [r.mention for r in before.roles if r not in after.roles]
            if added or removed:
                embed = discord.Embed(title="Roles Updated", color=discord.Color.blue(), timestamp=discord.utils.utcnow())
                embed.set_author(name=f"{after}", icon_url=after.display_avatar.url)
                if added: embed.add_field(name="Added", value=" ".join(added))
                if removed: embed.add_field(name="Removed", value=" ".join(removed))
                await self._send_log(after.guild, 'members', embed)

    # --- Server Events ---
    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        embed = discord.Embed(title="Role Created", color=discord.Color.green(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Name", value=role.name)
        embed.add_field(name="ID", value=role.id)
        await self._send_log(role.guild, 'server', embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        embed = discord.Embed(title="Role Deleted", color=discord.Color.red(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Name", value=role.name)
        await self._send_log(role.guild, 'server', embed)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        embed = discord.Embed(title="Channel Created", color=discord.Color.green(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Name", value=channel.name)
        embed.add_field(name="Type", value=str(channel.type).replace('_', ' ').title())
        await self._send_log(channel.guild, 'server', embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        embed = discord.Embed(title="Channel Deleted", color=discord.Color.red(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Name", value=channel.name)
        await self._send_log(channel.guild, 'server', embed)

    @commands.Cog.listener()
    async def on_webhooks_update(self, channel):
        embed = discord.Embed(title="Webhooks Updated", color=discord.Color.blue(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Channel", value=channel.mention)
        await self._send_log(channel.guild, 'webhooks', embed)

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild, before, after):
        embed = discord.Embed(title="Emojis Updated", color=discord.Color.blue(), timestamp=discord.utils.utcnow())
        if len(after) > len(before):
            new = [e for e in after if e not in before][0]
            embed.description = f"Added emoji: {new} (`{new.name}`)"
        elif len(before) > len(after):
            old = [e for e in before if e not in after][0]
            embed.description = f"Removed emoji: `{old.name}`"
        await self._send_log(guild, 'emojis', embed)

    @commands.Cog.listener()
    async def on_thread_create(self, thread):
        embed = discord.Embed(title="Thread Created", color=discord.Color.green(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Name", value=thread.name)
        embed.add_field(name="Parent", value=thread.parent.mention if thread.parent else "None")
        await self._send_log(thread.guild, 'threads', embed)

    # --- Voice Events ---
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel == after.channel: return
        
        embed = discord.Embed(color=discord.Color.blue(), timestamp=discord.utils.utcnow())
        embed.set_author(name=f"{member}", icon_url=member.display_avatar.url)
        
        if not before.channel:
            embed.title = "Joined Voice Channel"
            embed.description = f"Joined **{after.channel.name}**"
        elif not after.channel:
            embed.title = "Left Voice Channel"
            embed.description = f"Left **{before.channel.name}**"
        else:
            embed.title = "Moved Voice Channel"
            embed.description = f"Moved from **{before.channel.name}** to **{after.channel.name}**"
            
        await self._send_log(member.guild, 'voice', embed)

    @commands.Cog.listener()
    async def on_verification_success(self, member):
        embed = discord.Embed(title="User Verified", color=discord.Color.green(), timestamp=discord.utils.utcnow())
        embed.set_author(name=f"{member}", icon_url=member.display_avatar.url)
        embed.description = f"{member.mention} has successfully completed verification."
        embed.set_footer(text=f"Member ID: {member.id}")
        await self._send_log(member.guild, 'verification', embed)

    # --- Commands ---
    @commands.group(name="logs", invoke_without_command=True, help='View and manage logging settings.')
    @commands.has_permissions(administrator=True)
    async def logs_group(self, ctx):
        config = await self.get_config(ctx.guild.id)
        if not config or not config.get("events"):
            return await ctx.info("No logging events are currently configured for this server.")
        description = "Current logging configuration:\n\n"
        for event, data in sorted(config["events"].items()):
            channel = ctx.guild.get_channel(data.get("channel_id"))
            status = "✅" if data.get("enabled", True) else "❌"
            description += f"{status} **{event.capitalize()}**: {channel.mention if channel else 'Deleted Channel'}\n"
        await ctx.embed(description, title="Logging Configuration")

    @logs_group.command(name="setup", help='Setup a logging event.')
    @commands.has_permissions(administrator=True)
    async def logs_setup(self, ctx, event_type: str, channel: discord.TextChannel):
        event_type = event_type.lower()
        valid = ['messages', 'members', 'server', 'voice', 'mod', 'invites', 'antinuke', 'automod']
        if event_type not in valid: return await ctx.error(f"Invalid type. Use: `{', '.join(valid)}`")
        
        webhook = await channel.create_webhook(name="Horizen Logs")
        config = await self.get_config(ctx.guild.id) or {"events": {}}
        config["events"][event_type] = {"channel_id": channel.id, "webhook_url": webhook.url, "enabled": True}
        
        await self.update_config(ctx.guild.id, config)
        await ctx.success(f"Logging for **{event_type}** set up in {channel.mention}.")

async def setup(bot):
    await bot.add_cog(Logging(bot))
