import discord
from discord.ext import commands, tasks
import datetime

DISBOARD_ID = 302050872383242240

class Bumper(commands.Cog):
    category = 'utility'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager

    async def cog_load(self):
        self.bump_reminder_loop.start()

    def cog_unload(self):
        self.bump_reminder_loop.cancel()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id != DISBOARD_ID:
            return
        if not message.guild:
            return
        if message.embeds and 'bump' in str(message.embeds[0].description or '').lower():
            config = await self.db.find_one('bump_config', {'_id': message.guild.id})
            if not config or not config.get('enabled', True):
                return
            next_bump = int(discord.utils.utcnow().timestamp()) + 7200
            await self.db.update_one('bump_config', {'_id': message.guild.id}, {
                'last_bump': int(discord.utils.utcnow().timestamp()),
                'next_bump': next_bump,
                'last_bumper': message.interaction.user.id if message.interaction else None
            }, upsert=True)
            channel = message.guild.get_channel(config.get('channel_id', message.channel.id))
            if channel:
                await channel.send(f'⏰ Next bump available <t:{next_bump}:R>! I\'ll remind you.')

    @tasks.loop(minutes=5)
    async def bump_reminder_loop(self):
        now = int(discord.utils.utcnow().timestamp())
        configs = await self.db.find('bump_config', {})
        for config in configs:
            if not config.get('enabled', True):
                continue
            if not config.get('next_bump'):
                continue
            if config.get('reminded'):
                continue
            if now >= config['next_bump']:
                guild = self.bot.get_guild(config['_id'])
                if not guild:
                    continue
                channel = guild.get_channel(config.get('channel_id', 0))
                if not channel:
                    continue
                role_id = config.get('remind_role')
                mention = f'<@&{role_id}>' if role_id else ''
                await channel.send(f'🔔 {mention} Time to bump the server! Use `/bump` on Disboard.')
                await self.db.update_one('bump_config', {'_id': config['_id']}, {'reminded': True}, upsert=True)

    @bump_reminder_loop.before_loop
    async def before_bump_reminder(self):
        await self.bot.wait_until_ready()

    @commands.group(name='bumper', aliases=['bumpreminder', 'bremind'], invoke_without_command=True, help='Bump reminder system commands.')
    @commands.has_permissions(manage_guild=True)
    async def bumper_group(self, ctx):
        await ctx.send_help(ctx.command)

    @bumper_group.command(name='setup', help='Set the channel for bump reminders.')
    @commands.has_permissions(manage_guild=True)
    async def bumper_setup(self, ctx, channel: discord.TextChannel, role: discord.Role = None):
        data = {'channel_id': channel.id, 'enabled': True, 'reminded': False}
        if role:
            data['remind_role'] = role.id
        await self.db.update_one('bump_config', {'_id': ctx.guild.id}, data, upsert=True)
        msg = f'{self.bot.e.success} Bump reminders set to {channel.mention}.'
        if role:
            msg += f' Will ping {role.mention}.'
        await ctx.success(msg)

    @bumper_group.command(name='toggle', help='Enable or disable bump reminders.')
    @commands.has_permissions(manage_guild=True)
    async def bumper_toggle(self, ctx):
        config = await self.db.find_one('bump_config', {'_id': ctx.guild.id})
        if not config:
            return await ctx.error('Bump reminder not configured.')
        new = not config.get('enabled', True)
        await self.db.update_one('bump_config', {'_id': ctx.guild.id}, {'enabled': new}, upsert=True)
        await ctx.success(f'{self.bot.e.success} Bump reminders **{"enabled" if new else "disabled"}**.')

    @bumper_group.command(name='stats', help='Show bump statistics for this server.')
    async def bumper_stats(self, ctx):
        config = await self.db.find_one('bump_config', {'_id': ctx.guild.id})
        if not config:
            return await ctx.info('Bump reminder not configured.')
        last = f"<t:{config['last_bump']}:R>" if config.get('last_bump') else "`Never`"
        nxt = f"<t:{config['next_bump']}:R>" if config.get('next_bump') else "`Unknown`"
        embed = self.bot.embed_manager.generic(
            description=(
                f"**Channel:** <#{config.get('channel_id', 0)}>\n"
                f"**Status:** `{'Enabled' if config.get('enabled', True) else 'Disabled'}`\n"
                f"**Last Bump:** {last}\n"
                f"**Next Bump:** {nxt}"
            ),
            title='📊 Bump Stats'
        )
        await ctx.send(embed=embed)

    @bumper_group.command(name='setrole', help='Set the role to ping for bump reminders.')
    @commands.has_permissions(manage_guild=True)
    async def bumper_setrole(self, ctx, role: discord.Role):
        await self.db.update_one('bump_config', {'_id': ctx.guild.id}, {'remind_role': role.id}, upsert=True)
        await ctx.success(f'{self.bot.e.success} Bump reminder role set to {role.mention}.')

async def setup(bot):
    await bot.add_cog(Bumper(bot))
