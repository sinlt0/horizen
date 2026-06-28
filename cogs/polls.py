import discord
from discord.ext import commands, tasks
import datetime
import asyncio

class PollView(discord.ui.View):
    def __init__(self, bot, poll_id, options):
        super().__init__(timeout=None)
        self.bot = bot
        self.poll_id = poll_id
        for i, opt in enumerate(options[:5]):
            btn = discord.ui.Button(
                label=opt[:80],
                style=discord.ButtonStyle.primary,
                custom_id=f'poll:{poll_id}:{i}'
            )
            btn.callback = self._make_callback(i, opt)
            self.add_item(btn)

    def _make_callback(self, index, label):
        async def callback(interaction: discord.Interaction):
            data = await self.bot.db_manager.find_one('polls', {'_id': self.poll_id})
            if not data or not data.get('active'):
                return await interaction.response.send_message('This poll has ended.', ephemeral=True)
            votes = data.get('votes', {})
            uid = str(interaction.user.id)
            if uid in votes:
                if votes[uid] == index:
                    return await interaction.response.send_message('You already voted for this option.', ephemeral=True)
                old = votes[uid]
                data['options'][old]['count'] = max(0, data['options'][old].get('count', 1) - 1)
            votes[uid] = index
            data['votes'] = votes
            data['options'][index]['count'] = data['options'][index].get('count', 0) + 1
            await self.bot.db_manager.update_one('polls', {'_id': self.poll_id}, data, upsert=True)
            total = sum(o.get('count', 0) for o in data['options'])
            desc = f"**{data['question']}**\n\n"
            for o in data['options']:
                pct = int((o.get('count', 0) / max(total, 1)) * 100)
                bar = '█' * (pct // 10) + '░' * (10 - pct // 10)
                desc += f'**{o["label"]}**\n{bar} `{pct}%` ({o.get("count", 0)} votes)\n\n'
            embed = interaction.message.embeds[0]
            embed.description = desc
            await interaction.response.edit_message(embed=embed)
        return callback


class Polls(commands.Cog):
    category = 'utility'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager

    async def cog_load(self):
        polls = await self.db.find('polls', {'active': True})
        for poll in polls:
            view = PollView(self.bot, poll['_id'], [o['label'] for o in poll.get('options', [])])
            self.bot.add_view(view)
        self.poll_end_loop.start()

    def cog_unload(self):
        self.poll_end_loop.cancel()

    @tasks.loop(seconds=30)
    async def poll_end_loop(self):
        now = int(datetime.datetime.utcnow().timestamp())
        polls = await self.db.find('polls', {'active': True})
        for poll in polls:
            if poll.get('end_at') and now >= poll['end_at']:
                await self._end_poll(poll)

    @poll_end_loop.before_loop
    async def before_poll_end(self):
        await self.bot.wait_until_ready()

    async def _end_poll(self, poll_data):
        guild = self.bot.get_guild(poll_data.get('guild_id'))
        if not guild:
            return
        channel = guild.get_channel(poll_data.get('channel_id'))
        if not channel:
            return
        try:
            msg = await channel.fetch_message(poll_data['_id'])
        except Exception:
            await self.db.update_one('polls', {'_id': poll_data['_id']}, {'active': False}, upsert=True)
            return
        options = poll_data.get('options', [])
        winner = max(options, key=lambda o: o.get('count', 0)) if options else None
        total = sum(o.get('count', 0) for o in options)
        desc = f"**{poll_data['question']}** *(Ended)*\n\n"
        for o in options:
            pct = int((o.get('count', 0) / max(total, 1)) * 100)
            bar = '█' * (pct // 10) + '░' * (10 - pct // 10)
            mark = ' 🏆' if winner and o['label'] == winner['label'] else ''
            desc += f'**{o["label"]}**{mark}\n{bar} `{pct}%` ({o.get("count", 0)} votes)\n\n'
        embed = discord.Embed(title='📊 Poll Ended', description=desc, color=discord.Color.red(), timestamp=discord.utils.utcnow())
        await msg.edit(embed=embed, view=None)
        if winner:
            await channel.send(f'🏆 Poll ended! Winner: **{winner["label"]}** with `{winner.get("count", 0)}` votes.')
        await self.db.update_one('polls', {'_id': poll_data['_id']}, {'active': False}, upsert=True)

    @commands.group(name='poll2', aliases=['advpoll', 'pollcreate'], invoke_without_command=True, help='Advanced interactive poll system.')
    @commands.has_permissions(manage_messages=True)
    async def poll_group(self, ctx):
        await ctx.send_help(ctx.command)

    @poll_group.command(name='create', help='Create a button poll. Usage: poll2 create "Question" "Option1" "Option2" [duration]')
    @commands.has_permissions(manage_messages=True)
    async def poll_create(self, ctx, question: str, *args):
        import re as _re
        options = [a for a in args if not _re.match(r'^\d+[mhd]$', a)]
        duration_arg = next((a for a in args if _re.match(r'^\d+[mhd]$', a)), None)
        if len(options) < 2:
            return await ctx.error('Provide at least 2 options.')
        if len(options) > 5:
            return await ctx.error('Maximum 5 options.')
        end_at = None
        if duration_arg:
            amount, unit = int(duration_arg[:-1]), duration_arg[-1]
            seconds = amount * {'m': 60, 'h': 3600, 'd': 86400}[unit]
            end_at = int(datetime.datetime.utcnow().timestamp()) + seconds
        poll_options = [{'label': o, 'count': 0} for o in options]
        desc = f'**{question}**\n\n'
        for o in poll_options:
            desc += f'**{o["label"]}**\n{"░" * 10} `0%` (0 votes)\n\n'
        if end_at:
            desc += f'\n⏰ Ends <t:{end_at}:R>'
        embed = discord.Embed(title='📊 Poll', description=desc, color=discord.Color.blurple(), timestamp=discord.utils.utcnow())
        embed.set_footer(text=f'Started by {ctx.author}')
        view = PollView(self.bot, 0, options)
        msg = await ctx.send(embed=embed, view=view)
        view.poll_id = msg.id
        for item in view.children:
            item.custom_id = f'poll:{msg.id}:{item.custom_id.split(":")[-1]}'
        poll_data = {
            '_id': msg.id, 'guild_id': ctx.guild.id, 'channel_id': ctx.channel.id,
            'question': question, 'options': poll_options, 'votes': {}, 'active': True,
            'end_at': end_at, 'author_id': ctx.author.id
        }
        await self.db.update_one('polls', {'_id': msg.id}, poll_data, upsert=True)
        await msg.edit(view=PollView(self.bot, msg.id, options))

    @poll_group.command(name='end', help='End a poll early by message ID.')
    @commands.has_permissions(manage_messages=True)
    async def poll_end(self, ctx, message_id: int):
        data = await self.db.find_one('polls', {'_id': message_id})
        if not data or not data.get('active'):
            return await ctx.error('Poll not found or already ended.')
        await self._end_poll(data)
        await ctx.success(f'{self.bot.e.success} Poll ended.')

    @poll_group.command(name='results', help='View current results of an active poll.')
    async def poll_results(self, ctx, message_id: int):
        data = await self.db.find_one('polls', {'_id': message_id})
        if not data:
            return await ctx.error('Poll not found.')
        options = data.get('options', [])
        total = sum(o.get('count', 0) for o in options)
        desc = f"**{data['question']}**\n\n"
        for o in options:
            pct = int((o.get('count', 0) / max(total, 1)) * 100)
            desc += f'**{o["label"]}** — `{o.get("count", 0)}` votes (`{pct}%`)\n'
        desc += f'\n**Total votes:** `{total}`'
        embed = self.bot.embed_manager.generic(description=desc, title='📊 Poll Results')
        await ctx.send(embed=embed)

    @poll_group.command(name='list', help='List all active polls in this server.')
    async def poll_list(self, ctx):
        polls = await self.db.find('polls', {'guild_id': ctx.guild.id, 'active': True})
        if not polls:
            return await ctx.info('No active polls.')
        desc = '\n'.join([f'`{p["_id"]}` — **{p["question"][:60]}**' for p in polls[:10]])
        embed = self.bot.embed_manager.generic(description=desc, title=f'Active Polls ({len(polls)})')
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Polls(bot))
