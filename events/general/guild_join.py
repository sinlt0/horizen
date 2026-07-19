import discord
from discord.ext import commands

DISABLED_CONFIGS = {
    'leveling_config':     {'enabled': False, 'notify_type': 'channel', 'xp_min': 15, 'xp_max': 25, 'cooldown': 60},
    'automod_config':      {'enabled': False},
    'autorole_config':     {'enabled': False, 'roles': [], 'bot_roles': []},
    'logging_config':      {'enabled': False, 'events': {}},
    'antinuke_config':     {'enabled': False},
    'reputation_config':   {'enabled': False, 'decay_enabled': False},
    'confession_config':   {'enabled': False, 'count': 0},
    'bump_config':         {'enabled': False},
    'counting_config':     {'enabled': False, 'count': 0, 'record': 0},
    'suggestions_config':  {'enabled': False},
    'starboard_config':    {'enabled': False},
    'social_alerts':       {'enabled': False},
    'verification_config': {'enabled': False},
    'greetings_config':    {'welcome_enabled': False, 'goodbye_enabled': False},
    'ticket_config':       {'enabled': False},
    'booster_config':      {'enabled': False},
    'voicemaster_config':  {'enabled': False},
    'server_analytics':    {'enabled': False, 'messages': {}, 'commands': {}, 'joins': {}, 'leaves': {}},
    'music_config':        {'enabled': False},
    'birthday_config':     {'enabled': False},
    'custom_commands':     {'enabled': False, 'commands': {}, 'groups': {}},
    'reaction_roles':      {'enabled': False, 'panels': {}},
}


class GuildJoin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        await self.db.assign_guild(guild.id)
        print(f'Bot joined guild {guild.name} ({guild.id}) — initializing disabled configs.')

        for collection, defaults in DISABLED_CONFIGS.items():
            existing = await self.db.find_one(collection, {'_id': guild.id})
            if not existing:
                doc = {'_id': guild.id, **defaults}
                await self.db.update_one(collection, {'_id': guild.id}, doc, upsert=True)

        owner = guild.owner
        if owner:
            try:
                embed = discord.Embed(
                    title=f'👋 Thanks for adding Horizen to {guild.name}!',
                    description=(
                        '**All systems are disabled by default.**\n'
                        'Enable only what you need using setup commands.\n\n'
                        '**Quick Setup:**\n'
                        '`setup` — All-in-one server wizard\n'
                        '`systems list` — View all system statuses\n'
                        '`systems enable <name>` — Enable a system\n\n'
                        '**Key Systems:**\n'
                        '`leveling enable` · `automod setup` · `logging setup #ch`\n'
                        '`antinuke setup` · `trust setup enable` · `greetings setup`\n'
                        '`tickets setup` · `verification setup` · `birthday setup #ch`\n\n'
                        'Use `help` to see all 875+ commands.'
                    ),
                    color=discord.Color.blurple()
                )
                embed.set_thumbnail(url=self.bot.user.display_avatar.url)
                embed.set_footer(text='Horizen Systems • All systems opt-in by default')
                await owner.send(embed=embed)
            except Exception:
                pass

        print(f'Guild {guild.name} ({guild.id}) initialized with all systems disabled.')


async def setup(bot):
    await bot.add_cog(GuildJoin(bot))
