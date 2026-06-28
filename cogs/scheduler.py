import discord
from discord.ext import commands, tasks
import datetime
import re

class Scheduler(commands.Cog):
    category = 'utility'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager

    async def cog_load(self):
        self.scheduled_message_loop.start()

    def cog_unload(self):
        self.scheduled_message_loop.cancel()

    @tasks.loop(seconds=30)
    async def scheduled_message_loop(self):
        now = int(datetime.datetime.utcnow().timestamp())
        messages = await self.db.find('scheduled_messages', {'active': True})
        for msg in messages:
            if now >= msg.get('send_at', 0):
                guild = self.bot.get_guild(msg.get('guild_id'))
                if not guild:
                    await self.db.update_one('scheduled_messages', {'_id': msg['_id']}, {'active': False}, upsert=True)
                    continue
                channel = guild.get_channel(msg.get('channel_id'))
                if channel:
                    try:
                        if msg.get('embed'):
                            embed = discord.Embed(description=msg['content'], color=self.bot.embed_manager.color, timestamp=discord.utils.utcnow())
                            embed.set_footer(text='Scheduled Message')
                            await channel.send(embed=embed)
                        else:
                            await channel.send(msg['content'])
                    except Exception as e:
                        print(f'Scheduler: Failed to send message: {e}')
                if msg.get('repeat_seconds'):
                    next_send = now + msg['repeat_seconds']
                    await self.db.update_one('scheduled_messages', {'_id': msg['_id']}, {'send_at': next_send}, upsert=True)
                else:
                    await self.db.update_one('scheduled_messages', {'_id': msg['_id']}, {'active': False}, upsert=True)

    @scheduled_message_loop.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()

    def _parse_duration(self, s):
        match = re.match(r'(\d+)([mhd])', s.lower())
        if not match:
            return None
        return int(match.group(1)) * {'m': 60, 'h': 3600, 'd': 86400}[match.group(2)]

    @commands.group(name='schedule', aliases=['sched', 'scheduler'], invoke_without_command=True, help='Message scheduler commands.')
    @commands.has_permissions(manage_guild=True)
    async def schedule_group(self, ctx):
        await ctx.send_help(ctx.command)

    @schedule_group.command(name='send', help='Schedule a message. Usage: schedule send #channel 30m Your message here')
    @commands.has_permissions(manage_guild=True)
    async def schedule_send(self, ctx, channel: discord.TextChannel, delay: str, *, content: str):
        seconds = self._parse_duration(delay)
        if not seconds:
            return await ctx.error('Invalid delay. Use `30m`, `2h`, `1d`.')
        if seconds > 2592000:
            return await ctx.error('Maximum schedule delay is 30 days.')
        send_at = int(datetime.datetime.utcnow().timestamp()) + seconds
        msg_id = f'{ctx.guild.id}:{ctx.author.id}:{send_at}'
        await self.db.update_one('scheduled_messages', {'_id': msg_id}, {
            '_id': msg_id, 'guild_id': ctx.guild.id, 'channel_id': channel.id,
            'content': content, 'send_at': send_at, 'active': True,
            'author_id': ctx.author.id, 'embed': False, 'repeat_seconds': None
        }, upsert=True)
        await ctx.success(f'{self.bot.e.success} Message scheduled for {channel.mention} in `{delay}` (<t:{send_at}:R>).')

    @schedule_group.command(name='repeat', help='Schedule a repeating message. Usage: schedule repeat #channel 24h Your daily message')
    @commands.has_permissions(manage_guild=True)
    async def schedule_repeat(self, ctx, channel: discord.TextChannel, interval: str, *, content: str):
        seconds = self._parse_duration(interval)
        if not seconds:
            return await ctx.error('Invalid interval. Use `30m`, `2h`, `1d`.')
        if seconds < 300:
            return await ctx.error('Minimum repeat interval is 5 minutes.')
        send_at = int(datetime.datetime.utcnow().timestamp()) + seconds
        msg_id = f'{ctx.guild.id}:{ctx.author.id}:{send_at}:repeat'
        await self.db.update_one('scheduled_messages', {'_id': msg_id}, {
            '_id': msg_id, 'guild_id': ctx.guild.id, 'channel_id': channel.id,
            'content': content, 'send_at': send_at, 'active': True,
            'author_id': ctx.author.id, 'embed': False, 'repeat_seconds': seconds
        }, upsert=True)
        await ctx.success(f'{self.bot.e.success} Repeating message set for {channel.mention} every `{interval}`.')

    @schedule_group.command(name='list', help='List all scheduled messages for this server.')
    @commands.has_permissions(manage_guild=True)
    async def schedule_list(self, ctx):
        msgs = await self.db.find('scheduled_messages', {'guild_id': ctx.guild.id, 'active': True})
        if not msgs:
            return await ctx.info('No scheduled messages.')
        desc = '\n'.join([
            f'`{m["_id"].split(":")[-1]}` → <#{m["channel_id"]}> <t:{m["send_at"]}:R> — {m["content"][:40]}{"..." if len(m["content"]) > 40 else ""}'
            for m in msgs[:10]
        ])
        embed = self.bot.embed_manager.generic(description=desc, title=f'Scheduled Messages ({len(msgs)})')
        await ctx.send(embed=embed)

    @schedule_group.command(name='cancel', help='Cancel a scheduled message by its ID.')
    @commands.has_permissions(manage_guild=True)
    async def schedule_cancel(self, ctx, msg_id: str):
        data = await self.db.find_one('scheduled_messages', {'_id': msg_id})
        if not data or data.get('guild_id') != ctx.guild.id:
            return await ctx.error('Scheduled message not found.')
        await self.db.update_one('scheduled_messages', {'_id': msg_id}, {'active': False}, upsert=True)
        await ctx.success(f'{self.bot.e.success} Scheduled message cancelled.')

    @schedule_group.command(name='embed', help='Schedule an embedded message. Usage: schedule embed #channel 1h Message content')
    @commands.has_permissions(manage_guild=True)
    async def schedule_embed(self, ctx, channel: discord.TextChannel, delay: str, *, content: str):
        seconds = self._parse_duration(delay)
        if not seconds:
            return await ctx.error('Invalid delay. Use `30m`, `2h`, `1d`.')
        send_at = int(datetime.datetime.utcnow().timestamp()) + seconds
        msg_id = f'{ctx.guild.id}:{ctx.author.id}:{send_at}:embed'
        await self.db.update_one('scheduled_messages', {'_id': msg_id}, {
            '_id': msg_id, 'guild_id': ctx.guild.id, 'channel_id': channel.id,
            'content': content, 'send_at': send_at, 'active': True,
            'author_id': ctx.author.id, 'embed': True, 'repeat_seconds': None
        }, upsert=True)
        await ctx.success(f'{self.bot.e.success} Embedded message scheduled for {channel.mention} in `{delay}`.')

async def setup(bot):
    await bot.add_cog(Scheduler(bot))
