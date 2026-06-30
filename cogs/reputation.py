import discord
from discord.ext import commands, tasks
import datetime
import asyncio
import math

TRUST_TIERS = [
    (0,    'Newcomer',    '⬜', discord.Color.light_grey()),
    (100,  'Member',      '🟦', discord.Color.blue()),
    (300,  'Trusted',     '🟩', discord.Color.green()),
    (600,  'Reliable',    '🟨', discord.Color.gold()),
    (1000, 'Veteran',     '🟧', discord.Color.orange()),
    (1500, 'Elite',       '🟥', discord.Color.red()),
    (2500, 'Legend',      '🌟', discord.Color.purple()),
]

POINT_REASONS = {
    'message_activity':    (+1,   'Active messaging (per 10 msgs)'),
    'invite_join':         (+15,  'Invited a member who stayed'),
    'boost':               (+50,  'Server boost'),
    'vouch':               (+20,  'Vouched by trusted member'),
    'days_in_server':      (+2,   'Account age milestone (per 30 days)'),
    'giveaway_win':        (+5,   'Won a giveaway'),
    'suggestion_accepted': (+10,  'Suggestion accepted'),
    'staff_grant':         (None, 'Staff manual grant'),
    'warn':                (-25,  'Received a warning'),
    'timeout':             (-40,  'Received a timeout'),
    'automod_hit':         (-10,  'AutoMod violation'),
    'ban_appeal':          (-100, 'Was banned (appeal restored)'),
    'staff_deduct':        (None, 'Staff manual deduction'),
    'left_rejoin':         (-15,  'Left and rejoined within 7 days'),
}

MAX_VOUCHES_PER_DAY = 3
VOUCH_COOLDOWN_HOURS = 24
MIN_TRUST_TO_VOUCH = 300


def get_tier(points):
    tier = TRUST_TIERS[0]
    for threshold, name, emoji, color in TRUST_TIERS:
        if points >= threshold:
            tier = (threshold, name, emoji, color)
    return tier


def get_next_tier(points):
    for threshold, name, emoji, color in TRUST_TIERS:
        if points < threshold:
            return (threshold, name, emoji, color)
    return None


def build_trust_bar(points):
    tiers = TRUST_TIERS
    current_idx = 0
    for i, (threshold, _, _, _) in enumerate(tiers):
        if points >= threshold:
            current_idx = i
    if current_idx >= len(tiers) - 1:
        return '█' * 20 + ' `MAX`'
    current_threshold = tiers[current_idx][0]
    next_threshold = tiers[current_idx + 1][0]
    pct = (points - current_threshold) / (next_threshold - current_threshold)
    filled = int(pct * 20)
    bar = '█' * filled + '░' * (20 - filled)
    return f'{bar} `{int(pct * 100)}%`'


class ReputationSystem(commands.Cog):
    category = 'utility'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager
        self._msg_counter = {}
        self._vouch_cooldowns = {}
        self._processed_joins = set()

    async def cog_load(self):
        self.decay_loop.start()
        self.milestone_check_loop.start()

    def cog_unload(self):
        self.decay_loop.cancel()
        self.milestone_check_loop.cancel()

    async def _get_profile(self, guild_id, user_id):
        key = f'{guild_id}:{user_id}'
        data = await self.db.find_one('reputation', {'_id': key})
        if not data:
            data = {
                '_id': key,
                'guild_id': guild_id,
                'user_id': user_id,
                'points': 0,
                'history': [],
                'vouched_by': [],
                'vouches_given_today': 0,
                'vouch_reset_at': 0,
                'milestones_reached': [],
                'msg_count': 0,
                'last_active': 0,
                'joined_at': int(datetime.datetime.utcnow().timestamp()),
            }
        return data

    async def _save_profile(self, data):
        await self.db.update_one('reputation', {'_id': data['_id']}, data, upsert=True)

    async def _add_points(self, guild_id, user_id, amount, reason, actor_id=None):
        data = await self._get_profile(guild_id, user_id)
        old_points = data['points']
        data['points'] = max(0, data['points'] + amount)

        entry = {
            'amount': amount,
            'reason': reason,
            'ts': int(datetime.datetime.utcnow().timestamp()),
        }
        if actor_id:
            entry['by'] = actor_id

        data['history'] = ([entry] + data['history'])[:50]
        await self._save_profile(data)

        old_tier = get_tier(old_points)
        new_tier = get_tier(data['points'])
        if new_tier[0] > old_tier[0]:
            await self._announce_tier_up(guild_id, user_id, new_tier, data['points'])

        return data['points']

    async def _announce_tier_up(self, guild_id, user_id, tier, points):
        config = await self.db.find_one('reputation_config', {'_id': guild_id})
        if not config:
            return
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return
        member = guild.get_member(user_id)
        if not member:
            return

        channel_id = config.get('announce_channel')
        if channel_id:
            channel = guild.get_channel(channel_id)
            if channel:
                _, name, emoji, color = tier
                embed = discord.Embed(
                    title=f'{emoji} Trust Tier Up!',
                    description=(
                        f'{member.mention} has reached **{name}** tier!\n'
                        f'Total Trust Points: `{points}`'
                    ),
                    color=color
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                await channel.send(embed=embed)

        role_rewards = config.get('tier_roles', {})
        tier_name = tier[1]
        role_id = role_rewards.get(tier_name)
        if role_id:
            role = guild.get_role(role_id)
            if role:
                try:
                    await member.add_roles(role, reason=f'Trust tier: {tier_name}')
                    for other_tier_name, other_role_id in role_rewards.items():
                        if other_tier_name != tier_name:
                            other_role = guild.get_role(other_role_id)
                            if other_role and other_role in member.roles:
                                await member.remove_roles(other_role)
                except Exception:
                    pass

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        config = await self.db.find_one('reputation_config', {'_id': message.guild.id})
        if not config or not config.get('enabled', True):
            return

        key = f'{message.guild.id}:{message.author.id}'
        self._msg_counter[key] = self._msg_counter.get(key, 0) + 1

        if self._msg_counter[key] >= 10:
            self._msg_counter[key] = 0
            await self._add_points(message.guild.id, message.author.id, 1, 'message_activity')

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.bot:
            return
        config = await self.db.find_one('reputation_config', {'_id': member.guild.id})
        if not config or not config.get('enabled', True):
            return

        invite_cog = self.bot.get_cog('InviteTracker')
        if not invite_cog:
            return

        invite_data = await self.db.find_one('joined_members_map', {'_id': f'{member.guild.id}:{member.id}'})
        if invite_data and invite_data.get('inviter_id'):
            inviter_id = invite_data['inviter_id']
            left_at = invite_data.get('left_at')
            if left_at:
                now = int(datetime.datetime.utcnow().timestamp())
                if now - left_at < 604800:
                    await self._add_points(member.guild.id, member.id, -15, 'left_rejoin')
            await self._add_points(member.guild.id, inviter_id, 15, 'invite_join')

    @commands.Cog.listener()
    async def on_member_boost(self, member):
        config = await self.db.find_one('reputation_config', {'_id': member.guild.id})
        if not config or not config.get('enabled', True):
            return
        await self._add_points(member.guild.id, member.id, 50, 'boost')

    @tasks.loop(hours=24)
    async def decay_loop(self):
        configs = await self.db.find('reputation_config', {})
        for config in configs:
            if not config.get('decay_enabled', False):
                continue
            guild_id = config['_id']
            decay_rate = config.get('decay_rate', 5)
            threshold = config.get('decay_threshold', 7)
            now = int(datetime.datetime.utcnow().timestamp())
            cutoff = now - (threshold * 86400)
            profiles = await self.db.find('reputation', {'guild_id': guild_id})
            for profile in profiles:
                if profile.get('last_active', 0) < cutoff and profile['points'] > 0:
                    new_points = max(0, profile['points'] - decay_rate)
                    profile['points'] = new_points
                    profile['history'] = ([{
                        'amount': -decay_rate,
                        'reason': f'inactivity_decay ({threshold}d)',
                        'ts': now
                    }] + profile.get('history', []))[:50]
                    await self._save_profile(profile)

    @decay_loop.before_loop
    async def before_decay(self):
        await self.bot.wait_until_ready()

    @tasks.loop(hours=1)
    async def milestone_check_loop(self):
        configs = await self.db.find('reputation_config', {})
        for config in configs:
            milestones = config.get('milestones', {})
            if not milestones:
                continue
            guild_id = config['_id']
            profiles = await self.db.find('reputation', {'guild_id': guild_id})
            for profile in profiles:
                for pts_str, reward in milestones.items():
                    pts = int(pts_str)
                    if profile['points'] >= pts and pts_str not in profile.get('milestones_reached', []):
                        profile.setdefault('milestones_reached', []).append(pts_str)
                        await self._save_profile(profile)
                        guild = self.bot.get_guild(guild_id)
                        if guild:
                            member = guild.get_member(profile['user_id'])
                            if member and reward.get('role_id'):
                                role = guild.get_role(reward['role_id'])
                                if role:
                                    try:
                                        await member.add_roles(role, reason=f'Trust milestone: {pts}')
                                    except Exception:
                                        pass

    @milestone_check_loop.before_loop
    async def before_milestone(self):
        await self.bot.wait_until_ready()

    @commands.group(name='trust', aliases=['rep', 'reputation'], invoke_without_command=True, help='Trust & Reputation system commands.')
    async def trust_group(self, ctx, member: discord.Member = None):
        await ctx.invoke(self.trust_profile, member=member or ctx.author)

    @trust_group.command(name='profile', aliases=['p2'], help='View a member\'s trust profile.')
    async def trust_profile(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        data = await self._get_profile(ctx.guild.id, member.id)
        points = data['points']
        _, tier_name, tier_emoji, tier_color = get_tier(points)
        next_tier = get_next_tier(points)
        bar = build_trust_bar(points)

        history = data.get('history', [])[:5]
        hist_lines = '\n'.join([
            f'`{("+" if h["amount"] > 0 else "")}{h["amount"]}` {h["reason"]} — <t:{h["ts"]}:R>'
            for h in history
        ]) or 'No history yet.'

        desc = (
            f'**Trust Points:** `{points}`\n'
            f'**Tier:** {tier_emoji} **{tier_name}**\n'
            f'**Progress:** {bar}\n'
        )
        if next_tier:
            needed = next_tier[0] - points
            desc += f'**Next Tier:** {next_tier[2]} {next_tier[1]} — `{needed}` pts needed\n'

        desc += f'\n**Vouches Received:** `{len(data.get("vouched_by", []))}`\n'
        desc += f'\n**Recent History:**\n{hist_lines}'

        embed = discord.Embed(
            title=f'{tier_emoji} {member.display_name}\'s Trust Profile',
            description=desc,
            color=tier_color
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f'{ctx.guild.name} Trust System')
        await ctx.send(embed=embed)

    @trust_group.command(name='leaderboard', aliases=['lb2', 'top2'], help='Show the trust leaderboard for this server.')
    async def trust_leaderboard(self, ctx, page: int = 1):
        profiles = await self.db.find('reputation', {'guild_id': ctx.guild.id})
        profiles = [p for p in profiles if p['points'] > 0]
        profiles.sort(key=lambda p: p['points'], reverse=True)

        per_page = 10
        total_pages = max(1, math.ceil(len(profiles) / per_page))
        page = max(1, min(page, total_pages))
        start = (page - 1) * per_page
        page_profiles = profiles[start:start + per_page]

        lines = []
        medals = {1: '🥇', 2: '🥈', 3: '🥉'}
        for i, p in enumerate(page_profiles, start + 1):
            member = ctx.guild.get_member(p['user_id'])
            name = member.display_name if member else f'<@{p["user_id"]}>'
            _, tier_name, emoji, _ = get_tier(p['points'])
            medal = medals.get(i, f'`{i}.`')
            lines.append(f'{medal} {name} — {emoji} **{tier_name}** `{p["points"]} pts`')

        embed = self.bot.embed_manager.generic(
            description='\n'.join(lines) if lines else 'No trust data yet.',
            title=f'🏆 Trust Leaderboard — Page {page}/{total_pages}'
        )
        embed.set_footer(text=f'{len(profiles)} members ranked')
        await ctx.send(embed=embed)

    @trust_group.command(name='vouch', help='Vouch for a member to increase their trust.')
    async def trust_vouch(self, ctx, member: discord.Member, *, reason: str = None):
        if member == ctx.author:
            return await ctx.error('You cannot vouch for yourself.')
        if member.bot:
            return await ctx.error('You cannot vouch for bots.')

        voucher_data = await self._get_profile(ctx.guild.id, ctx.author.id)
        if voucher_data['points'] < MIN_TRUST_TO_VOUCH:
            return await ctx.error(f'You need `{MIN_TRUST_TO_VOUCH}` trust points to vouch for others. You have `{voucher_data["points"]}`.')

        now = int(datetime.datetime.utcnow().timestamp())
        if now < voucher_data.get('vouch_reset_at', 0):
            remaining = voucher_data['vouch_reset_at'] - now
            hrs = remaining // 3600
            return await ctx.error(f'Vouch limit reached. Resets in `{hrs}h`.')

        if now >= voucher_data.get('vouch_reset_at', 0):
            voucher_data['vouches_given_today'] = 0
            voucher_data['vouch_reset_at'] = now + (VOUCH_COOLDOWN_HOURS * 3600)

        if voucher_data['vouches_given_today'] >= MAX_VOUCHES_PER_DAY:
            return await ctx.error(f'You\'ve used all `{MAX_VOUCHES_PER_DAY}` daily vouches.')

        target_data = await self._get_profile(ctx.guild.id, member.id)
        if ctx.author.id in target_data.get('vouched_by', []):
            return await ctx.error(f'You\'ve already vouched for {member.mention}.')

        target_data.setdefault('vouched_by', []).append(ctx.author.id)
        await self._save_profile(target_data)

        voucher_data['vouches_given_today'] += 1
        await self._save_profile(voucher_data)

        await self._add_points(ctx.guild.id, member.id, 20, f'vouch by {ctx.author}', ctx.author.id)
        await ctx.success(
            f'{self.bot.e.success} Vouched for {member.mention}! They received `+20` trust points.\n'
            f'You have `{MAX_VOUCHES_PER_DAY - voucher_data["vouches_given_today"]}` vouches remaining today.'
        )

    @trust_group.command(name='give', help='Manually grant trust points to a member.')
    @commands.has_permissions(manage_guild=True)
    async def trust_give(self, ctx, member: discord.Member, amount: int, *, reason: str = 'Staff grant'):
        if amount == 0:
            return await ctx.error('Amount cannot be zero.')
        new_total = await self._add_points(ctx.guild.id, member.id, amount, f'staff_grant: {reason}', ctx.author.id)
        sign = '+' if amount > 0 else ''
        await ctx.success(f'{self.bot.e.success} {sign}{amount} trust points → {member.mention}. New total: `{new_total}`.')

    @trust_group.command(name='deduct', help='Manually deduct trust points from a member.')
    @commands.has_permissions(manage_guild=True)
    async def trust_deduct(self, ctx, member: discord.Member, amount: int, *, reason: str = 'Staff deduction'):
        if amount <= 0:
            return await ctx.error('Amount must be positive.')
        new_total = await self._add_points(ctx.guild.id, member.id, -amount, f'staff_deduct: {reason}', ctx.author.id)
        await ctx.success(f'{self.bot.e.success} -{amount} trust points from {member.mention}. New total: `{new_total}`.')

    @trust_group.command(name='reset', help='Reset a member\'s trust profile to zero.')
    @commands.has_permissions(manage_guild=True)
    async def trust_reset(self, ctx, member: discord.Member):
        key = f'{ctx.guild.id}:{member.id}'
        await self.db.delete_one('reputation', {'_id': key})
        await ctx.success(f'{self.bot.e.success} Trust profile reset for {member.mention}.')

    @trust_group.command(name='history', aliases=['log2'], help='View full trust history for a member.')
    @commands.has_permissions(manage_messages=True)
    async def trust_history(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        data = await self._get_profile(ctx.guild.id, member.id)
        history = data.get('history', [])
        if not history:
            return await ctx.info(f'No trust history for {member.mention}.')
        lines = [
            f'`{("+" if h["amount"] > 0 else "")}{h["amount"]}` **{h["reason"]}** <t:{h["ts"]}:R>'
            + (f' by <@{h["by"]}>' if h.get('by') else '')
            for h in history[:20]
        ]
        embed = self.bot.embed_manager.generic(
            description='\n'.join(lines),
            title=f'📋 Trust History — {member.display_name}'
        )
        await ctx.send(embed=embed)

    @trust_group.command(name='check', help='Quick trust check — show points and tier for a member.')
    async def trust_check(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        data = await self._get_profile(ctx.guild.id, member.id)
        points = data['points']
        _, tier_name, emoji, color = get_tier(points)
        await ctx.send(f'{emoji} **{member.display_name}** — {tier_name} · `{points} pts`')

    @trust_group.command(name='tiers', help='Show all available trust tiers and their point requirements.')
    async def trust_tiers(self, ctx):
        lines = []
        for threshold, name, emoji, color in TRUST_TIERS:
            lines.append(f'{emoji} **{name}** — `{threshold}+ pts`')
        embed = self.bot.embed_manager.generic(
            description='\n'.join(lines),
            title='🏅 Trust Tiers'
        )
        await ctx.send(embed=embed)

    @trust_group.command(name='compare', help='Compare trust scores between two members.')
    async def trust_compare(self, ctx, member1: discord.Member, member2: discord.Member):
        d1 = await self._get_profile(ctx.guild.id, member1.id)
        d2 = await self._get_profile(ctx.guild.id, member2.id)
        p1, p2 = d1['points'], d2['points']
        _, t1, e1, _ = get_tier(p1)
        _, t2, e2, _ = get_tier(p2)
        winner = member1 if p1 >= p2 else member2
        embed = self.bot.embed_manager.generic(
            description=(
                f'{e1} **{member1.display_name}** — {t1} · `{p1} pts`\n'
                f'{e2} **{member2.display_name}** — {t2} · `{p2} pts`\n\n'
                f'🏆 **{winner.display_name}** leads by `{abs(p1 - p2)} pts`'
            ),
            title='⚖️ Trust Comparison'
        )
        await ctx.send(embed=embed)

    @trust_group.command(name='report', help='Generate a full moderation trust report for a member.')
    @commands.has_permissions(manage_messages=True)
    async def trust_report(self, ctx, member: discord.Member):
        data = await self._get_profile(ctx.guild.id, member.id)
        points = data['points']
        _, tier_name, emoji, color = get_tier(points)

        warns = sum(1 for h in data.get('history', []) if 'warn' in h.get('reason', '').lower())
        timeouts = sum(1 for h in data.get('history', []) if 'timeout' in h.get('reason', '').lower())
        automod = sum(1 for h in data.get('history', []) if 'automod' in h.get('reason', '').lower())
        boosts = sum(1 for h in data.get('history', []) if 'boost' in h.get('reason', '').lower())
        invites = sum(1 for h in data.get('history', []) if 'invite' in h.get('reason', '').lower())
        vouches = len(data.get('vouched_by', []))

        risk = 'Low 🟢'
        if points < 100 or warns >= 3 or timeouts >= 2:
            risk = 'Medium 🟡'
        if points < 0 or warns >= 5 or timeouts >= 3 or automod >= 10:
            risk = 'High 🔴'

        joined_at = member.joined_at
        days_in_server = (datetime.datetime.utcnow() - joined_at.replace(tzinfo=None)).days if joined_at else 0

        embed = discord.Embed(
            title=f'🔍 Trust Report — {member}',
            color=color,
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name='Trust Score', value=f'{emoji} **{tier_name}** · `{points} pts`', inline=True)
        embed.add_field(name='Risk Level', value=risk, inline=True)
        embed.add_field(name='Days in Server', value=f'`{days_in_server}d`', inline=True)
        embed.add_field(name='Violations', value=f'Warns: `{warns}` | Timeouts: `{timeouts}` | AutoMod: `{automod}`', inline=False)
        embed.add_field(name='Positive', value=f'Vouches: `{vouches}` | Boosts: `{boosts}` | Invite Joins: `{invites}`', inline=False)
        embed.add_field(name='Account Created', value=f'<t:{int(member.created_at.timestamp())}:R>', inline=True)
        embed.add_field(name='Joined Server', value=f'<t:{int(joined_at.timestamp())}:R>' if joined_at else 'Unknown', inline=True)
        embed.set_footer(text=f'Report generated by {ctx.author}')
        await ctx.send(embed=embed)

    @trust_group.command(name='points', help='Show what actions earn or cost trust points.')
    async def trust_points(self, ctx):
        gains = '\n'.join([
            f'`+{v}` {d}' for k, (v, d) in POINT_REASONS.items()
            if v and v > 0
        ])
        losses = '\n'.join([
            f'`{v}` {d}' for k, (v, d) in POINT_REASONS.items()
            if v and v < 0
        ])
        embed = self.bot.embed_manager.generic(
            description=f'**Gains:**\n{gains}\n\n**Losses:**\n{losses}',
            title='📊 Trust Point Values'
        )
        embed.set_footer(text='Staff can also manually grant or deduct points.')
        await ctx.send(embed=embed)

    @trust_group.group(name='setup', invoke_without_command=True, help='Trust system configuration.')
    @commands.has_permissions(manage_guild=True)
    async def trust_setup(self, ctx):
        await ctx.send_help(ctx.command)

    @trust_setup.command(name='enable', help='Enable the trust system in this server.')
    @commands.has_permissions(manage_guild=True)
    async def trust_enable(self, ctx):
        await self.db.update_one('reputation_config', {'_id': ctx.guild.id}, {'enabled': True}, upsert=True)
        await ctx.success(f'{self.bot.e.success} Trust system **enabled**.')

    @trust_setup.command(name='disable', help='Disable the trust system in this server.')
    @commands.has_permissions(manage_guild=True)
    async def trust_disable(self, ctx):
        await self.db.update_one('reputation_config', {'_id': ctx.guild.id}, {'enabled': False}, upsert=True)
        await ctx.success(f'{self.bot.e.success} Trust system **disabled**.')

    @trust_setup.command(name='channel', help='Set the channel for trust tier-up announcements.')
    @commands.has_permissions(manage_guild=True)
    async def trust_channel(self, ctx, channel: discord.TextChannel):
        await self.db.update_one('reputation_config', {'_id': ctx.guild.id}, {'announce_channel': channel.id}, upsert=True)
        await ctx.success(f'{self.bot.e.success} Tier-up announcements → {channel.mention}.')

    @trust_setup.command(name='tierrole', help='Assign a role reward to a trust tier. Usage: trust setup tierrole <TierName> @Role')
    @commands.has_permissions(manage_guild=True)
    async def trust_tierrole(self, ctx, tier_name: str, role: discord.Role):
        valid_tiers = [t[1] for t in TRUST_TIERS]
        tier_name = tier_name.capitalize()
        if tier_name not in valid_tiers:
            return await ctx.error(f'Invalid tier. Choose: `{", ".join(valid_tiers)}`')
        config = await self.db.find_one('reputation_config', {'_id': ctx.guild.id}) or {}
        config.setdefault('tier_roles', {})[tier_name] = role.id
        await self.db.update_one('reputation_config', {'_id': ctx.guild.id}, config, upsert=True)
        await ctx.success(f'{self.bot.e.success} **{tier_name}** tier → {role.mention}.')

    @trust_setup.command(name='milestone', help='Set a trust milestone reward. Usage: trust setup milestone <points> @Role')
    @commands.has_permissions(manage_guild=True)
    async def trust_milestone(self, ctx, points: int, role: discord.Role):
        if points < 1:
            return await ctx.error('Points must be positive.')
        config = await self.db.find_one('reputation_config', {'_id': ctx.guild.id}) or {}
        config.setdefault('milestones', {})[str(points)] = {'role_id': role.id}
        await self.db.update_one('reputation_config', {'_id': ctx.guild.id}, config, upsert=True)
        await ctx.success(f'{self.bot.e.success} At `{points}` trust pts → {role.mention}.')

    @trust_setup.command(name='decay', help='Enable point decay for inactive members. Usage: trust setup decay <rate> <threshold_days>')
    @commands.has_permissions(manage_guild=True)
    async def trust_decay(self, ctx, rate: int = 5, threshold_days: int = 7):
        if rate < 1 or threshold_days < 1:
            return await ctx.error('Rate and threshold must be positive.')
        await self.db.update_one('reputation_config', {'_id': ctx.guild.id}, {
            'decay_enabled': True,
            'decay_rate': rate,
            'decay_threshold': threshold_days
        }, upsert=True)
        await ctx.success(f'{self.bot.e.success} Decay enabled: `-{rate} pts` per day after `{threshold_days}` days inactivity.')

    @trust_setup.command(name='nodecay', help='Disable point decay.')
    @commands.has_permissions(manage_guild=True)
    async def trust_nodecay(self, ctx):
        await self.db.update_one('reputation_config', {'_id': ctx.guild.id}, {'decay_enabled': False}, upsert=True)
        await ctx.success(f'{self.bot.e.success} Point decay **disabled**.')

    @trust_setup.command(name='config', help='View the current trust system configuration.')
    @commands.has_permissions(manage_guild=True)
    async def trust_config(self, ctx):
        config = await self.db.find_one('reputation_config', {'_id': ctx.guild.id})
        if not config:
            return await ctx.info('Trust system not configured. Use `trust setup enable` to start.')

        tier_roles = config.get('tier_roles', {})
        tier_role_str = '\n'.join([f'**{t}** → <@&{rid}>' for t, rid in tier_roles.items()]) or 'None'

        milestones = config.get('milestones', {})
        milestone_str = '\n'.join([f'`{pts}` pts → <@&{v["role_id"]}>' for pts, v in milestones.items()]) or 'None'

        status = "Enabled" if config.get("enabled", True) else "Disabled"
        announce = f"<#{config.get('announce_channel')}>" if config.get("announce_channel") else "Not set"
        decay_info = ""
        if config.get("decay_enabled"):
            decay_info = f" · `-{config.get('decay_rate', 5)} pts` after `{config.get('decay_threshold', 7)}d` inactivity"
        decay_status = f"`{'Enabled' if config.get('decay_enabled') else 'Disabled'}`{decay_info}"
        embed = self.bot.embed_manager.generic(
            description=(
                f"**Status:** `{status}`\n"
                f"**Announce Channel:** {announce}\n"
                f"**Decay:** {decay_status}\n\n"
                f"**Tier Roles:**\n{tier_role_str}\n\n"
                f"**Milestones:**\n{milestone_str}"
            ),
            title="⚙️ Trust System Configuration"
        )
        await ctx.send(embed=embed)

    def award_points_external(self, guild_id, user_id, reason_key, custom_amount=None):
        if reason_key not in POINT_REASONS:
            return
        amount = custom_amount if custom_amount is not None else POINT_REASONS[reason_key][0]
        if amount is None:
            return
        self.bot.loop.create_task(
            self._add_points(guild_id, user_id, amount, reason_key)
        )

async def setup(bot):
    await bot.add_cog(ReputationSystem(bot))
