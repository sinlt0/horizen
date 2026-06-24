import discord
from discord.ext import commands
import asyncio

class SetupWizardView(discord.ui.View):
    def __init__(self, bot, ctx):
        super().__init__(timeout=600)
        self.bot = bot
        self.ctx = ctx
        self.owner = ctx.author

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.owner:
            await interaction.response.send_message("This setup is restricted to the initiator.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="🛡️ Security", style=discord.ButtonStyle.primary)
    async def security_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Launching Security Wizard...", ephemeral=True)
        await self.ctx.invoke(self.bot.get_command('security setup'))

    @discord.ui.button(label="📊 Statistics", style=discord.ButtonStyle.primary)
    async def stats_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Creating Statistics Hub...", ephemeral=True)
        await self.ctx.invoke(self.bot.get_command('stats add'), s_type="members")
        await self.ctx.invoke(self.bot.get_command('stats add'), s_type="online")
        await self.ctx.invoke(self.bot.get_command('stats add'), s_type="boosts")

    @discord.ui.button(label="📡 Social Hub", style=discord.ButtonStyle.primary)
    async def alerts_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.ctx.invoke(self.bot.get_command('alerts'))
        await interaction.response.send_message("Social Hub dashboard opened.", ephemeral=True)

    @discord.ui.button(label="📝 Logging", style=discord.ButtonStyle.secondary)
    async def logging_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Please use `!logging config` to set up your webhook-based audit logs.", ephemeral=True)

    @discord.ui.button(label="✅ Finish Setup", style=discord.ButtonStyle.success)
    async def finish(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = self.bot.embed_manager.success("Your server has been successfully configured with Horizen's core systems.", title="Setup Complete")
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

class SetupHub(commands.Cog):
    category = 'config'

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setup", help="Launch the high-end Master Setup Wizard to configure your server.")
    @commands.has_permissions(administrator=True)
    async def master_setup(self, ctx):
        embed = self.bot.embed_manager.generic(
            title="Horizen Master Setup Hub",
            description=(
                "Welcome to the professional onboarding wizard. Select a module below to begin high-speed configuration.\n\n"
                "**🛡️ Security**: Configure AntiNuke and AutoMod tiers.\n"
                "**📊 Statistics**: Automatically generate sidebar counter channels.\n"
                "**📡 Social Hub**: Manage your automated notification feeds.\n"
                "**📝 Logging**: Link your server's audit logs to Discord webhooks."
            )
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        await ctx.send(embed=embed, view=SetupWizardView(self.bot, ctx))

async def setup(bot):
    await bot.add_cog(SetupHub(bot))
