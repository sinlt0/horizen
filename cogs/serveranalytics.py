import discord
from discord.ext import commands, tasks
import datetime
import asyncio

class ServerAnalytics(commands.Cog):
    category = 'utility'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager
        self._msg_buffer = {}
        self._cmd_buffer = {}

    async def cog_load(self):
        self.flush_analytics.start()

    def cog_unload(self):
        self.flush_analytics.cancel()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        key = f'{message.guild.id}'
        today = datetime.datetime.utcnow().strftime('%Y-%m-%d')
        self._msg_buffer.setdefault(key, {}).setdefault(today, 0)
        self._msg_buffer[key][today] += 1

    @commands.Cog.listener()
    async def on_command(self, ctx):
        if not ctx.guild:
            return
        key = f'{ctx.guild.id}'
        today = datetime.datetime.utcnow().strftime('%Y-%m-%d')
        self._cmd_buffer.setdefault(key, {}).setdefault(today, 0)
        self._cmd_buffer[key][today] += 1

    @tasks.loop(minutes=5)
    async def flush_analytics(self):
        for guild_id_str, daily in self._msg_buffer.items():
            gid = int(guild_id_str)
            data = await self.db.find_one('server_analytics', {'_id': gid}) or {'_id': gid, 'messages': {}, 'commands': {}, 'joins': {}, 'leaves': {}}
            for date, count in daily.items():
                data['messages'][date] = data['messages'].get(date, 0) + count
            await self.db.update_one('server_analytics', {'_id': gid}, data, upsert=True)
        self._msg_buffer.clear()

        for guild_id_str, daily in self._cmd_buffer.items():
            gid = int(guild_id_str)
            data = await self.db.find_one('server_analytics', {'_id': gid}) or {'_id': gid, 'messages': {}, 'commands': {}, 'joins': {}, 'leaves': {}}
            for date, count in daily.items():
                data['commands'][date] = data['commands'].get(date, 0) + count
            await self.db.update_one('server_analytics', {'_id': gid}, data, upsert=True)
        self._cmd_buffer.clear()

    @flush_analytics.before_loop
    async def before_flush(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.bot:
            return
        today = datetime.datetime.utcnow().strftime('%Y-%m-%d')
        data = await self.db.find_one('server_analytics', {'_id': member.guild.id}) or {'_id': member.guild.id, 'messages': {}, 'commands': {}, 'joins': {}, 'leaves': {}}
        data.setdefault('joins', {})[today] = data.get('joins', {}).get(today, 0) + 1
        await self.db.update_one('server_analytics', {'_id': member.guild.id}, data, upsert=True)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if member.bot:
            return
        today = datetime.datetime.utcnow().strftime('%Y-%m-%d')
        data = await self.db.find_one('server_analytics', {'_id': member.guild.id}) or {'_id': member.guild.id, 'messages': {}, 'commands': {}, 'joins': {}, 'leaves': {}}
        data.setdefault('leaves', {})[today] = data.get('leaves', {}).get(today, 0) + 1
        await self.db.update_one('server_analytics', {'_id': member.guild.id}, data, upsert=True)

    def _last_n_days(self, data_dict, n=7):
        dates = sorted(data_dict.keys())[-n:]
        return [(d, data_dict.get(d, 0)) for d in dates]

    def _bar(self, value, max_val, width=15):
        if max_val == 0:
            return '░' * width
        filled = int((value / max_val) * width)
        return '█' * filled + '░' * (width - filled)

    @commands.group(name='analytics', aliases=['stats2', 'serverstats2'], invoke_without_command=True, help='Server analytics and activity tracking.')
    async def analytics_group(self, ctx):
        await ctx.invoke(self.analytics_overview)

    @analytics_group.command(name='overview', aliases=['summary'], help='Overview of server activity.')
    async def analytics_overview(self, ctx):
        data = await self.db.find_one('server_analytics', {'_id': ctx.guild.id})
        if not data:
            return await ctx.info('No analytics data yet. Data is collected automatically.')

        guild = ctx.guild
        total_msgs = sum(data.get('messages', {}).values())
        total_cmds = sum(data.get('commands', {}).values())
        total_joins = sum(data.get('joins', {}).values())
        total_leaves = sum(data.get('leaves', {}).values())

        today = datetime.datetime.utcnow().strftime('%Y-%m-%d')
        msgs_today = data.get('messages', {}).get(today, 0)
        joins_today = data.get('joins', {}).get(today, 0)

        bots = sum(1 for m in guild.members if m.bot)
        humans = guild.member_count - bots
        online = sum(1 for m in guild.members if m.status != discord.Status.offline and not m.bot)

        embed = self.bot.embed_manager.generic(
            description=(
                f'**Members:** `{humans}` humans · `{bots}` bots · `{online}` online\n'
                f'**Text Channels:** `{len(guild.text_channels)}` · **Voice:** `{len(guild.voice_channels)}`\n'
                f'**Roles:** `{len(guild.roles)}` · **Emojis:** `{len(guild.emojis)}`\n\n'
                f'**Messages Today:** `{msgs_today}`\n'
                f'**Total Messages:** `{total_msgs:,}`\n'
                f'**Total Commands:** `{total_cmds:,}`\n'
                f'**Total Joins:** `{total_joins:,}`\n'
                f'**Net Growth:** `{total_joins - total_leaves:+,}`\n'
                f'**Joins Today:** `{joins_today}`'
            ),
            title=f'📊 {guild.name} — Analytics Overview'
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        await ctx.send(embed=embed)

    @analytics_group.command(name='messages', aliases=['msgstats'], help='Message activity for the last 7 days.')
    async def analytics_messages(self, ctx, days: int = 7):
        days = max(1, min(30, days))
        data = await self.db.find_one('server_analytics', {'_id': ctx.guild.id})
        if not data or not data.get('messages'):
            return await ctx.info('No message data yet.')
        daily = self._last_n_days(data['messages'], days)
        max_val = max(v for _, v in daily) if daily else 1
        lines = [f'`{d}` {self._bar(v, max_val)} `{v}`' for d, v in daily]
        embed = self.bot.embed_manager.generic(
            description='\n'.join(lines) or 'No data.',
            title=f'💬 Message Activity — Last {days} Days'
        )
        await ctx.send(embed=embed)

    @analytics_group.command(name='growth', help='Member join/leave activity for the last 7 days.')
    async def analytics_growth(self, ctx, days: int = 7):
        days = max(1, min(30, days))
        data = await self.db.find_one('server_analytics', {'_id': ctx.guild.id})
        if not data:
            return await ctx.info('No growth data yet.')
        joins = self._last_n_days(data.get('joins', {}), days)
        leaves = self._last_n_days(data.get('leaves', {}), days)
        join_map = dict(joins)
        leave_map = dict(leaves)
        all_dates = sorted(set(list(join_map.keys()) + list(leave_map.keys())))[-days:]
        lines = []
        for d in all_dates:
            j = join_map.get(d, 0)
            l = leave_map.get(d, 0)
            net = j - l
            sign = '+' if net >= 0 else ''
            lines.append(f'`{d}` +`{j}` joins / -`{l}` leaves / **{sign}{net} net**')
        embed = self.bot.embed_manager.generic(
            description='\n'.join(lines) or 'No data.',
            title=f'📈 Member Growth — Last {days} Days'
        )
        await ctx.send(embed=embed)

    @analytics_group.command(name='commands', aliases=['cmdstats'], help='Command usage stats for the last 7 days.')
    async def analytics_commands(self, ctx, days: int = 7):
        days = max(1, min(30, days))
        data = await self.db.find_one('server_analytics', {'_id': ctx.guild.id})
        if not data or not data.get('commands'):
            return await ctx.info('No command data yet.')
        daily = self._last_n_days(data['commands'], days)
        max_val = max(v for _, v in daily) if daily else 1
        lines = [f'`{d}` {self._bar(v, max_val)} `{v}`' for d, v in daily]
        embed = self.bot.embed_manager.generic(
            description='\n'.join(lines) or 'No data.',
            title=f'⚡ Command Usage — Last {days} Days'
        )
        await ctx.send(embed=embed)

    @analytics_group.command(name='channels', help='Show most active channels by message count.')
    @commands.has_permissions(manage_guild=True)
    async def analytics_channels(self, ctx):
        data = await self.db.find_one('server_analytics', {'_id': ctx.guild.id}) or {}
        channel_msgs = data.get('channel_messages', {})
        if not channel_msgs:
            return await ctx.info('No per-channel data yet.')
        sorted_ch = sorted(channel_msgs.items(), key=lambda x: x[1], reverse=True)[:10]
        max_val = sorted_ch[0][1] if sorted_ch else 1
        lines = [f'<#{ch_id}> {self._bar(count, max_val)} `{count}`' for ch_id, count in sorted_ch]
        embed = self.bot.embed_manager.generic(
            description='\n'.join(lines),
            title='📡 Most Active Channels'
        )
        await ctx.send(embed=embed)

    @analytics_group.command(name='members', aliases=['memberbreakdown'], help='Breakdown of server members.')
    async def analytics_members(self, ctx):
        guild = ctx.guild
        bots = [m for m in guild.members if m.bot]
        humans = [m for m in guild.members if not m.bot]
        online = [m for m in humans if m.status == discord.Status.online]
        idle = [m for m in humans if m.status == discord.Status.idle]
        dnd = [m for m in humans if m.status == discord.Status.dnd]
        offline = [m for m in humans if m.status == discord.Status.offline]
        boosters = guild.premium_subscribers

        embed = self.bot.embed_manager.generic(
            description=(
                f'**Total:** `{guild.member_count}`\n'
                f'**Humans:** `{len(humans)}`\n'
                f'**Bots:** `{len(bots)}`\n\n'
                f'🟢 Online: `{len(online)}`\n'
                f'🟡 Idle: `{len(idle)}`\n'
                f'🔴 Do Not Disturb: `{len(dnd)}`\n'
                f'⚫ Offline: `{len(offline)}`\n\n'
                f'💎 Boosters: `{len(boosters)}`\n'
                f'📅 Created: <t:{int(guild.created_at.timestamp())}:R>'
            ),
            title=f'👥 Member Breakdown — {guild.name}'
        )
        await ctx.send(embed=embed)

    @analytics_group.command(name='roles', help='Show role distribution across server members.')
    async def analytics_roles(self, ctx):
        guild = ctx.guild
        role_counts = []
        for role in reversed(guild.roles):
            if role.name == '@everyone':
                continue
            count = len(role.members)
            if count > 0:
                role_counts.append((role, count))
        role_counts.sort(key=lambda x: x[1], reverse=True)
        top = role_counts[:15]
        max_val = top[0][1] if top else 1
        lines = [f'{r.mention} {self._bar(c, max_val)} `{c}`' for r, c in top]
        embed = self.bot.embed_manager.generic(
            description='\n'.join(lines) or 'No roles.',
            title='🎭 Role Distribution'
        )
        await ctx.send(embed=embed)

    @analytics_group.command(name='joinedrank', aliases=['jrank'], help='Show what position a member joined at.')
    async def analytics_joinedrank(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        members_by_join = sorted([m for m in ctx.guild.members if m.joined_at], key=lambda m: m.joined_at)
        rank = next((i + 1 for i, m in enumerate(members_by_join) if m.id == member.id), None)
        if not rank:
            return await ctx.error('Could not determine join rank.')
        await ctx.success(
            f'{member.mention} was the **#{rank}** member to join **{ctx.guild.name}**.\n'
            f'Joined: <t:{int(member.joined_at.timestamp())}:R>'
        )

    @analytics_group.command(name='oldest', help='Show the oldest members of this server.')
    async def analytics_oldest(self, ctx, count: int = 5):
        count = max(1, min(15, count))
        members = sorted([m for m in ctx.guild.members if m.joined_at and not m.bot], key=lambda m: m.joined_at)[:count]
        desc = '\n'.join([
            f'`{i+1}.` {m.mention} — joined <t:{int(m.joined_at.timestamp())}:R>'
            for i, m in enumerate(members)
        ])
        embed = self.bot.embed_manager.generic(description=desc, title=f'🏛️ Oldest Members (Top {count})')
        await ctx.send(embed=embed)

    @analytics_group.command(name='newest', help='Show the newest members of this server.')
    async def analytics_newest(self, ctx, count: int = 5):
        count = max(1, min(15, count))
        members = sorted([m for m in ctx.guild.members if m.joined_at and not m.bot], key=lambda m: m.joined_at, reverse=True)[:count]
        desc = '\n'.join([
            f'`{i+1}.` {m.mention} — joined <t:{int(m.joined_at.timestamp())}:R>'
            for i, m in enumerate(members)
        ])
        embed = self.bot.embed_manager.generic(description=desc, title=f'🆕 Newest Members (Top {count})')
        await ctx.send(embed=embed)

    @analytics_group.command(name='reset', help='Reset all analytics data for this server.')
    @commands.has_permissions(administrator=True)
    async def analytics_reset(self, ctx):
        await self.db.delete_one('server_analytics', {'_id': ctx.guild.id})
        await ctx.success(f'{self.bot.e.success} All analytics data reset.')

async def setup(bot):
    await bot.add_cog(ServerAnalytics(bot))
