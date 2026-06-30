import discord
from discord.ext import commands
import re
import datetime
import time
import aiohttp
from typing import Optional, Union

class DurationConverter(commands.Converter):

    async def convert(self, ctx, argument):
        amount = argument[:-1]
        unit = argument[-1].lower()
        if amount.isdigit() and unit in ['s', 'm', 'h', 'd', 'w']:
            return (int(amount), unit)
        raise commands.BadArgument('Invalid duration format. Use e.g. 10m, 1h, 1d.')

class Moderation(commands.Cog):
    category = 'moderation'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager
        self.session = aiohttp.ClientSession()

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    @commands.command(name="nuke", help="Clones and deletes the current channel to clear history.")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def nuke_cmd(self, ctx):
        channel = ctx.channel
        pos = channel.position
        new_channel = await channel.clone(reason=f"Nuke by {ctx.author}")
        await new_channel.edit(position=pos)
        await channel.delete(reason=f"Nuke by {ctx.author}")
        
        embed = self.bot.embed_manager.success(
            f"Channel has been nuked by {ctx.author.mention}",
            title="Nuked!"
        )
        embed.set_image(url="https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExMnhicHkzbmR4bmR4bmR4bmR4bmR4bmR4bmR4bmR4bmR4bmR4bmR4bmR4JmVwPXYxX2ludGVybmFsX2dpZl9ieV9pZCZjdD1n/HhTXt43pk1I1W/giphy.gif")
        await new_channel.send(embed=embed)

    async def get_case_id(self, guild_id):
        config = await self.db.find_one('mod_config', {'_id': guild_id})
        if not config:
            case_id = 1
        else:
            case_id = config.get('case_count', 0) + 1
        await self.db.update_one('mod_config', {'_id': guild_id}, {'case_count': case_id}, upsert=True)
        return case_id

    async def log_action(self, ctx, action_type, target, reason, duration=None):
        case_id = await self.get_case_id(ctx.guild.id)
        timestamp = time.time()
        data = {'case_id': case_id, 'guild_id': ctx.guild.id, 'target_id': target.id, 'mod_id': ctx.author.id, 'type': action_type, 'reason': reason, 'duration': duration, 'timestamp': timestamp}
        await self.db.insert_one('mod_cases', {'_id': f'{ctx.guild.id}-{case_id}', **data})
        
        log_cog = self.bot.get_cog('Logging')
        if log_cog:
            embed = discord.Embed(
                title=f'Case #{case_id} | {action_type}', 
                description=f'**Target:** {target.mention} ({target.id})\n**Moderator:** {ctx.author.mention}\n**Reason:** {reason}' + (f'\n**Duration:** {duration}' if duration else ''), 
                color=discord.Color.orange(), 
                timestamp=datetime.datetime.fromtimestamp(timestamp)
            )
            embed.set_footer(text=f'ID: {target.id}')
            await log_cog.log_mod(ctx.guild, embed)
        
        return case_id

    @commands.command(name='kick', help='Kick a member from the server.')
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str='No reason provided'):
        if member.top_role >= ctx.author.top_role and not await ctx.is_extra_owner():
            return await ctx.error('You cannot kick someone with a higher or equal role.')
        try:
            await member.kick(reason=f'Mod: {ctx.author} | Reason: {reason}')
            case_id = await self.log_action(ctx, 'Kick', member, reason)
            await ctx.success(f'**{member}** has been kicked. (Case #{case_id})')
        except discord.Forbidden:
            await ctx.error('I do not have permission to kick this member.')

    @commands.command(name='ban', help='Ban a user from the server.')
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, user: Union[discord.Member, discord.User], *, reason: str='No reason provided'):
        if isinstance(user, discord.Member):
            if user.top_role >= ctx.author.top_role and not await ctx.is_extra_owner():
                return await ctx.error('You cannot ban someone with a higher or equal role.')
        try:
            await ctx.guild.ban(user, reason=f'Mod: {ctx.author} | Reason: {reason}')
            case_id = await self.log_action(ctx, 'Ban', user, reason)
            await ctx.success(f'**{user}** has been banned. (Case #{case_id})')
        except discord.Forbidden:
            await ctx.error('I do not have permission to ban this user.')

    @commands.command(name='unban', help='Unban a user from the server.')
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user_id: int, *, reason: str='No reason provided'):
        try:
            user = await self.bot.fetch_user(user_id)
            await ctx.guild.unban(user, reason=f'Mod: {ctx.author} | Reason: {reason}')
            case_id = await self.log_action(ctx, 'Unban', user, reason)
            await ctx.success(f'**{user}** has been unbanned. (Case #{case_id})')
        except discord.NotFound:
            await ctx.error('User not found or not banned.')
        except discord.Forbidden:
            await ctx.error('I do not have permission to unban this user.')

    @commands.command(name='mute', aliases=['timeout'], help='Timeout a member for a specified duration.')
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx, member: discord.Member, duration: DurationConverter, *, reason: str='No reason provided'):
        if member.top_role >= ctx.author.top_role and not await ctx.is_extra_owner():
            return await ctx.error('You cannot mute someone with a higher or equal role.')
        amount, unit = duration
        delta = None
        if unit == 's':
            delta = datetime.timedelta(seconds=amount)
        elif unit == 'm':
            delta = datetime.timedelta(minutes=amount)
        elif unit == 'h':
            delta = datetime.timedelta(hours=amount)
        elif unit == 'd':
            delta = datetime.timedelta(days=amount)
        elif unit == 'w':
            delta = datetime.timedelta(weeks=amount)
        if delta.total_seconds() > 2419200:
            return await ctx.error('Timeout duration cannot exceed 28 days.')
        try:
            await member.timeout(delta, reason=f'Mod: {ctx.author} | Reason: {reason}')
            rep_cog = self.bot.get_cog("ReputationSystem")
            if rep_cog: rep_cog.award_points_external(ctx.guild.id, member.id, "timeout")
            duration_str = f'{amount}{unit}'
            case_id = await self.log_action(ctx, 'Mute', member, reason, duration_str)
            await ctx.success(f'**{member}** has been muted for {duration_str}. (Case #{case_id})')
        except discord.Forbidden:
            await ctx.error('I do not have permission to mute this member.')

    @commands.command(name='unmute', aliases=['untimeout'], help='Remove timeout from a member.')
    @commands.has_permissions(moderate_members=True)
    async def unmute(self, ctx, member: discord.Member, *, reason: str='No reason provided'):
        try:
            await member.timeout(None, reason=f'Mod: {ctx.author} | Reason: {reason}')
            rep_cog = self.bot.get_cog("ReputationSystem")
            if rep_cog: rep_cog.award_points_external(ctx.guild.id, member.id, "timeout")
            case_id = await self.log_action(ctx, 'Unmute', member, reason)
            await ctx.success(f'**{member}** has been unmuted. (Case #{case_id})')
        except discord.Forbidden:
            await ctx.error('I do not have permission to unmute this member.')

    @commands.command(name='warn', help='Warn a member.')
    @commands.has_permissions(moderate_members=True)
    async def warn(self, ctx, member: discord.Member, *, reason: str='No reason provided'):
        if member.bot:
            return await ctx.error('You cannot warn bots.')
        warn_key = f'warns:{ctx.guild.id}:{member.id}'
        res = await self.db.find_one('mod_cases', {'_id': warn_key})
        warn_count = (res.get('count', 0) if res else 0) + 1
        await self.db.update_one('mod_cases', {'_id': warn_key}, {'count': warn_count}, upsert=True)
        case_id = await self.log_action(ctx, 'Warn', member, reason)
        rep_cog = self.bot.get_cog('ReputationSystem')
        if rep_cog:
            rep_cog.award_points_external(ctx.guild.id, member.id, 'warn')
        await ctx.success(f'**{member}** has been warned. (Total: {warn_count} | Case #{case_id})')

    @commands.command(name='warns', aliases=['warnings'], help='View warnings for a member.')
    @commands.has_permissions(moderate_members=True)
    async def warns(self, ctx, member: discord.Member):
        warn_key = f'warns:{ctx.guild.id}:{member.id}'
        res = await self.db.find_one('mod_cases', {'_id': warn_key})
        count = res.get('count', 0) if res else 0
        await ctx.info(f'**{member}** has **{count}** warnings in this server.', title='Warnings')

    @commands.command(name='delwarn', aliases=['clearwarns'], help='Clear all warnings for a member.')
    @commands.has_permissions(administrator=True)
    async def delwarn(self, ctx, member: discord.Member):
        warn_key = f'warns:{ctx.guild.id}:{member.id}'
        await self.db.delete_one('mod_cases', {'_id': warn_key})
        await ctx.success(f'Cleared all warnings for **{member}**.')

    @commands.command(name='purge', aliases=['clear'], help='Delete a specified number of messages.')
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int):
        if amount < 1 or amount > 100:
            return await ctx.error('Please specify an amount between 1 and 100.')
        await ctx.message.delete()
        deleted = await ctx.channel.purge(limit=amount)
        await ctx.success(f'Deleted `{len(deleted)}` messages.', delete_after=5)

    @commands.command(name='modconfig', help='Configure moderation settings.')
    @commands.has_permissions(administrator=True)
    async def modconfig(self, ctx, setting: str, value: discord.TextChannel=None):
        setting = setting.lower()
        if setting == 'logs':
            if not value:
                return await ctx.error('Please mention a channel to set as the log channel.')
            await self.db.update_one('mod_config', {'_id': ctx.guild.id}, {'log_channel': value.id}, upsert=True)
            await ctx.success(f'Moderation logs will now be sent to {value.mention}.')
        else:
            await ctx.error('Unknown setting. Available: `logs`')

async def setup(bot):
    await bot.add_cog(Moderation(bot))
