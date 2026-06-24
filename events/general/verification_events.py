import discord
from discord.ext import commands

class VerificationEvents(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager

    @commands.Cog.listener()
    async def on_member_join(self, member):
        config = await self.db.find_one('verification_config', {'_id': member.guild.id})
        if not config:
            return
        unverified_role_id = config.get('unverified_role_id')
        if not unverified_role_id:
            return
        role = member.guild.get_role(unverified_role_id)
        if role:
            try:
                await member.add_roles(role, reason='Automatic unverified role assignment')
            except discord.Forbidden:
                print(f'Failed to assign unverified role in {member.guild.name}: Missing permissions.')

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        config = await self.db.find_one('verification_config', {'_id': channel.guild.id})
        if not config:
            return
        unverified_role_id = config.get('unverified_role_id')
        if not unverified_role_id:
            return
        role = channel.guild.get_role(unverified_role_id)
        if role:
            try:
                await channel.set_permissions(role, view_channel=False, reason='Verification lockdown')
            except discord.Forbidden:
                pass

async def setup(bot):
    await bot.add_cog(VerificationEvents(bot))