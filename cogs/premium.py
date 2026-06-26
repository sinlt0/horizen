import discord
from discord.ext import commands
from utils.premium_manager import PremiumManager
import time
from datetime import datetime

class PremiumDurationSelect(discord.ui.Select):
    def __init__(self, premium_manager, target_id=None, mode="key"):
        options = [
            discord.SelectOption(label="7 Days", value="7d", description="Premium for 1 week"),
            discord.SelectOption(label="2 Weeks", value="2week", description="Premium for 2 weeks"),
            discord.SelectOption(label="1 Month", value="1month", description="Premium for 30 days"),
            discord.SelectOption(label="1 Year", value="1y", description="Premium for 365 days"),
            discord.SelectOption(label="2 Years", value="2y", description="Premium for 730 days"),
            discord.SelectOption(label="Lifetime", value="lifetime", description="Permanent Premium status"),
        ]
        super().__init__(placeholder="Select duration...", options=options)
        self.pm = premium_manager
        self.target_id = target_id # Guild ID for direct add
        self.mode = mode

    async def callback(self, interaction: discord.Interaction):
        try:
            if not await interaction.client.is_owner(interaction.user) and not interaction.client.dev_manager.is_dev(interaction.user.id, interaction.client):
                return await interaction.response.send_message("You are not authorized.", ephemeral=True)

            duration_key = self.values[0]
            
            if self.mode == "key":
                key = await self.pm.generate_key(duration_key)
                embed = interaction.client.embed_manager.success(
                    f"Generated **{duration_key}** premium key:\n`{key}`",
                    title="Key Generated"
                )
                await interaction.response.edit_message(embed=embed, view=None)
            else:
                expiry = await self.pm.add_premium(self.target_id, duration_key)
                expiry_str = datetime.fromtimestamp(expiry).strftime('%Y-%m-%d %H:%M:%S') if expiry else "Lifetime"
                embed = interaction.client.embed_manager.success(
                    f"Added **{duration_key}** premium to Guild ID: `{self.target_id}`\nExpires: `{expiry_str}`",
                    title="Premium Added"
                )
                await interaction.response.edit_message(embed=embed, view=None)
        except Exception as e:
            print(f"Error in premium dropdown: {e}")
            import traceback
            traceback.print_exc()
            if not interaction.response.is_done():
                await interaction.response.send_message("An error occurred.", ephemeral=True)

class PremiumView(discord.ui.View):
    def __init__(self, premium_manager, target_id=None, mode="key"):
        super().__init__(timeout=60)
        self.add_item(PremiumDurationSelect(premium_manager, target_id, mode))

class PremiumCog(commands.Cog):
    category = "premium"

    def __init__(self, bot):
        self.bot = bot
        self.pm: PremiumManager = bot.premium_manager

    def is_dev_check():
        async def predicate(ctx):
            return await ctx.bot.is_owner(ctx.author) or ctx.bot.dev_manager.is_dev(ctx.author.id, ctx.bot)
        return commands.check(predicate)

    @commands.group(name="premium", invoke_without_command=True, help="View premium status for this guild.")
    async def premium_group(self, ctx):
        is_prem, expiry = await self.pm.get_premium_status(ctx.guild.id)
        if is_prem:
            expiry_str = datetime.fromtimestamp(expiry).strftime('%Y-%m-%d %H:%M:%S') if expiry else "Lifetime"
            await ctx.info(f"This guild has **Premium** status!\nExpires: `{expiry_str}`", title="Premium Status")
        else:
            await ctx.info("This guild does not have Premium status.", title="Premium Status")

    @premium_group.command(name="generate", help="Generate a premium key (Devs Only).")
    @is_dev_check()
    async def premium_generate(self, ctx):
        embed = ctx.bot.embed_manager.generic(
            "Select the duration for the new premium key:",
            title="Generate Premium Key"
        )
        await ctx.send(embed=embed, view=PremiumView(self.pm, mode="key"))

    @premium_group.command(name="add", help="Directly add premium to a guild (Devs Only).")
    @is_dev_check()
    async def premium_add(self, ctx, guild_id: int):
        embed = ctx.bot.embed_manager.generic(
            f"Select the duration to give premium to Guild ID: `{guild_id}`",
            title="Add Direct Premium"
        )
        await ctx.send(embed=embed, view=PremiumView(self.pm, target_id=guild_id, mode="add"))

    @premium_group.command(name="claim", help="Claim a premium key for this guild.")
    @commands.has_permissions(manage_guild=True)
    async def premium_claim(self, ctx, key: str):
        success, result = await self.pm.claim_key(ctx.guild.id, key)
        if success:
            expiry_str = datetime.fromtimestamp(result).strftime('%Y-%m-%d %H:%M:%S') if result else "Lifetime"
            await ctx.success(f"Successfully claimed premium!\nExpires: `{expiry_str}`", title="Key Claimed")
        else:
            await ctx.error(f"Failed to claim key: {result}")

async def setup(bot):
    await bot.add_cog(PremiumCog(bot))
