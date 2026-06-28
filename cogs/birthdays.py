import discord
from discord.ext import commands, tasks
import datetime

class Birthdays(commands.Cog):
    category = 'utility'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager

    async def cog_load(self):
        self.birthday_check.start()

    def cog_unload(self):
        self.birthday_check.cancel()

    @tasks.loop(hours=1)
    async def birthday_check(self):
        now = datetime.datetime.utcnow()
        if now.hour != 8:
            return
        configs = await self.db.find('birthday_config', {})
        for config in configs:
            guild = self.bot.get_guild(config['_id'])
            if not guild:
                continue
            channel = guild.get_channel(config.get('channel_id', 0))
            if not channel:
                continue
            birthdays = await self.db.find('birthdays', {'guild_id': guild.id})
            for b in birthdays:
                if b.get('month') == now.month and b.get('day') == now.day:
                    member = guild.get_member(b['user_id'])
                    if not member:
                        continue
                    role_id = config.get('role_id')
                    if role_id:
                        role = guild.get_role(role_id)
                        if role:
                            try:
                                await member.add_roles(role)
                            except Exception:
                                pass
                    msg = config.get('message', '🎂 Happy Birthday {mention}! Hope you have an amazing day!')
                    await channel.send(msg.replace('{mention}', member.mention).replace('{name}', member.display_name))

    @birthday_check.before_loop
    async def before_birthday_check(self):
        await self.bot.wait_until_ready()

    @commands.group(name='birthday', aliases=['bday', 'bd'], invoke_without_command=True, help='Birthday system commands.')
    async def birthday_group(self, ctx):
        await ctx.send_help(ctx.command)

    @birthday_group.command(name='set', help='Set your birthday. Usage: birthday set MM/DD')
    async def birthday_set(self, ctx, date: str):
        try:
            parts = date.split('/')
            month, day = int(parts[0]), int(parts[1])
            if not (1 <= month <= 12 and 1 <= day <= 31):
                raise ValueError
        except Exception:
            return await ctx.error('Invalid date. Use `MM/DD` format e.g. `12/25`.')
        key = f'{ctx.guild.id}:{ctx.author.id}'
        await self.db.update_one('birthdays', {'_id': key}, {
            '_id': key, 'user_id': ctx.author.id, 'guild_id': ctx.guild.id,
            'month': month, 'day': day
        }, upsert=True)
        await ctx.success(f'{self.bot.e.success} Birthday set to **{month:02d}/{day:02d}**.')

    @birthday_group.command(name='remove', help='Remove your birthday from this server.')
    async def birthday_remove(self, ctx):
        key = f'{ctx.guild.id}:{ctx.author.id}'
        await self.db.delete_one('birthdays', {'_id': key})
        await ctx.success(f'{self.bot.e.success} Birthday removed.')

    @birthday_group.command(name='check', help='Check a member\'s birthday.')
    async def birthday_check_cmd(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        key = f'{ctx.guild.id}:{member.id}'
        data = await self.db.find_one('birthdays', {'_id': key})
        if not data:
            return await ctx.info(f'{member.mention} has not set their birthday.')
        await ctx.success(f'{member.mention}\'s birthday is **{data["month"]:02d}/{data["day"]:02d}**.')

    @birthday_group.command(name='list', help='List upcoming birthdays in this server.')
    async def birthday_list(self, ctx):
        birthdays = await self.db.find('birthdays', {'guild_id': ctx.guild.id})
        if not birthdays:
            return await ctx.info('No birthdays set in this server.')
        now = datetime.datetime.utcnow()
        def sort_key(b):
            m, d = b.get('month', 1), b.get('day', 1)
            if (m, d) >= (now.month, now.day):
                return (m, d)
            return (m + 12, d)
        birthdays = sorted(birthdays, key=sort_key)[:15]
        desc = '\n'.join([
            f'<@{b["user_id"]}> — **{b["month"]:02d}/{b["day"]:02d}**'
            for b in birthdays
        ])
        embed = self.bot.embed_manager.generic(description=desc, title='🎂 Upcoming Birthdays')
        await ctx.send(embed=embed)

    @birthday_group.command(name='setup', help='Configure the birthday channel and optional role.')
    @commands.has_permissions(manage_guild=True)
    async def birthday_setup(self, ctx, channel: discord.TextChannel, role: discord.Role = None):
        data = {'channel_id': channel.id}
        if role:
            data['role_id'] = role.id
        await self.db.update_one('birthday_config', {'_id': ctx.guild.id}, data, upsert=True)
        msg = f'{self.bot.e.success} Birthday channel set to {channel.mention}.'
        if role:
            msg += f' Birthday role: {role.mention}.'
        await ctx.success(msg)

    @birthday_group.command(name='setmessage', help='Set a custom birthday message. Use {mention} and {name}.')
    @commands.has_permissions(manage_guild=True)
    async def birthday_setmessage(self, ctx, *, message: str):
        await self.db.update_one('birthday_config', {'_id': ctx.guild.id}, {'message': message}, upsert=True)
        await ctx.success(f'{self.bot.e.success} Birthday message updated.')

    @birthday_group.command(name='today', help='Show whose birthday it is today.')
    async def birthday_today(self, ctx):
        now = datetime.datetime.utcnow()
        birthdays = await self.db.find('birthdays', {'guild_id': ctx.guild.id})
        today = [b for b in birthdays if b.get('month') == now.month and b.get('day') == now.day]
        if not today:
            return await ctx.info('No birthdays today.')
        mentions = ', '.join([f'<@{b["user_id"]}>' for b in today])
        await ctx.send(f'🎂 Happy Birthday to {mentions}!')

async def setup(bot):
    await bot.add_cog(Birthdays(bot))
