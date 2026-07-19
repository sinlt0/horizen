import discord
from discord.ext import commands
import datetime

class ServerStats2(commands.Cog):
    category = 'utility'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager

    @commands.command(name='channelcount', help='Count channels by type in this server.')
    async def channelcount(self, ctx):
        text = len(ctx.guild.text_channels)
        voice = len(ctx.guild.voice_channels)
        categories = len(ctx.guild.categories)
        stages = len(ctx.guild.stage_channels)
        forums = len([c for c in ctx.guild.channels if c.type == discord.ChannelType.forum])
        await ctx.send(f'📊 Text: `{text}` | Voice: `{voice}` | Categories: `{categories}` | Stage: `{stages}` | Forum: `{forums}`')

    @commands.command(name='rolecount', help='Count total roles in this server.')
    async def rolecount(self, ctx):
        count = len(ctx.guild.roles) - 1
        await ctx.send(f'🎭 This server has **{count}** roles.')

    @commands.command(name='emojicount', help='Count total emojis in this server.')
    async def emojicount(self, ctx):
        static = len([e for e in ctx.guild.emojis if not e.animated])
        animated = len([e for e in ctx.guild.emojis if e.animated])
        limit = ctx.guild.emoji_limit
        await ctx.send(f'😀 Static: `{static}` | Animated: `{animated}` | Limit: `{limit}` each')

    @commands.command(name='boostprogress', help='Show boost progress to the next tier.')
    async def boostprogress(self, ctx):
        tier_thresholds = {0: 2, 1: 7, 2: 14}
        current_tier = ctx.guild.premium_tier
        current_boosts = ctx.guild.premium_subscription_count
        if current_tier >= 3:
            return await ctx.send('🎉 This server is already at the maximum boost tier!')
        needed = tier_thresholds.get(current_tier, 2)
        remaining = max(0, needed - current_boosts)
        pct = min(100, int((current_boosts / needed) * 100))
        bar = '█' * (pct // 10) + '░' * (10 - pct // 10)
        await ctx.send(f'💎 Tier `{current_tier}` → `{current_tier + 1}`\n{bar} `{pct}%`\n`{remaining}` more boost(s) needed.')

    @commands.command(name='verificationlevel', help='Show this server\'s verification level.')
    async def verificationlevel(self, ctx):
        levels = {
            discord.VerificationLevel.none: 'None — no restrictions',
            discord.VerificationLevel.low: 'Low — must have a verified email',
            discord.VerificationLevel.medium: 'Medium — must be registered for 5+ minutes',
            discord.VerificationLevel.high: 'High — must be a member for 10+ minutes',
            discord.VerificationLevel.highest: 'Highest — must have a verified phone',
        }
        level = ctx.guild.verification_level
        await ctx.send(f'🛡️ Verification Level: **{level.name.capitalize()}**\n{levels.get(level, "Unknown")}')

    @commands.command(name='contentfilter', help='Show this server\'s explicit content filter setting.')
    async def contentfilter(self, ctx):
        filters = {
            discord.ContentFilter.disabled: 'Disabled',
            discord.ContentFilter.no_role: 'Scan messages from members without a role',
            discord.ContentFilter.all_members: 'Scan messages from all members',
        }
        await ctx.send(f'🔍 Content Filter: **{filters.get(ctx.guild.explicit_content_filter, "Unknown")}**')

    @commands.command(name='afkchannel', help='Show this server\'s configured AFK voice channel.')
    async def afkchannel(self, ctx):
        if not ctx.guild.afk_channel:
            return await ctx.info('No AFK channel configured.')
        await ctx.send(f'💤 AFK Channel: {ctx.guild.afk_channel.mention} (timeout: `{ctx.guild.afk_timeout // 60}` min)')

    @commands.command(name='systemchannel', help='Show this server\'s configured system messages channel.')
    async def systemchannel(self, ctx):
        if not ctx.guild.system_channel:
            return await ctx.info('No system channel configured.')
        await ctx.send(f'📢 System Channel: {ctx.guild.system_channel.mention}')

    @commands.command(name='rulechannel', help='Show this server\'s configured rules channel.')
    async def rulechannel(self, ctx):
        if not ctx.guild.rules_channel:
            return await ctx.info('No rules channel configured.')
        await ctx.send(f'📋 Rules Channel: {ctx.guild.rules_channel.mention}')

    @commands.command(name='featurelist', help='Show special features enabled for this server.')
    async def featurelist(self, ctx):
        features = ctx.guild.features
        if not features:
            return await ctx.info('This server has no special features enabled.')
        formatted = [f.replace('_', ' ').title() for f in features]
        embed = self.bot.embed_manager.generic(description='\n'.join([f'• {f}' for f in formatted]), title='✨ Server Features')
        await ctx.send(embed=embed)

    @commands.command(name='largestrole', help='Show the role with the most members.')
    async def largestrole(self, ctx):
        roles = [r for r in ctx.guild.roles if r.name != '@everyone' and len(r.members) > 0]
        if not roles:
            return await ctx.info('No roles with members found.')
        largest = max(roles, key=lambda r: len(r.members))
        await ctx.send(f'🎭 Largest role: {largest.mention} with **{len(largest.members)}** members.')

    @commands.command(name='newestrole', help='Show the most recently created role.')
    async def newestrole(self, ctx):
        roles = [r for r in ctx.guild.roles if r.name != '@everyone']
        if not roles:
            return await ctx.info('No roles found.')
        newest = max(roles, key=lambda r: r.created_at)
        await ctx.send(f'🆕 Newest role: {newest.mention} — created <t:{int(newest.created_at.timestamp())}:R>')

    @commands.command(name='oldestrole', help='Show the oldest role in this server.')
    async def oldestrole(self, ctx):
        roles = [r for r in ctx.guild.roles if r.name != '@everyone']
        if not roles:
            return await ctx.info('No roles found.')
        oldest = min(roles, key=lambda r: r.created_at)
        await ctx.send(f'🏛️ Oldest role: {oldest.mention} — created <t:{int(oldest.created_at.timestamp())}:R>')

    @commands.command(name='botcount', help='Count how many bots are in this server.')
    async def botcount(self, ctx):
        bots = [m for m in ctx.guild.members if m.bot]
        await ctx.send(f'🤖 This server has **{len(bots)}** bot(s) out of `{ctx.guild.member_count}` total members.')

    @commands.command(name='humancount', help='Count how many human members are in this server.')
    async def humancount(self, ctx):
        humans = [m for m in ctx.guild.members if not m.bot]
        await ctx.send(f'👤 This server has **{len(humans)}** human member(s) out of `{ctx.guild.member_count}` total.')

    @commands.command(name='onlinecount', help='Count how many members are currently online.')
    async def onlinecount(self, ctx):
        online = [m for m in ctx.guild.members if m.status != discord.Status.offline and not m.bot]
        await ctx.send(f'🟢 **{len(online)}** member(s) currently online.')

    @commands.command(name='mobilecount', help='Count how many members are on mobile.')
    async def mobilecount(self, ctx):
        mobile = [m for m in ctx.guild.members if m.is_on_mobile()]
        await ctx.send(f'📱 **{len(mobile)}** member(s) currently on mobile.')

    @commands.command(name='streamingcount', help='Count how many members are currently streaming.')
    async def streamingcount(self, ctx):
        streaming = [m for m in ctx.guild.members if any(isinstance(a, discord.Streaming) for a in m.activities)]
        await ctx.send(f'🔴 **{len(streaming)}** member(s) currently streaming.')

    @commands.command(name='customstatuscount', help='Count how many members have a custom status set.')
    async def customstatuscount(self, ctx):
        custom = [m for m in ctx.guild.members if any(isinstance(a, discord.CustomActivity) for a in m.activities)]
        await ctx.send(f'💬 **{len(custom)}** member(s) have a custom status set.')

    @commands.command(name='mfacount', help='Show this server\'s 2FA requirement for moderators.')
    async def mfacount(self, ctx):
        level = 'Required' if ctx.guild.mfa_level.value == 1 else 'Not Required'
        await ctx.send(f'🔐 2FA for Moderators: **{level}**')

    @commands.command(name='nitrocount', help='Count members with Discord Nitro (based on animated avatar/banner).')
    async def nitrocount(self, ctx):
        nitro_members = [m for m in ctx.guild.members if m.display_avatar.is_animated()]
        await ctx.send(f'💎 Approximately **{len(nitro_members)}** member(s) may have Nitro (animated avatar detected).')

    @commands.command(name='pendingcount', help='Count members still pending membership screening.')
    async def pendingcount(self, ctx):
        pending = [m for m in ctx.guild.members if m.pending]
        await ctx.send(f'⏳ **{len(pending)}** member(s) pending screening.')

    @commands.command(name='timeoutcount', help='Count currently timed-out members.')
    async def timeoutcount(self, ctx):
        timed_out = [m for m in ctx.guild.members if m.is_timed_out()]
        await ctx.send(f'🔇 **{len(timed_out)}** member(s) currently timed out.')

    @commands.command(name='avgaccountage', help='Show the average account age of members.')
    async def avgaccountage(self, ctx):
        humans = [m for m in ctx.guild.members if not m.bot]
        if not humans:
            return await ctx.info('No human members found.')
        now = datetime.datetime.now(datetime.timezone.utc)
        avg_days = sum((now - m.created_at).days for m in humans) / len(humans)
        avg_years = avg_days / 365.25
        await ctx.send(f'📊 Average account age: **{avg_years:.1f} years** (`{int(avg_days)}` days)')

    @commands.command(name='joindate', help='Show when a member joined this server.')
    async def joindate(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        if not member.joined_at:
            return await ctx.error('Could not determine join date.')
        await ctx.send(f'📅 {member.mention} joined <t:{int(member.joined_at.timestamp())}:F> (<t:{int(member.joined_at.timestamp())}:R>)')

async def setup(bot):
    await bot.add_cog(ServerStats2(bot))
