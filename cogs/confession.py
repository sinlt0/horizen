import discord
from discord.ext import commands

class Confession(commands.Cog):
    category = 'utility'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager

    @commands.group(name='confession', aliases=['confess', 'cf'], invoke_without_command=True, help='Anonymous confession system commands.')
    async def confession_group(self, ctx):
        await ctx.send_help(ctx.command)

    @confession_group.command(name='setup', help='Set the confession channel.')
    @commands.has_permissions(manage_guild=True)
    async def confession_setup(self, ctx, channel: discord.TextChannel):
        await self.db.update_one('confession_config', {'_id': ctx.guild.id}, {
            'channel_id': channel.id, 'count': 0, 'enabled': True
        }, upsert=True)
        await ctx.success(f'{self.bot.e.success} Confession channel set to {channel.mention}.')

    @confession_group.command(name='send', help='Send an anonymous confession.')
    async def confession_send(self, ctx, *, message: str):
        if len(message) > 2000:
            return await ctx.error('Confession must be under 2000 characters.')
        config = await self.db.find_one('confession_config', {'_id': ctx.guild.id})
        if not config or not config.get('enabled', True):
            return await ctx.error('Confessions are not enabled or configured.')
        channel = ctx.guild.get_channel(config.get('channel_id', 0))
        if not channel:
            return await ctx.error('Confession channel not found.')
        count = config.get('count', 0) + 1
        embed = discord.Embed(
            description=message,
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_author(name=f'Anonymous Confession #{count}')
        embed.set_footer(text=ctx.guild.name)
        msg = await channel.send(embed=embed)
        await msg.add_reaction('❤️')
        await msg.add_reaction('🤝')
        await self.db.update_one('confession_config', {'_id': ctx.guild.id}, {'count': count}, upsert=True)
        try:
            await ctx.message.delete()
        except Exception:
            pass
        try:
            await ctx.author.send(f'{self.bot.e.success} Your confession #{count} has been sent anonymously.')
        except Exception:
            pass

    @confession_group.command(name='toggle', help='Enable or disable the confession system.')
    @commands.has_permissions(manage_guild=True)
    async def confession_toggle(self, ctx):
        config = await self.db.find_one('confession_config', {'_id': ctx.guild.id})
        if not config:
            return await ctx.error('Confession system not configured.')
        new_state = not config.get('enabled', True)
        await self.db.update_one('confession_config', {'_id': ctx.guild.id}, {'enabled': new_state}, upsert=True)
        state = 'enabled' if new_state else 'disabled'
        await ctx.success(f'{self.bot.e.success} Confessions **{state}**.')

    @confession_group.command(name='stats', help='Show confession stats for this server.')
    async def confession_stats(self, ctx):
        config = await self.db.find_one('confession_config', {'_id': ctx.guild.id})
        if not config:
            return await ctx.info('Confession system not configured.')
        embed = self.bot.embed_manager.generic(
            description=(
                f'**Channel:** <#{config.get("channel_id", 0)}>\n'
                f'**Total Confessions:** `{config.get("count", 0)}`\n'
                f'**Status:** `{"Enabled" if config.get("enabled", True) else "Disabled"}`'
            ),
            title='🤫 Confession Stats'
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Confession(bot))
