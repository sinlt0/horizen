import discord
from discord.ext import commands
import json
import os
from utils.prefix_manager import PrefixManager

def is_dev():
    async def predicate(ctx):
        if await ctx.bot.is_owner(ctx.author):
            return True
        if hasattr(ctx.bot, 'dev_manager') and ctx.bot.dev_manager.is_dev(ctx.author.id, ctx.bot):
            return True
        raise commands.NotOwner("This command is restricted to bot developers.")
    return commands.check(predicate)

class DevCog(commands.Cog):
    category = "dev"

    def __init__(self, bot):
        self.bot = bot
        self.prefix_manager = bot.prefix_manager

    @commands.command(name='adddev', help='Add a user to the developers list (Owner Only).')
    @commands.is_owner()
    async def add_developer(self, ctx, user: discord.User):
        if user.id in self.bot.dev_manager.dev_ids:
            return await ctx.warning(f"{user.mention} is already a developer.")
        self.bot.dev_manager.dev_ids.add(user.id)
        with open(self.bot.dev_manager.file_path, 'w') as f:
            json.dump({"dev_ids": list(self.bot.dev_manager.dev_ids)}, f, indent=4)
        await ctx.success(f"Added {user.mention} to the developer list.")

    @commands.command(name='removedev', help='Remove a user from the developers list (Owner Only).')
    @commands.is_owner()
    async def remove_developer(self, ctx, user: discord.User):
        if user.id not in self.bot.dev_manager.dev_ids:
            return await ctx.warning(f"{user.mention} is not in the developer list.")
        self.bot.dev_manager.dev_ids.remove(user.id)
        with open(self.bot.dev_manager.file_path, 'w') as f:
            json.dump({"dev_ids": list(self.bot.dev_manager.dev_ids)}, f, indent=4)
        await ctx.success(f"Removed {user.mention} from the developer list.")

    @commands.command(name='devlist', help='List all bot developers.')
    @is_dev()
    async def developer_list(self, ctx):
        devs = []
        for dev_id in self.bot.dev_manager.dev_ids:
            user = self.bot.get_user(dev_id)
            devs.append(f"{user.mention} ({dev_id})" if user else f"Unknown User ({dev_id})")
        description = "\n".join(devs) if devs else "No developers added yet."
        await ctx.embed(description, title="Bot Developers")

    @commands.command(name='addnoprefix', help='Grant a user permission to use no prefix (Devs/Owner).')
    @is_dev()
    async def add_no_prefix_user(self, ctx, user: discord.User):
        await self.prefix_manager.add_no_prefix_user(user.id)
        await ctx.success(f'User {user.mention} can now use commands without a prefix.')

    @commands.command(name='removenoprefix', help='Revoke a user\'s no-prefix permission (Devs/Owner).')
    @is_dev()
    async def remove_no_prefix_user(self, ctx, user: discord.User):
        await self.prefix_manager.remove_no_prefix_user(user.id)
        await ctx.success(f'User {user.mention} can no longer use commands without a prefix.')

    @commands.command(name='noprefixlist', help='List all users allowed to use no prefix (Devs/Owner).')
    @is_dev()
    async def no_prefix_list(self, ctx):
        users = await self.prefix_manager.get_no_prefix_users()
        if not users:
            return await ctx.info("No users are currently allowed to use no prefix.")
        user_mentions = []
        for user_id in users:
            user = self.bot.get_user(user_id)
            user_mentions.append(user.mention if user else f"<@{user_id}>")
        await ctx.embed("\n".join(user_mentions), title="No-Prefix Allowed Users")

    @commands.command(name='shutdown', aliases=['stop'], help='Shutdown the bot (Owner Only).')
    @commands.is_owner()
    async def shutdown(self, ctx):
        await ctx.success("Shutting down... Goodbye!", title="Shutdown")
        await self.bot.close()

    @commands.command(name='restart', help='Restart the bot (Devs/Owner).')
    @is_dev()
    async def restart(self, ctx):
        import sys
        await ctx.success("Restarting... Please wait.", title="Restart")
        os.execv(sys.executable, ['python'] + sys.argv)

    @commands.command(name='jishaku', aliases=['jsk'], help='Load the jishaku extension (Devs/Owner).')
    @is_dev()
    async def load_jishaku(self, ctx):
        try:
            await self.bot.load_extension('jishaku')
            await ctx.success("Jishaku has been loaded successfully.")
        except Exception as e:
            await ctx.error(f"Failed to load jishaku: {e}")

async def setup(bot):
    await bot.add_cog(DevCog(bot))
