import discord
from discord.ext import commands
import aiohttp
import datetime
import collections
import time

class EventLogger(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager
        self.session = aiohttp.ClientSession()

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    async def send_webhook(self, guild_id, event_type, embed):
        config = await self.db.find_one('logging_config', {'_id': guild_id})
        if not config or 'events' not in config:
            return
        event_data = config['events'].get(event_type)
        if not event_data or not event_data.get('enabled') or (not event_data.get('webhook_url')):
            return
        webhook_url = event_data['webhook_url']
        webhook = discord.Webhook.from_url(webhook_url, session=self.session)
        try:
            await webhook.send(embed=embed, username='Horizen Logging', avatar_url=self.bot.user.display_avatar.url)
        except discord.NotFound:
            config['events'][event_type]['enabled'] = False
            await self.db.update_one('logging_config', {'_id': guild_id}, config)
        except Exception as e:
            print(f'Error sending logging webhook ({event_type}): {e}')

    async def _notify_antinuke(self, guild, user, action_type):
        antinuke = self.bot.get_cog('AntiNuke')
        if antinuke:
            await antinuke.check_nuke(guild, user, action_type)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot or not message.guild:
            return
        embed = discord.Embed(title='Message Deleted', description=f'**Author:** {message.author.mention} ({message.author.id})\n**Channel:** {message.channel.mention}', color=discord.Color.red(), timestamp=discord.utils.utcnow())
        if message.content:
            embed.add_field(name='Content', value=message.content[:1024], inline=False)
        await self.send_webhook(message.guild.id, 'messages', embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot or not before.guild or before.content == after.content:
            return
        embed = discord.Embed(title='Message Edited', description=f'**Author:** {before.author.mention} ({before.author.id})\n**Channel:** {before.channel.mention}\n[Jump to Message]({after.jump_url})', color=discord.Color.blue(), timestamp=discord.utils.utcnow())
        embed.add_field(name='Before', value=before.content[:1024] if before.content else 'None', inline=False)
        embed.add_field(name='After', value=after.content[:1024] if after.content else 'None', inline=False)
        await self.send_webhook(before.guild.id, 'messages', embed)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        embed = discord.Embed(title='Member Joined', description=f'{member.mention} ({member.id}) joined the server.', color=discord.Color.green(), timestamp=discord.utils.utcnow())
        embed.add_field(name='Account Created', value=f'<t:{int(member.created_at.timestamp())}:R>', inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        await self.send_webhook(member.guild.id, 'members', embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        moderator = None
        reason = None
        try:
            async for entry in member.guild.audit_logs(limit=5, action=discord.AuditLogAction.kick):
                if entry.target.id == member.id and (discord.utils.utcnow() - entry.created_at).total_seconds() < 10:
                    moderator = entry.user
                    reason = entry.reason
                    break
        except discord.Forbidden:
            pass
        if moderator:
            if moderator.id == self.bot.user.id:
                return
            await self._notify_antinuke(member.guild, moderator, "Mass Kick")
            embed = discord.Embed(title='Member Kicked', description=f"**User:** {member.mention} ({member.id})\n**Moderator:** {moderator.mention}\n**Reason:** {reason or 'No reason provided'}", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
            await self.send_webhook(member.guild.id, 'mod', embed)
        else:
            embed = discord.Embed(title='Member Left', description=f'{member.mention} ({member.id}) left the server.', color=discord.Color.red(), timestamp=discord.utils.utcnow())
            roles = [role.mention for role in member.roles if role.name != '@everyone']
            if roles:
                embed.add_field(name='Roles', value=' '.join(roles[:1024]), inline=False)
            await self.send_webhook(member.guild.id, 'members', embed)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        guild_id = before.guild.id
        if before.nick != after.nick:
            embed = discord.Embed(title='Nickname Changed', description=f'**Member:** {after.mention} ({after.id})', color=discord.Color.blue(), timestamp=discord.utils.utcnow())
            embed.add_field(name='Before', value=before.nick or 'None')
            embed.add_field(name='After', value=after.nick or 'None')
            await self.send_webhook(guild_id, 'members', embed)
        if before.roles != after.roles:
            added = [r.mention for r in after.roles if r not in before.roles]
            removed = [r.mention for r in before.roles if r not in after.roles]
            if added or removed:
                embed = discord.Embed(title='Roles Updated', description=f'**Member:** {after.mention} ({after.id})', color=discord.Color.blue(), timestamp=discord.utils.utcnow())
                if added:
                    embed.add_field(name='Added', value=' '.join(added))
                if removed:
                    embed.add_field(name='Removed', value=' '.join(removed))
                await self.send_webhook(guild_id, 'members', embed)
        if before.premium_since != after.premium_since:
            if after.premium_since:
                embed = discord.Embed(title='Server Boosted!', description=f'{after.mention} just boosted the server!', color=discord.Color.nitro_pink(), timestamp=discord.utils.utcnow())
                await self.send_webhook(guild_id, 'boosts', embed)
            else:
                embed = discord.Embed(title='Boost Removed', description=f'{after.mention} is no longer boosting the server.', color=discord.Color.red(), timestamp=discord.utils.utcnow())
                await self.send_webhook(guild_id, 'boosts', embed)

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        moderator = invite.inviter
        if not moderator:
            try:
                async for entry in invite.guild.audit_logs(limit=1, action=discord.AuditLogAction.invite_create):
                    if entry.target.code == invite.code:
                        moderator = entry.user
                        break
            except:
                pass
        embed = discord.Embed(title='Invite Created', description=f"**Code:** `{invite.code}`\n**Inviter:** {(moderator.mention if moderator else 'Unknown')}\n**Channel:** {invite.channel.mention}", color=discord.Color.green(), timestamp=discord.utils.utcnow())
        if invite.max_uses:
            embed.add_field(name='Max Uses', value=str(invite.max_uses))
        if invite.max_age:
            embed.add_field(name='Expires In', value=f'{invite.max_age}s')
        await self.send_webhook(invite.guild.id, 'invites', embed)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        moderator = None
        try:
            async for entry in invite.guild.audit_logs(limit=1, action=discord.AuditLogAction.invite_delete):
                if entry.target.code == invite.code:
                    moderator = entry.user
                    break
        except:
            pass
        embed = discord.Embed(title='Invite Deleted', description=f'**Code:** `{invite.code}`\n**Channel:** {invite.channel.mention}' + (f'\n**Deleted by:** {moderator.mention}' if moderator else ''), color=discord.Color.red(), timestamp=discord.utils.utcnow())
        await self.send_webhook(invite.guild.id, 'invites', embed)

    @commands.Cog.listener()
    async def on_webhooks_update(self, channel):
        moderator = None
        action_type = 'Updated'
        try:
            async for entry in channel.guild.audit_logs(limit=1):
                if entry.action in [discord.AuditLogAction.webhook_create, discord.AuditLogAction.webhook_update, discord.AuditLogAction.webhook_delete]:
                    if (discord.utils.utcnow() - entry.created_at).total_seconds() < 10:
                        moderator = entry.user
                        if entry.action == discord.AuditLogAction.webhook_create:
                            action_type = 'Created'
                        elif entry.action == discord.AuditLogAction.webhook_delete:
                            action_type = 'Deleted'
                        break
        except:
            pass
        if moderator: await self._notify_antinuke(channel.guild, moderator, "Mass Webhook Update")
        embed = discord.Embed(title=f'Webhooks {action_type}', description=f'Webhooks were {action_type.lower()} in channel {channel.mention}' + (f'\n**Action by:** {moderator.mention}' if moderator else ''), color=discord.Color.orange(), timestamp=discord.utils.utcnow())
        await self.send_webhook(channel.guild.id, 'webhooks', embed)

    @commands.Cog.listener()
    async def on_thread_create(self, thread):
        embed = discord.Embed(title='Thread Created', description=f"**Name:** {thread.name}\n**Parent Channel:** {thread.parent.mention}\n**Author:** {(thread.owner.mention if thread.owner else 'Unknown')}", color=discord.Color.green(), timestamp=discord.utils.utcnow())
        await self.send_webhook(thread.guild.id, 'threads', embed)

    @commands.Cog.listener()
    async def on_thread_delete(self, thread):
        moderator = None
        try:
            async for entry in thread.guild.audit_logs(limit=1, action=discord.AuditLogAction.thread_delete):
                if entry.target.id == thread.id:
                    moderator = entry.user
                    break
        except:
            pass
        embed = discord.Embed(title='Thread Deleted', description=f'**Name:** {thread.name}\n**Parent Channel:** {thread.parent.mention}' + (f'\n**Deleted by:** {moderator.mention}' if moderator else ''), color=discord.Color.red(), timestamp=discord.utils.utcnow())
        await self.send_webhook(thread.guild.id, 'threads', embed)

    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        moderator = None
        reason = None
        try:
            async for entry in after.audit_logs(limit=1, action=discord.AuditLogAction.guild_update):
                if (discord.utils.utcnow() - entry.created_at).total_seconds() < 10:
                    moderator = entry.user
                    reason = entry.reason
                    break
        except: pass
        if moderator:
            impact = []
            if before.name != after.name: impact.append(f"Name: {before.name} -> {after.name}")
            if before.vanity_url_code != after.vanity_url_code: impact.append(f"Vanity: {before.vanity_url_code} -> {after.vanity_url_code}")
            if impact:
                embed = discord.Embed(title="Server Updated", description=f"**Action by:** {moderator.mention}\n" + "\n".join(impact), color=discord.Color.orange(), timestamp=discord.utils.utcnow())
                await self.send_webhook(after.id, "antinuke", embed)
        if before.premium_tier != after.premium_tier:
            embed = discord.Embed(title='Server Boost Level Changed', description=f'Server level moved from **Level {before.premium_tier}** to **Level {after.premium_tier}**!', color=discord.Color.nitro_pink(), timestamp=discord.utils.utcnow())
            embed.add_field(name='Total Boosts', value=str(after.premium_subscription_count))
            await self.send_webhook(after.id, 'boosts', embed)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        moderator = None
        try:
            async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_create):
                if entry.target.id == role.id:
                    moderator = entry.user
                    break
        except: pass
        if moderator: await self._notify_antinuke(role.guild, moderator, "Mass Role Create")
        embed = discord.Embed(title='Role Created', description=f'Role: **{role.name}** ({role.id})', color=discord.Color.green(), timestamp=discord.utils.utcnow())
        await self.send_webhook(role.guild.id, 'server', embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        moderator = None
        try:
            async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
                if entry.target.id == role.id:
                    moderator = entry.user
                    break
        except: pass
        if moderator: await self._notify_antinuke(role.guild, moderator, "Mass Role Delete")
        embed = discord.Embed(title='Role Deleted', description=f'Role: **{role.name}** ({role.id})', color=discord.Color.red(), timestamp=discord.utils.utcnow())
        await self.send_webhook(role.guild.id, 'server', embed)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        moderator = None
        try:
            async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_create):
                if entry.target.id == channel.id:
                    moderator = entry.user
                    break
        except: pass
        if moderator: await self._notify_antinuke(channel.guild, moderator, "Mass Channel Create")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        moderator = None
        try:
            async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
                if entry.target.id == channel.id:
                    moderator = entry.user
                    break
        except: pass
        if moderator: await self._notify_antinuke(channel.guild, moderator, "Mass Channel Delete")
        embed = discord.Embed(title='Channel Deleted', description=f'Channel: **{channel.name}** ({channel.id})', color=discord.Color.red(), timestamp=discord.utils.utcnow())
        await self.send_webhook(channel.guild.id, 'server', embed)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel == after.channel:
            return
        embed = discord.Embed(title='Voice State Updated', description=f'**Member:** {member.mention} ({member.id})', color=discord.Color.gold(), timestamp=discord.utils.utcnow())
        if not before.channel:
            embed.description += f'\nJoined voice channel: **{after.channel.name}**'
        elif not after.channel:
            embed.description += f'\nLeft voice channel: **{before.channel.name}**'
        else:
            embed.description += f'\nMoved from **{before.channel.name}** to **{after.channel.name}**'
        await self.send_webhook(member.guild.id, 'voice', embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        moderator_name = 'Unknown'
        moderator_obj = None
        reason = 'No reason provided'
        try:
            async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.ban):
                if entry.target.id == user.id:
                    if entry.user.id == self.bot.user.id:
                        return
                    moderator_name = f'{entry.user} ({entry.user.id})'
                    moderator_obj = entry.user
                    reason = entry.reason or reason
                    break
        except discord.Forbidden:
            pass
        if moderator_obj: await self._notify_antinuke(guild, moderator_obj, "Mass Ban")
        embed = discord.Embed(title='Member Banned', description=f'**User:** {user.mention} ({user.id})\n**Moderator:** {moderator_name}\n**Reason:** {reason}', color=discord.Color.dark_red(), timestamp=discord.utils.utcnow())
        await self.send_webhook(guild.id, 'mod', embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        moderator_name = 'Unknown'
        reason = 'No reason provided'
        try:
            async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.unban):
                if entry.target.id == user.id:
                    if entry.user.id == self.bot.user.id:
                        return
                    moderator_name = f'{entry.user} ({entry.user.id})'
                    reason = entry.reason or reason
                    break
        except discord.Forbidden:
            pass
        embed = discord.Embed(title='Member Unbanned', description=f'**User:** {user.mention} ({user.id})\n**Moderator:** {moderator_name}\n**Reason:** {reason}', color=discord.Color.green(), timestamp=discord.utils.utcnow())
        await self.send_webhook(guild.id, 'mod', embed)

async def setup(bot):
    await bot.add_cog(EventLogger(bot))
