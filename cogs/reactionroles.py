import discord
from discord.ext import commands

class ReactionRoles(commands.Cog):
    category = 'config'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager
        self._cache = {}

    async def cog_load(self):
        await self._load_cache()

    async def _load_cache(self):
        configs = await self.db.find('reaction_roles', {})
        for c in configs:
            self._cache[c['_id']] = c.get('panels', {})

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.member and payload.member.bot:
            return
        panels = self._cache.get(payload.guild_id, {})
        key = f'{payload.channel_id}:{payload.message_id}'
        panel = panels.get(key)
        if not panel:
            return
        emoji_str = str(payload.emoji)
        role_id = panel.get(emoji_str)
        if not role_id:
            return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        role = guild.get_role(role_id)
        if role and payload.member:
            try:
                await payload.member.add_roles(role, reason='Reaction Role')
            except Exception:
                pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        panels = self._cache.get(payload.guild_id, {})
        key = f'{payload.channel_id}:{payload.message_id}'
        panel = panels.get(key)
        if not panel:
            return
        emoji_str = str(payload.emoji)
        role_id = panel.get(emoji_str)
        if not role_id:
            return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        member = guild.get_member(payload.user_id)
        role = guild.get_role(role_id)
        if role and member:
            try:
                await member.remove_roles(role, reason='Reaction Role Removed')
            except Exception:
                pass

    @commands.group(name='reactionrole', aliases=['rr', 'rrole'], invoke_without_command=True, help='Reaction role management commands.')
    @commands.has_permissions(manage_roles=True)
    async def rr_group(self, ctx):
        await ctx.send_help(ctx.command)

    @rr_group.command(name='create', help='Create a reaction role panel. Usage: rr create #channel Title | Description')
    @commands.has_permissions(manage_roles=True)
    async def rr_create(self, ctx, channel: discord.TextChannel, *, content: str):
        parts = content.split('|', 1)
        title = parts[0].strip()
        desc = parts[1].strip() if len(parts) > 1 else 'React to get a role!'
        embed = discord.Embed(title=title, description=desc, color=self.bot.embed_manager.color)
        embed.set_footer(text='React below to get your roles')
        msg = await channel.send(embed=embed)
        config = await self.db.find_one('reaction_roles', {'_id': ctx.guild.id}) or {'_id': ctx.guild.id, 'panels': {}}
        key = f'{channel.id}:{msg.id}'
        config['panels'][key] = {}
        await self.db.update_one('reaction_roles', {'_id': ctx.guild.id}, config, upsert=True)
        self._cache.setdefault(ctx.guild.id, {})[key] = {}
        await ctx.success(f'{self.bot.e.success} Panel created in {channel.mention}. ID: `{msg.id}`')

    @rr_group.command(name='add', help='Add an emoji-role pair to a panel. Usage: rr add <message_id> <emoji> <@role>')
    @commands.has_permissions(manage_roles=True)
    async def rr_add(self, ctx, message_id: int, emoji: str, role: discord.Role):
        config = await self.db.find_one('reaction_roles', {'_id': ctx.guild.id})
        if not config:
            return await ctx.error('No panels configured. Use `rr create` first.')
        panel_key = next((k for k in config.get('panels', {}) if k.endswith(f':{message_id}')), None)
        if not panel_key:
            return await ctx.error('Panel not found. Check the message ID.')
        channel_id = int(panel_key.split(':')[0])
        channel = ctx.guild.get_channel(channel_id)
        try:
            msg = await channel.fetch_message(message_id)
            await msg.add_reaction(emoji)
        except Exception:
            return await ctx.error('Could not add reaction. Check the emoji.')
        config['panels'][panel_key][emoji] = role.id
        await self.db.update_one('reaction_roles', {'_id': ctx.guild.id}, config, upsert=True)
        self._cache.setdefault(ctx.guild.id, {}).setdefault(panel_key, {})[emoji] = role.id
        await ctx.success(f'{self.bot.e.success} Added {emoji} → {role.mention}.')

    @rr_group.command(name='remove', help='Remove an emoji from a reaction role panel.')
    @commands.has_permissions(manage_roles=True)
    async def rr_remove(self, ctx, message_id: int, emoji: str):
        config = await self.db.find_one('reaction_roles', {'_id': ctx.guild.id})
        if not config:
            return await ctx.error('No panels configured.')
        panel_key = next((k for k in config.get('panels', {}) if k.endswith(f':{message_id}')), None)
        if not panel_key:
            return await ctx.error('Panel not found.')
        if emoji not in config['panels'].get(panel_key, {}):
            return await ctx.error('Emoji not found in that panel.')
        del config['panels'][panel_key][emoji]
        await self.db.update_one('reaction_roles', {'_id': ctx.guild.id}, config, upsert=True)
        if ctx.guild.id in self._cache and panel_key in self._cache[ctx.guild.id]:
            self._cache[ctx.guild.id][panel_key].pop(emoji, None)
        await ctx.success(f'{self.bot.e.success} Removed {emoji} from panel.')

    @rr_group.command(name='delete', help='Delete an entire reaction role panel.')
    @commands.has_permissions(manage_roles=True)
    async def rr_delete(self, ctx, message_id: int):
        config = await self.db.find_one('reaction_roles', {'_id': ctx.guild.id})
        if not config:
            return await ctx.error('No panels configured.')
        panel_key = next((k for k in config.get('panels', {}) if k.endswith(f':{message_id}')), None)
        if not panel_key:
            return await ctx.error('Panel not found.')
        del config['panels'][panel_key]
        await self.db.update_one('reaction_roles', {'_id': ctx.guild.id}, config, upsert=True)
        if ctx.guild.id in self._cache:
            self._cache[ctx.guild.id].pop(panel_key, None)
        await ctx.success(f'{self.bot.e.success} Panel deleted.')

    @rr_group.command(name='list', help='List all reaction role panels in this server.')
    @commands.has_permissions(manage_roles=True)
    async def rr_list(self, ctx):
        config = await self.db.find_one('reaction_roles', {'_id': ctx.guild.id})
        panels = config.get('panels', {}) if config else {}
        if not panels:
            return await ctx.info('No reaction role panels configured.')
        desc = ''
        for key, mappings in panels.items():
            ch_id, msg_id = key.split(':')
            desc += f'**Message `{msg_id}`** in <#{ch_id}>\n'
            for emoji, role_id in mappings.items():
                desc += f'  {emoji} → <@&{role_id}>\n'
        embed = self.bot.embed_manager.generic(description=desc, title='Reaction Role Panels')
        await ctx.send(embed=embed)

    @rr_group.command(name='sync', help='Reload the reaction role cache from the database.')
    @commands.has_permissions(manage_roles=True)
    async def rr_sync(self, ctx):
        await self._load_cache()
        await ctx.success(f'{self.bot.e.success} Reaction role cache resynced.')

async def setup(bot):
    await bot.add_cog(ReactionRoles(bot))
