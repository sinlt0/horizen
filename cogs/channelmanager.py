import discord
from discord.ext import commands
import asyncio

class ChannelManager(commands.Cog):
    category = 'utility'

    def __init__(self, bot):
        self.bot = bot

    @commands.group(name='channel', aliases=['ch'], invoke_without_command=True, help='Advanced channel management commands.')
    @commands.has_permissions(manage_channels=True)
    async def channel_group(self, ctx):
        await ctx.send_help(ctx.command)

    @channel_group.command(name='info', help='Show detailed info about a channel.')
    async def channel_info2(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        embed = self.bot.embed_manager.generic(
            description=(
                f'**ID:** `{channel.id}`\n'
                f'**Type:** `{channel.type}`\n'
                f'**Category:** `{channel.category}`\n'
                f'**Topic:** {channel.topic or "`None`"}\n'
                f'**NSFW:** `{channel.is_nsfw()}`\n'
                f'**Slowmode:** `{channel.slowmode_delay}s`\n'
                f'**Position:** `{channel.position}`\n'
                f'**Created:** <t:{int(channel.created_at.timestamp())}:R>\n'
                f'**Threads:** `{len(channel.threads)}`'
            ),
            title=f'#{channel.name}'
        )
        await ctx.send(embed=embed)

    @channel_group.command(name='create', help='Create a new text channel. Usage: channel create name [category]')
    @commands.has_permissions(manage_channels=True)
    async def channel_create(self, ctx, name: str, *, category: discord.CategoryChannel = None):
        ch = await ctx.guild.create_text_channel(name, category=category, reason=f'Created by {ctx.author}')
        await ctx.success(f'{self.bot.e.success} Created {ch.mention}.')

    @channel_group.command(name='createvoice', aliases=['cvc'], help='Create a new voice channel.')
    @commands.has_permissions(manage_channels=True)
    async def channel_createvoice(self, ctx, name: str, *, category: discord.CategoryChannel = None):
        ch = await ctx.guild.create_voice_channel(name, category=category, reason=f'Created by {ctx.author}')
        await ctx.success(f'{self.bot.e.success} Created voice channel **{ch.name}**.')

    @channel_group.command(name='delete', help='Delete a channel.')
    @commands.has_permissions(manage_channels=True)
    async def channel_delete(self, ctx, channel: discord.TextChannel, *, reason: str = 'Staff action'):
        name = channel.name
        await channel.delete(reason=reason)
        await ctx.success(f'{self.bot.e.success} Deleted **#{name}**.')

    @channel_group.command(name='clone', help='Clone a channel.')
    @commands.has_permissions(manage_channels=True)
    async def channel_clone(self, ctx, channel: discord.TextChannel = None, *, new_name: str = None):
        channel = channel or ctx.channel
        new_ch = await channel.clone(name=new_name or f'{channel.name}-copy')
        await ctx.success(f'{self.bot.e.success} Cloned to {new_ch.mention}.')

    @channel_group.command(name='topic', help='Set the topic for a channel.')
    @commands.has_permissions(manage_channels=True)
    async def channel_topic(self, ctx, channel: discord.TextChannel = None, *, topic: str):
        channel = channel or ctx.channel
        await channel.edit(topic=topic[:1024])
        await ctx.success(f'{self.bot.e.success} Topic updated for {channel.mention}.')

    @channel_group.command(name='slowmode', help='Set slowmode for a channel (0 to disable).')
    @commands.has_permissions(manage_channels=True)
    async def channel_slowmode(self, ctx, seconds: int, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        if not 0 <= seconds <= 21600:
            return await ctx.error('Slowmode must be 0–21600 seconds.')
        await channel.edit(slowmode_delay=seconds)
        msg = f'Slowmode disabled on {channel.mention}.' if seconds == 0 else f'Slowmode set to `{seconds}s` on {channel.mention}.'
        await ctx.success(f'{self.bot.e.success} {msg}')

    @channel_group.command(name='nsfw', help='Toggle NSFW mode for a channel.')
    @commands.has_permissions(manage_channels=True)
    async def channel_nsfw(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        await channel.edit(nsfw=not channel.is_nsfw())
        state = 'enabled' if channel.is_nsfw() else 'disabled'
        await ctx.success(f'{self.bot.e.success} NSFW **{state}** for {channel.mention}.')

    @channel_group.command(name='rename', help='Rename a channel.')
    @commands.has_permissions(manage_channels=True)
    async def channel_rename(self, ctx, channel: discord.TextChannel = None, *, name: str):
        channel = channel or ctx.channel
        old = channel.name
        await channel.edit(name=name)
        await ctx.success(f'{self.bot.e.success} Renamed **#{old}** → **#{name}**.')

    @channel_group.command(name='move', help='Move a channel to a different category.')
    @commands.has_permissions(manage_channels=True)
    async def channel_move(self, ctx, channel: discord.TextChannel, category: discord.CategoryChannel):
        await channel.edit(category=category)
        await ctx.success(f'{self.bot.e.success} Moved {channel.mention} to **{category.name}**.')

    @channel_group.command(name='lock', help='Lock a channel, preventing messages.')
    @commands.has_permissions(manage_channels=True)
    async def channel_lock2(self, ctx, channel: discord.TextChannel = None, *, reason: str = None):
        channel = channel or ctx.channel
        ow = channel.overwrites_for(ctx.guild.default_role)
        ow.send_messages = False
        await channel.set_permissions(ctx.guild.default_role, overwrite=ow, reason=reason)
        await ctx.success(f'{self.bot.e.success} 🔒 {channel.mention} locked.')

    @channel_group.command(name='unlock', help='Unlock a previously locked channel.')
    @commands.has_permissions(manage_channels=True)
    async def channel_unlock2(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        ow = channel.overwrites_for(ctx.guild.default_role)
        ow.send_messages = None
        await channel.set_permissions(ctx.guild.default_role, overwrite=ow)
        await ctx.success(f'{self.bot.e.success} 🔓 {channel.mention} unlocked.')

    @channel_group.command(name='hide', help='Hide a channel from all members.')
    @commands.has_permissions(manage_channels=True)
    async def channel_hide2(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        ow = channel.overwrites_for(ctx.guild.default_role)
        ow.view_channel = False
        await channel.set_permissions(ctx.guild.default_role, overwrite=ow)
        await ctx.success(f'{self.bot.e.success} {channel.mention} hidden.')

    @channel_group.command(name='show', help='Unhide a previously hidden channel.')
    @commands.has_permissions(manage_channels=True)
    async def channel_show(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        ow = channel.overwrites_for(ctx.guild.default_role)
        ow.view_channel = None
        await channel.set_permissions(ctx.guild.default_role, overwrite=ow)
        await ctx.success(f'{self.bot.e.success} {channel.mention} is now visible.')

    @channel_group.command(name='sync', help='Sync a channel\'s permissions with its category.')
    @commands.has_permissions(manage_channels=True)
    async def channel_sync(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        if not channel.category:
            return await ctx.error('This channel has no category to sync with.')
        await channel.edit(sync_permissions=True)
        await ctx.success(f'{self.bot.e.success} {channel.mention} permissions synced with **{channel.category.name}**.')

    @channel_group.command(name='purge', help='Bulk delete messages from a channel (1-1000).')
    @commands.has_permissions(manage_messages=True)
    async def channel_purge(self, ctx, amount: int, member: discord.Member = None):
        if not 1 <= amount <= 1000:
            return await ctx.error('Amount must be between 1 and 1000.')
        def check(m):
            return m.author == member if member else True
        deleted = await ctx.channel.purge(limit=amount + 1, check=check)
        await ctx.send(f'{self.bot.e.success} Deleted `{len(deleted) - 1}` messages.', delete_after=5)

    @channel_group.command(name='list', help='List all channels grouped by category.')
    async def channel_list(self, ctx):
        categories = {}
        for ch in ctx.guild.channels:
            cat_name = ch.category.name if ch.category else 'No Category'
            categories.setdefault(cat_name, []).append(ch)
        lines = []
        for cat, channels in sorted(categories.items()):
            lines.append(f'**{cat}**')
            for ch in channels[:8]:
                icon = '💬' if isinstance(ch, discord.TextChannel) else '🔊' if isinstance(ch, discord.VoiceChannel) else '📁'
                lines.append(f'  {icon} {ch.name}')
        embed = self.bot.embed_manager.generic(
            description='\n'.join(lines[:50]),
            title=f'📋 Channels ({len(ctx.guild.channels)})'
        )
        await ctx.send(embed=embed)

    @channel_group.command(name='threads', help='List active threads in a channel.')
    async def channel_threads(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        threads = channel.threads
        if not threads:
            return await ctx.info(f'No active threads in {channel.mention}.')
        desc = '\n'.join([f'• **{t.name}** — `{t.message_count}` messages' for t in threads[:20]])
        embed = self.bot.embed_manager.generic(description=desc, title=f'🧵 Threads in #{channel.name}')
        await ctx.send(embed=embed)

    @channel_group.command(name='overrides', help='Show permission overrides for a channel.')
    @commands.has_permissions(manage_channels=True)
    async def channel_overrides(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        overwrites = channel.overwrites
        if not overwrites:
            return await ctx.info('No permission overrides set.')
        lines = []
        for target, ow in list(overwrites.items())[:15]:
            granted = [p.replace('_', ' ').title() for p, v in ow if v is True]
            denied = [p.replace('_', ' ').title() for p, v in ow if v is False]
            name = target.mention if hasattr(target, 'mention') else str(target)
            lines.append(f'**{name}**')
            if granted: lines.append(f'  ✅ {", ".join(granted[:5])}')
            if denied: lines.append(f'  ❌ {", ".join(denied[:5])}')
        embed = self.bot.embed_manager.generic(description='\n'.join(lines), title=f'🔐 Overrides — #{channel.name}')
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ChannelManager(bot))
