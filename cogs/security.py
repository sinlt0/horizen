import discord
from discord.ext import commands
import asyncio

class SecurityWizard(discord.ui.View):
    def __init__(self, bot, author):
        super().__init__(timeout=300)
        self.bot = bot
        self.author = author

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.author:
            await interaction.response.send_message("This wizard is not for you.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label='Low Protection', style=discord.ButtonStyle.secondary)
    async def low_tier(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.apply_tier(interaction, 'low')

    @discord.ui.button(label='Standard Protection', style=discord.ButtonStyle.primary)
    async def std_tier(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.apply_tier(interaction, 'standard')

    @discord.ui.button(label='High Protection', style=discord.ButtonStyle.success)
    async def high_tier(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.apply_tier(interaction, 'high')

    @discord.ui.button(label='Nuclear Protection', style=discord.ButtonStyle.danger)
    async def nuke_tier(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.apply_tier(interaction, 'nuclear')

    async def apply_tier(self, interaction, tier):
        settings = {
            'low': {
                'automod': {'spam_enabled': True, 'invites_enabled': True, 'links_enabled': False},
                'antinuke': {'enabled': True, 'punishment': 'quarantine', 'limits': 5}
            },
            'standard': {
                'automod': {'spam_enabled': True, 'invites_enabled': True, 'links_enabled': True, 'badwords_enabled': True, 'heat_enabled': True},
                'antinuke': {'enabled': True, 'punishment': 'quarantine', 'limits': 3}
            },
            'high': {
                'automod': {'spam_enabled': True, 'invites_enabled': True, 'links_enabled': True, 'badwords_enabled': True, 'heat_enabled': True, 'zalgo_enabled': True, 'caps_enabled': True},
                'antinuke': {'enabled': True, 'punishment': 'ban', 'limits': 2, 'vanity_protection': True}
            },
            'nuclear': {
                'automod': {'spam_enabled': True, 'invites_enabled': True, 'links_enabled': True, 'badwords_enabled': True, 'heat_enabled': True, 'zalgo_enabled': True, 'caps_enabled': True, 'images_enabled': True, 'images_limit': 1},
                'antinuke': {'enabled': True, 'punishment': 'ban', 'limits': 1, 'vanity_protection': True, 'panic_mode': False}
            }
        }
        
        data = settings[tier]
        guild_id = interaction.guild.id
        
        am_config = data['automod']
        await self.bot.db_manager.update_one('automod_config', {'_id': guild_id}, am_config, upsert=True)
        
        an_data = data['antinuke']
        an_config = {
            'antinuke_enabled': an_data['enabled'],
            'antinuke_punishment': an_data['punishment'],
            'vanity_protection': an_data.get('vanity_protection', False)
        }
        limit = an_data['limits']
        actions = ['mass_ban', 'mass_kick', 'mass_role_delete', 'mass_role_create', 'mass_channel_delete', 'mass_channel_create', 'mass_webhook_update', 'bot_add', 'mass_emoji_delete', 'dangerous_perms']
        for action in actions:
            an_config[f'antinuke_limit_{action}'] = limit
            
        await self.bot.db_manager.update_one('automod_config', {'_id': guild_id}, an_config, upsert=True)
        
        await interaction.response.send_message(f"✅ **{tier.capitalize()} Security Tier** has been applied successfully!", ephemeral=True)
        self.stop()

class Security(commands.Cog):
    category = 'config'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager

    @commands.group(name='security', aliases=['sec'], invoke_without_command=True, help='Unified security dashboard and configuration.')
    @commands.has_permissions(administrator=True)
    async def security_group(self, ctx):
        config = await self.db.find_one('automod_config', {'_id': ctx.guild.id})
        if not config: return await ctx.info("Security is not configured. Use `!security setup` to begin.")
        
        am_keys = ['links', 'invites', 'spam', 'badwords', 'heat']
        an_status = '✅' if config.get('antinuke_enabled') else '❌'
        
        desc = f"**Anti-Nuke:** {an_status}\n"
        desc += f"**Punishment:** {config.get('antinuke_punishment', 'quarantine').capitalize()}\n\n"
        desc += "**Active AutoMod Filters:**\n"
        for k in am_keys:
            s = '✅' if config.get(f'{k}_enabled') else '❌'
            desc += f"{s} {k.capitalize()}\n"
            
        await ctx.embed(desc, title="Horizen Security Dashboard")

    @security_group.command(name='setup', help='Start the interactive security configuration wizard.')
    @commands.has_permissions(administrator=True)
    async def security_setup(self, ctx):
        embed = self.bot.embed_manager.generic(
            title="Security Setup Wizard",
            description=(
                "Please select a security tier for your server.\n\n"
                "**Low**: Minimal filtering, recommended for small private servers.\n"
                "**Standard**: Balanced protection, suitable for most communities.\n"
                "**High**: Aggressive protection, recommended for large public servers.\n"
                "**Nuclear**: Extreme lockdown, blocks almost all automated activity."
            )
        )
        await ctx.send(embed=embed, view=SecurityWizard(self.bot, ctx.author))

    @security_group.command(name='tune', help='Granularly tune any security setting.')
    @commands.has_permissions(administrator=True)
    async def security_tune(self, ctx, module: str, setting: str, value: str):
        module = module.lower()
        setting = setting.lower()
        
        if module == 'antinuke':
            if setting == 'limit':
                return await ctx.invoke(self.bot.get_command('antinuke limit'), action='ban', limit=int(value))
        
        await ctx.success(f"Security setting **{setting}** in module **{module}** updated.")

    @commands.command(name="setprefix", aliases=["prefix", "prefixset"], help="Sets a custom prefix for the server.")
    @commands.has_permissions(administrator=True)
    async def setprefix(self, ctx, prefix: str):
        if len(prefix) > 5:
            return await ctx.error("Prefix must be less than 5 characters.")
        
        await self.bot.prefix_manager.set_prefix(ctx.guild.id, prefix)
        await ctx.success(f"Server prefix has been updated to: `{prefix}`")

    @commands.command(name="prefixinfo", help="Shows the current server prefix.")
    async def prefixinfo(self, ctx):
        prefix = await self.bot.prefix_manager.get_prefix(ctx.guild.id)
        await ctx.info(f"The current prefix for this server is: `{prefix}`")

    @commands.command(name="toggleprefix", aliases=["tprefix"], help="Enable or disable the use of guild-specific prefixes.")
    @commands.has_permissions(administrator=True)
    async def toggle_prefix(self, ctx, status: bool):
        await self.bot.prefix_manager.toggle_prefix(ctx.guild.id, status)
        await ctx.success(f"Guild-specific prefixing has been **{'enabled' if status else 'disabled'}**.")

    @commands.command(name="toggle", help="Enable or disable specific bot modules.")
    @commands.has_permissions(administrator=True)
    async def toggle_module(self, ctx, module: str = None):
        if not module:
            return await ctx.info("Available modules: `leveling`, `automod`, `antinuke` (use `!leveling toggle`, etc. for specific settings)")
        
        module = module.lower()
        if module == 'leveling':
            cog = self.bot.get_cog('Leveling')
            if cog: await ctx.invoke(self.bot.get_command('leveling toggle'))
        elif module == 'automod':
            await ctx.invoke(self.bot.get_command('automod toggle'))
        else:
            await ctx.error(f"Module `{module}` does not support direct toggling via this shortcut.")

async def setup(bot):
    await bot.add_cog(Security(bot))
