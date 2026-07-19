import discord
from discord.ext import commands
import json
import io
import datetime

class ServerData(commands.Cog):
    category = 'utility'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager

    @commands.command(name='exportroles', help='Export all server roles as a JSON file.')
    @commands.has_permissions(manage_roles=True)
    async def exportroles(self, ctx):
        roles_data = []
        for role in ctx.guild.roles:
            if role.name == '@everyone':
                continue
            roles_data.append({
                'name': role.name,
                'color': str(role.color),
                'hoist': role.hoist,
                'mentionable': role.mentionable,
                'permissions': role.permissions.value,
                'position': role.position,
            })
        buf = io.BytesIO(json.dumps(roles_data, indent=2).encode())
        buf.seek(0)
        await ctx.send(f'{self.bot.e.success} Exported `{len(roles_data)}` roles.', file=discord.File(buf, filename='roles_export.json'))

    @commands.command(name='exportchannels', help='Export server channel structure as a JSON file.')
    @commands.has_permissions(manage_channels=True)
    async def exportchannels(self, ctx):
        channels_data = []
        for ch in ctx.guild.channels:
            channels_data.append({
                'name': ch.name,
                'type': str(ch.type),
                'category': ch.category.name if ch.category else None,
                'position': ch.position,
            })
        buf = io.BytesIO(json.dumps(channels_data, indent=2).encode())
        buf.seek(0)
        await ctx.send(f'{self.bot.e.success} Exported `{len(channels_data)}` channels.', file=discord.File(buf, filename='channels_export.json'))

    @commands.command(name='exportmembers', help='Export a list of server members as a JSON file.')
    @commands.has_permissions(administrator=True)
    async def exportmembers(self, ctx):
        members_data = []
        for m in ctx.guild.members:
            members_data.append({
                'id': m.id,
                'name': str(m),
                'display_name': m.display_name,
                'bot': m.bot,
                'joined_at': m.joined_at.isoformat() if m.joined_at else None,
                'roles': [r.name for r in m.roles if r.name != '@everyone'],
            })
        buf = io.BytesIO(json.dumps(members_data, indent=2).encode())
        buf.seek(0)
        await ctx.send(f'{self.bot.e.success} Exported `{len(members_data)}` members.', file=discord.File(buf, filename='members_export.json'))

    @commands.command(name='exportbans', help='Export the server ban list as a JSON file.')
    @commands.has_permissions(ban_members=True)
    async def exportbans(self, ctx):
        bans = [entry async for entry in ctx.guild.bans(limit=1000)]
        bans_data = [{'user_id': b.user.id, 'user': str(b.user), 'reason': b.reason} for b in bans]
        if not bans_data:
            return await ctx.info('No bans to export.')
        buf = io.BytesIO(json.dumps(bans_data, indent=2).encode())
        buf.seek(0)
        await ctx.send(f'{self.bot.e.success} Exported `{len(bans_data)}` bans.', file=discord.File(buf, filename='bans_export.json'))

    @commands.command(name='exportemojis', help='Export a list of server emojis as a JSON file.')
    async def exportemojis(self, ctx):
        emojis_data = [{'name': e.name, 'id': e.id, 'animated': e.animated, 'url': str(e.url)} for e in ctx.guild.emojis]
        if not emojis_data:
            return await ctx.info('This server has no custom emojis.')
        buf = io.BytesIO(json.dumps(emojis_data, indent=2).encode())
        buf.seek(0)
        await ctx.send(f'{self.bot.e.success} Exported `{len(emojis_data)}` emojis.', file=discord.File(buf, filename='emojis_export.json'))

    @commands.command(name='serversnapshot', help='Take a full JSON snapshot of the server structure.')
    @commands.has_permissions(administrator=True)
    async def serversnapshot(self, ctx):
        guild = ctx.guild
        snapshot = {
            'name': guild.name,
            'id': guild.id,
            'member_count': guild.member_count,
            'created_at': guild.created_at.isoformat(),
            'snapshot_taken': datetime.datetime.utcnow().isoformat(),
            'roles': [{'name': r.name, 'color': str(r.color), 'position': r.position} for r in guild.roles if r.name != '@everyone'],
            'channels': [{'name': c.name, 'type': str(c.type), 'category': c.category.name if c.category else None} for c in guild.channels],
            'boost_tier': guild.premium_tier,
            'boost_count': guild.premium_subscription_count,
            'verification_level': str(guild.verification_level),
        }
        buf = io.BytesIO(json.dumps(snapshot, indent=2).encode())
        buf.seek(0)
        await ctx.send(f'{self.bot.e.success} Server snapshot created.', file=discord.File(buf, filename=f'{guild.name}_snapshot.json'))

    @commands.command(name='importroles', help='Import roles from a previously exported JSON file (attach it).')
    @commands.has_permissions(administrator=True)
    async def importroles(self, ctx):
        if not ctx.message.attachments:
            return await ctx.error('Attach a JSON file exported with `exportroles`.')
        attachment = ctx.message.attachments[0]
        if not attachment.filename.endswith('.json'):
            return await ctx.error('File must be a `.json` file.')
        import aiohttp
        async with aiohttp.ClientSession() as s:
            async with s.get(attachment.url) as r:
                raw = await r.text()
        try:
            roles_data = json.loads(raw)
        except json.JSONDecodeError:
            return await ctx.error('Invalid JSON file.')

        created = 0
        for role_info in roles_data:
            existing = discord.utils.get(ctx.guild.roles, name=role_info['name'])
            if existing:
                continue
            try:
                color_str = role_info.get('color', '#000000').lstrip('#')
                color = discord.Color(int(color_str, 16)) if color_str != '000000' else discord.Color.default()
                await ctx.guild.create_role(
                    name=role_info['name'],
                    color=color,
                    hoist=role_info.get('hoist', False),
                    mentionable=role_info.get('mentionable', False),
                    reason=f'Imported by {ctx.author}'
                )
                created += 1
            except Exception:
                continue
        await ctx.success(f'{self.bot.e.success} Imported `{created}` new roles.')

    @commands.command(name='backupserver', aliases=['createbackup'], help='Create a full server configuration backup.')
    @commands.has_permissions(administrator=True)
    async def backupserver(self, ctx):
        guild = ctx.guild
        backup_id = f'{guild.id}_{int(datetime.datetime.utcnow().timestamp())}'
        backup_data = {
            'guild_id': guild.id,
            'guild_name': guild.name,
            'created_at': datetime.datetime.utcnow().isoformat(),
            'created_by': ctx.author.id,
            'roles': [
                {'name': r.name, 'color': str(r.color), 'permissions': r.permissions.value, 'hoist': r.hoist, 'position': r.position}
                for r in guild.roles if r.name != '@everyone'
            ],
            'channels': [
                {'name': c.name, 'type': str(c.type), 'category': c.category.name if c.category else None, 'position': c.position}
                for c in guild.channels
            ],
        }
        await self.db.update_one('server_backups', {'_id': backup_id}, backup_data, upsert=True)
        await ctx.success(f'{self.bot.e.success} Backup created. ID: `{backup_id}`\nUse `listbackups` to view all backups.')

    @commands.command(name='listbackups', help='List all saved server backups.')
    @commands.has_permissions(administrator=True)
    async def listbackups(self, ctx):
        backups = await self.db.find('server_backups', {'guild_id': ctx.guild.id})
        if not backups:
            return await ctx.info('No backups found. Use `backupserver` to create one.')
        lines = [f'`{b["_id"]}` — <t:{int(datetime.datetime.fromisoformat(b["created_at"]).timestamp())}:R>' for b in backups[:10]]
        embed = self.bot.embed_manager.generic(description='\n'.join(lines), title=f'💾 Server Backups ({len(backups)})')
        await ctx.send(embed=embed)

    @commands.command(name='deletebackup', help='Delete a server backup by its ID.')
    @commands.has_permissions(administrator=True)
    async def deletebackup(self, ctx, backup_id: str):
        backup = await self.db.find_one('server_backups', {'_id': backup_id})
        if not backup or backup.get('guild_id') != ctx.guild.id:
            return await ctx.error('Backup not found.')
        await self.db.delete_one('server_backups', {'_id': backup_id})
        await ctx.success(f'{self.bot.e.success} Backup `{backup_id}` deleted.')

    @commands.command(name='comparebackup', help='Compare current server state to a saved backup.')
    @commands.has_permissions(administrator=True)
    async def comparebackup(self, ctx, backup_id: str):
        backup = await self.db.find_one('server_backups', {'_id': backup_id})
        if not backup or backup.get('guild_id') != ctx.guild.id:
            return await ctx.error('Backup not found.')

        old_roles = {r['name'] for r in backup.get('roles', [])}
        current_roles = {r.name for r in ctx.guild.roles if r.name != '@everyone'}
        added_roles = current_roles - old_roles
        removed_roles = old_roles - current_roles

        old_channels = {c['name'] for c in backup.get('channels', [])}
        current_channels = {c.name for c in ctx.guild.channels}
        added_channels = current_channels - old_channels
        removed_channels = old_channels - current_channels

        desc = (
            f'**Roles Added:** {", ".join(added_roles) or "None"}\n'
            f'**Roles Removed:** {", ".join(removed_roles) or "None"}\n\n'
            f'**Channels Added:** {", ".join(added_channels) or "None"}\n'
            f'**Channels Removed:** {", ".join(removed_channels) or "None"}'
        )
        embed = self.bot.embed_manager.generic(description=desc, title=f'📊 Backup Comparison — `{backup_id}`')
        await ctx.send(embed=embed)

    @commands.command(name='serverconfig', aliases=['exportconfig'], help='Export all bot configuration for this server as JSON.')
    @commands.has_permissions(administrator=True)
    async def serverconfig(self, ctx):
        collections = [
            'automod_config', 'mod_config', 'logging_config', 'leveling_config',
            'autorole_config', 'ticket_config', 'antinuke_config', 'reputation_config',
        ]
        combined = {}
        for col in collections:
            doc = await self.db.find_one(col, {'_id': ctx.guild.id})
            if doc:
                combined[col] = doc
        if not combined:
            return await ctx.info('No configuration data found for this server.')
        buf = io.BytesIO(json.dumps(combined, indent=2, default=str).encode())
        buf.seek(0)
        await ctx.send(f'{self.bot.e.success} Exported configuration for `{len(combined)}` systems.', file=discord.File(buf, filename='bot_config_export.json'))

async def setup(bot):
    await bot.add_cog(ServerData(bot))
