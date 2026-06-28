import discord
from discord.ext import commands

class Counting(commands.Cog):
    category = 'utility'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager
        self._cache = {}

    async def cog_load(self):
        configs = await self.db.find('counting_config', {})
        for c in configs:
            self._cache[c['_id']] = c

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        config = self._cache.get(message.guild.id)
        if not config or config.get('channel_id') != message.channel.id:
            return
        content = message.content.strip()
        if not content.lstrip('-').isdigit():
            if config.get('delete_invalid', True):
                try:
                    await message.delete()
                except Exception:
                    pass
            return
        num = int(content)
        expected = config.get('count', 0) + 1
        last_user = config.get('last_user')
        if num != expected:
            await message.add_reaction('❌')
            fail_msg = await message.channel.send(
                f'❌ {message.author.mention} ruined it at **{config["count"]}**! Next number is `1`.'
            )
            config['count'] = 0
            config['last_user'] = None
            config['record'] = max(config.get('record', 0), config.get('count', 0))
            await self.db.update_one('counting_config', {'_id': message.guild.id}, config, upsert=True)
            self._cache[message.guild.id] = config
            return
        if last_user == message.author.id:
            await message.add_reaction('❌')
            await message.channel.send(f'❌ {message.author.mention} you can\'t count twice in a row! Reset to `1`.')
            config['count'] = 0
            config['last_user'] = None
            await self.db.update_one('counting_config', {'_id': message.guild.id}, config, upsert=True)
            self._cache[message.guild.id] = config
            return
        await message.add_reaction('✅')
        config['count'] = num
        config['last_user'] = message.author.id
        if num > config.get('record', 0):
            config['record'] = num
            if num % 100 == 0:
                await message.channel.send(f'🎉 New record: **{num}**!')
        await self.db.update_one('counting_config', {'_id': message.guild.id}, config, upsert=True)
        self._cache[message.guild.id] = config

    @commands.group(name='counting', aliases=['count'], invoke_without_command=True, help='Counting channel management.')
    @commands.has_permissions(manage_channels=True)
    async def counting_group(self, ctx):
        await ctx.send_help(ctx.command)

    @counting_group.command(name='setup', help='Set the counting channel.')
    @commands.has_permissions(manage_channels=True)
    async def counting_setup(self, ctx, channel: discord.TextChannel):
        config = {'_id': ctx.guild.id, 'channel_id': channel.id, 'count': 0, 'last_user': None, 'record': 0, 'delete_invalid': True}
        await self.db.update_one('counting_config', {'_id': ctx.guild.id}, config, upsert=True)
        self._cache[ctx.guild.id] = config
        await ctx.success(f'{self.bot.e.success} Counting channel set to {channel.mention}. Start at **1**!')

    @counting_group.command(name='stats', help='Show counting stats for this server.')
    async def counting_stats(self, ctx):
        config = self._cache.get(ctx.guild.id) or await self.db.find_one('counting_config', {'_id': ctx.guild.id})
        if not config:
            return await ctx.info('No counting channel configured.')
        embed = self.bot.embed_manager.generic(
            description=(
                f'**Current Count:** `{config.get("count", 0)}`\n'
                f'**Record:** `{config.get("record", 0)}`\n'
                f'**Channel:** <#{config.get("channel_id", 0)}>\n'
                f'**Last Counter:** <@{config["last_user"]}>' if config.get('last_user') else ''
            ),
            title='🔢 Counting Stats'
        )
        await ctx.send(embed=embed)

    @counting_group.command(name='reset', help='Reset the count back to 0.')
    @commands.has_permissions(manage_channels=True)
    async def counting_reset(self, ctx):
        config = self._cache.get(ctx.guild.id) or {}
        config['count'] = 0
        config['last_user'] = None
        await self.db.update_one('counting_config', {'_id': ctx.guild.id}, config, upsert=True)
        self._cache[ctx.guild.id] = config
        await ctx.success(f'{self.bot.e.success} Count reset. Start at **1**!')

    @counting_group.command(name='scount', help='Set the current count to a specific number.')
    @commands.has_permissions(manage_guild=True)
    async def counting_scount(self, ctx, number: int):
        config = self._cache.get(ctx.guild.id) or {}
        config['count'] = number
        config['last_user'] = None
        await self.db.update_one('counting_config', {'_id': ctx.guild.id}, config, upsert=True)
        self._cache[ctx.guild.id] = config
        await ctx.success(f'{self.bot.e.success} Count set to **{number}**. Next: `{number + 1}`.')

    @counting_group.command(name='toggle', aliases=['toggledelete'], help='Toggle deletion of invalid messages in counting channel.')
    @commands.has_permissions(manage_channels=True)
    async def counting_toggle(self, ctx):
        config = self._cache.get(ctx.guild.id) or {}
        config['delete_invalid'] = not config.get('delete_invalid', True)
        await self.db.update_one('counting_config', {'_id': ctx.guild.id}, config, upsert=True)
        self._cache[ctx.guild.id] = config
        state = 'enabled' if config['delete_invalid'] else 'disabled'
        await ctx.success(f'{self.bot.e.success} Invalid message deletion **{state}**.')

async def setup(bot):
    await bot.add_cog(Counting(bot))
