from discord.ext import commands

class GuildEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """Automatically assign a cluster to a guild when it joins"""
        # The assign_guild method handles both DB update and local cache update
        await self.bot.db_manager.assign_guild(guild.id)
        print(f"Bot joined guild {guild.name} ({guild.id}) and assigned it to a database cluster.")

async def setup(bot):
    await bot.add_cog(GuildEvents(bot))
