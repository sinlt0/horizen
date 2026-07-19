import discord
from discord.ext import commands

SYSTEMS = {
    'leveling':     ('leveling_config',    'XP and level-up system'),
    'autorole':     ('autorole_config',    'Auto-assign roles on join'),
    'greetings':    ('greetings_config',   'Welcome and goodbye messages'),
    'logging':      ('logging_config',     'Event logging'),
    'antinuke':     ('antinuke_config',    'AntiNuke protection'),
    'automod':      ('automod_config',     'AutoMod filters'),
    'verification': ('verification_config','CAPTCHA verification'),
    'tickets':      ('ticket_config',      'Support ticket system'),
    'starboard':    ('starboard_config',   'Starboard'),
    'suggestions':  ('suggestions_config', 'Suggestion submissions'),
    'booster':      ('booster_config',     'Nitro booster perks'),
    'voicemaster':  ('voicemaster_config', 'Voice master channels'),
    'reputation':   ('reputation_config',  'Trust and reputation'),
    'confession':   ('confession_config',  'Anonymous confessions'),
    'bumper':       ('bump_config',        'Disboard bump reminder'),
    'birthday':     ('birthday_config',    'Birthday announcements'),
    'counting':     ('counting_config',    'Counting channel'),
    'alerts':       ('social_alerts',      'Social media alerts'),
    'analytics':    ('server_analytics',   'Server analytics tracking'),
    'music':        ('music_config',       'Music system'),
}


def _is_enabled(config, system_key):
    if config is None:
        return False
    if system_key == 'greetings':
        return config.get('welcome_enabled', False) or config.get('goodbye_enabled', False)
    return config.get('enabled', False)


class Systems(commands.Cog):
    category = 'config'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager

    @commands.group(name='systems', aliases=['system', 'modules'], invoke_without_command=True, help='View and manage all bot systems for this server.')
    @commands.has_permissions(manage_guild=True)
    async def systems_group(self, ctx):
        await ctx.invoke(self.systems_list)

    @systems_group.command(name='list', aliases=['status'], help='Show enabled/disabled status of all systems.')
    @commands.has_permissions(manage_guild=True)
    async def systems_list(self, ctx):
        lines = []
        for key, (collection, description) in SYSTEMS.items():
            config = await self.db.find_one(collection, {'_id': ctx.guild.id})
            enabled = _is_enabled(config, key)
            icon = '🟢' if enabled else '🔴'
            lines.append(f'{icon} **{key}** — {description}')
        embed = self.bot.embed_manager.generic(
            description='\n'.join(lines),
            title=f'⚙️ System Status — {ctx.guild.name}'
        )
        embed.set_footer(text='Use "systems enable <name>" or "systems disable <name>" to toggle.')
        await ctx.send(embed=embed)

    @systems_group.command(name='enable', help='Enable a system. Usage: systems enable <name>')
    @commands.has_permissions(manage_guild=True)
    async def systems_enable(self, ctx, *, name: str):
        name = name.lower()
        if name not in SYSTEMS:
            return await ctx.error(f'Unknown system. Valid: {", ".join(f"`{k}`" for k in SYSTEMS)}')
        collection, description = SYSTEMS[name]
        if name == 'greetings':
            await self.db.update_one(collection, {'_id': ctx.guild.id}, {'welcome_enabled': True}, upsert=True)
        else:
            await self.db.update_one(collection, {'_id': ctx.guild.id}, {'enabled': True}, upsert=True)
        await ctx.success(f'{self.bot.e.success} **{name.capitalize()}** enabled. Configure it with `{name} setup`.')

    @systems_group.command(name='disable', help='Disable a system. Usage: systems disable <name>')
    @commands.has_permissions(manage_guild=True)
    async def systems_disable(self, ctx, *, name: str):
        name = name.lower()
        if name not in SYSTEMS:
            return await ctx.error(f'Unknown system. Valid: {", ".join(f"`{k}`" for k in SYSTEMS)}')
        collection, _ = SYSTEMS[name]
        if name == 'greetings':
            await self.db.update_one(collection, {'_id': ctx.guild.id}, {'welcome_enabled': False, 'goodbye_enabled': False}, upsert=True)
        else:
            await self.db.update_one(collection, {'_id': ctx.guild.id}, {'enabled': False}, upsert=True)
        await ctx.success(f'{self.bot.e.success} **{name.capitalize()}** disabled.')

    @systems_group.command(name='reset', help='Reset all systems to disabled for this server.')
    @commands.has_permissions(administrator=True)
    async def systems_reset(self, ctx):
        confirm_msg = await ctx.send(f'⚠️ This will **disable all systems** for **{ctx.guild.name}**. React ✅ to confirm or ❌ to cancel.')
        await confirm_msg.add_reaction('✅')
        await confirm_msg.add_reaction('❌')
        def check(r, u):
            return u == ctx.author and str(r.emoji) in ('✅', '❌') and r.message.id == confirm_msg.id
        try:
            reaction, _ = await self.bot.wait_for('reaction_add', timeout=30, check=check)
        except Exception:
            return await confirm_msg.edit(content='❌ Timed out.')
        if str(reaction.emoji) != '✅':
            return await confirm_msg.edit(content='❌ Cancelled.')
        for key, (collection, _) in SYSTEMS.items():
            if key == 'greetings':
                await self.db.update_one(collection, {'_id': ctx.guild.id}, {'welcome_enabled': False, 'goodbye_enabled': False}, upsert=True)
            else:
                await self.db.update_one(collection, {'_id': ctx.guild.id}, {'enabled': False}, upsert=True)
        await confirm_msg.edit(content=f'{self.bot.e.success} All systems disabled.')

    @systems_group.command(name='info', help='Show setup instructions for a system. Usage: systems info <name>')
    async def systems_info(self, ctx, *, name: str):
        name = name.lower()
        if name not in SYSTEMS:
            return await ctx.error(f'Unknown system `{name}`.')
        collection, description = SYSTEMS[name]
        config = await self.db.find_one(collection, {'_id': ctx.guild.id})
        enabled = _is_enabled(config, name)
        hints = {
            'leveling':    '`leveling enable` · `leveling channel #ch` · `leveling notify dm/channel/disabled`',
            'autorole':    '`autorole add @role` — roles assigned on member join',
            'greetings':   '`greetings setup` — configure welcome/goodbye channels and messages',
            'logging':     '`logging setup #channel` — configure event logging',
            'antinuke':    '`antinuke setup` — configure thresholds and punishments',
            'automod':     '`automod` — open the AutoMod dashboard',
            'verification':'`verification setup` — set channel, role, and CAPTCHA mode',
            'tickets':     '`tickets setup` — configure support ticket panels',
            'starboard':   '`starboard setup #channel` — set emoji and star threshold',
            'suggestions': '`suggestions setup #channel`',
            'booster':     '`booster setup` — configure Nitro booster perks',
            'voicemaster': '`voicemaster setup` — set the join-to-create channel',
            'reputation':  '`trust setup channel #ch` · `trust setup tierrole`',
            'confession':  '`confession setup #channel`',
            'bumper':      '`bumper setup #channel` — auto-remind when Disboard bump is ready',
            'birthday':    '`birthday setup #channel` — announce member birthdays',
            'counting':    '`counting setup #channel`',
            'alerts':      '`alerts` — open the social media alerts dashboard',
            'analytics':   'Auto-tracks messages, joins, commands — view with `analytics overview`',
            'music':       '`mplay <query>` to start — no setup required',
        }
        embed = self.bot.embed_manager.generic(
            description=(
                f'**Description:** {description}\n'
                f'**Status:** {"🟢 Enabled" if enabled else "🔴 Disabled"}\n\n'
                f'**How to set up:**\n{hints.get(name, "No setup required.")}'
            ),
            title=f'ℹ️ System: {name.capitalize()}'
        )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Systems(bot))
