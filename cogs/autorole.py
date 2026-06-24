import discord
from discord.ext import commands
import asyncio
import datetime

class AutoRole(commands.Cog):
    category = 'config'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager

    async def get_config(self, guild_id):
        config = await self.db.find_one('autorole_config', {'_id': guild_id})
        return config or {}

    @commands.group(name='autorole', aliases=['ar'], invoke_without_command=True, help='Configure automatic role assignment for new members.')
    @commands.has_permissions(administrator=True)
    async def autorole_group(self, ctx):
        config = await self.get_config(ctx.guild.id)
        if not config: return await ctx.info("AutoRole is not configured. Use `!autorole human` or `!autorole bot` to begin.")
        status = '✅ Enabled' if config.get('enabled', True) else '❌ Disabled'
        h_roles = [ctx.guild.get_role(r).mention for r in config.get('human_roles', []) if ctx.guild.get_role(r)]
        b_roles = [ctx.guild.get_role(r).mention for r in config.get('bot_roles', []) if ctx.guild.get_role(r)]
        desc = f"**Status:** {status}\n\n**Human Roles:** {', '.join(h_roles) if h_roles else 'None'}\n**Bot Roles:** {', '.join(b_roles) if b_roles else 'None'}"
        await ctx.embed(desc, title="AutoRole Configuration")

    @autorole_group.command(name='toggle', help='Enable or disable AutoRole system.')
    @commands.has_permissions(administrator=True)
    async def autorole_toggle(self, ctx, status: bool):
        await self.db.update_one('autorole_config', {'_id': ctx.guild.id}, {'enabled': status}, upsert=True)
        await ctx.success(f"AutoRole system {'enabled' if status else 'disabled'}.")

    @autorole_group.group(name='human', invoke_without_command=True, help='Manage roles for humans.')
    @commands.has_permissions(administrator=True)
    async def autorole_human(self, ctx):
        config = await self.get_config(ctx.guild.id)
        roles = [ctx.guild.get_role(r).mention for r in config.get('human_roles', []) if ctx.guild.get_role(r)]
        await ctx.embed(", ".join(roles) if roles else "None", title="AutoRole: Humans")

    @autorole_human.command(name='add', help='Add a role to the human autorole list.')
    @commands.has_permissions(administrator=True)
    async def human_add(self, ctx, role: discord.Role):
        if role >= ctx.guild.me.top_role: return await ctx.error("I cannot assign a role higher than mine.")
        config = await self.get_config(ctx.guild.id)
        roles = config.get('human_roles', [])
        if role.id in roles: return await ctx.warning("That role is already in the list.")
        roles.append(role.id)
        await self.db.update_one('autorole_config', {'_id': ctx.guild.id}, {'human_roles': roles}, upsert=True)
        await ctx.success(f"Added {role.mention} to human autoroles.")

    @autorole_human.command(name='remove', help='Remove a role from the human autorole list.')
    @commands.has_permissions(administrator=True)
    async def human_remove(self, ctx, role: discord.Role):
        config = await self.get_config(ctx.guild.id)
        roles = config.get('human_roles', [])
        if role.id not in roles: return await ctx.warning("That role is not in the list.")
        roles.remove(role.id)
        await self.db.update_one('autorole_config', {'_id': ctx.guild.id}, {'human_roles': roles}, upsert=True)
        await ctx.success(f"Removed {role.mention} from human autoroles.")

    @autorole_group.group(name='bot', invoke_without_command=True, help='Manage roles for bots.')
    @commands.has_permissions(administrator=True)
    async def bots_autorole_group(self, ctx):
        config = await self.get_config(ctx.guild.id)
        roles = [ctx.guild.get_role(r).mention for r in config.get('bot_roles', []) if ctx.guild.get_role(r)]
        await ctx.embed(", ".join(roles) if roles else "None", title="AutoRole: Bots")

    @bots_autorole_group.command(name='add', help='Add a role to the bot autorole list.')
    @commands.has_permissions(administrator=True)
    async def add_bot_role(self, ctx, role: discord.Role):
        if role >= ctx.guild.me.top_role: return await ctx.error("I cannot assign a role higher than mine.")
        config = await self.get_config(ctx.guild.id)
        roles = config.get('bot_roles', [])
        if role.id in roles: return await ctx.warning("That role is already in the list.")
        roles.append(role.id)
        await self.db.update_one('autorole_config', {'_id': ctx.guild.id}, {'bot_roles': roles}, upsert=True)
        await ctx.success(f"Added {role.mention} to bot autoroles.")

    @bots_autorole_group.command(name='remove', help='Remove a role from the bot autorole list.')
    @commands.has_permissions(administrator=True)
    async def remove_bot_role(self, ctx, role: discord.Role):
        config = await self.get_config(ctx.guild.id)
        roles = config.get('bot_roles', [])
        if role.id not in roles: return await ctx.warning("That role is not in the list.")
        roles.remove(role.id)
        await self.db.update_one('autorole_config', {'_id': ctx.guild.id}, {'bot_roles': roles}, upsert=True)
        await ctx.success(f"Removed {role.mention} from bot autoroles.")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        config = await self.get_config(member.guild.id)
        if not config or not config.get('enabled', True): return
        if member.bot:
            role_ids = config.get('bot_roles', [])
            roles = [member.guild.get_role(r) for r in role_ids if member.guild.get_role(r)]
            if roles:
                try: await member.add_roles(*roles, reason="AutoRole: Bot Join")
                except: pass
        else:
            v_config = await self.bot.db_manager.find_one('verification_config', {'_id': member.guild.id})
            if not v_config or not v_config.get('enabled'):
                delay = v_config.get('joingate_delay', 0) if v_config else 0
                if delay > 0: await asyncio.sleep(delay)
                if not member.guild.get_member(member.id): return
                role_ids = config.get('human_roles', [])
                roles = [member.guild.get_role(r) for r in role_ids if member.guild.get_role(r)]
                if roles:
                    try: await member.add_roles(*roles, reason="AutoRole: Human Join (Gated)")
                    except: pass

    @commands.Cog.listener()
    async def on_verification_success(self, member):
        config = await self.get_config(member.guild.id)
        if not config or not config.get('enabled', True): return
        role_ids = config.get('human_roles', [])
        roles = [member.guild.get_role(r) for r in role_ids if member.guild.get_role(r)]
        if roles:
            try: await member.add_roles(*roles, reason="AutoRole: Human Verified")
            except: pass

async def setup(bot):
    await bot.add_cog(AutoRole(bot))
