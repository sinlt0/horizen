import discord
from discord.ext import commands, tasks
import asyncio

class StatusRewards(commands.Cog):
    category = 'utility'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager
        self.role_queue = asyncio.Queue()
        self.check_all_members.start()
        self.queue_processor.start()

    def cog_unload(self):
        self.check_all_members.cancel()
        self.queue_processor.cancel()

    async def get_config(self, guild_id):
        return await self.bot.get_config('status_reward_config', guild_id)

    async def update_config(self, guild_id, data):
        await self.bot.update_config('status_reward_config', guild_id, data)

    @tasks.loop(seconds=2)
    async def queue_processor(self):
        if self.role_queue.empty(): return
        
        member, role, action, reason, config = await self.role_queue.get()
        try:
            if action == "add":
                await member.add_roles(role, reason=reason)
                log_msg = f"{self.bot.e.success} {member.mention} added the vanity! Role {role.mention} granted."
            else:
                await member.remove_roles(role, reason=reason)
                log_msg = f"{self.bot.e.error} {member.mention} removed the vanity. Role {role.mention} revoked."
            
            log_channel = member.guild.get_channel(config.get('log_channel'))
            if log_channel:
                await log_channel.send(embed=self.bot.embed_manager.generic(description=log_msg, title="Status Reward"))
        except discord.HTTPException as e:
            if e.status == 429:
                await self.role_queue.put((member, role, action, reason, config))
                await asyncio.sleep(e.retry_after or 5)
        except: pass
        finally:
            self.role_queue.task_done()

    def _has_status(self, member, required_text):
        if not member.activities: return False
        for activity in member.activities:
            if isinstance(activity, discord.CustomActivity):
                if activity.text and required_text.lower() in activity.text.lower():
                    return True
        return False

    async def _process_member(self, member, config):
        if member.bot: return
        role_id = config.get('role_id')
        required_text = config.get('text')
        if not role_id or not required_text: return

        role = member.guild.get_role(role_id)
        if not role: return

        is_representing = self._has_status(member, required_text)
        
        if is_representing:
            if role not in member.roles:
                await self.role_queue.put((member, role, "add", f"Status Reward: Supporting {required_text}", config))
        else:
            if role in member.roles:
                await self.role_queue.put((member, role, "remove", f"Status Reward: No longer supporting {required_text}", config))

    @commands.Cog.listener()
    async def on_presence_update(self, before, after):
        if not after.guild: return
        config = await self.get_config(after.guild.id)
        if not config.get('enabled'): return
        
        if before.activities != after.activities:
            await self._process_member(after, config)

    @tasks.loop(minutes=30)
    async def check_all_members(self):
        for guild in self.bot.guilds:
            config = await self.get_config(guild.id)
            if not config.get('enabled'): continue
            for member in guild.members:
                await self._process_member(member, config)
                await asyncio.sleep(0.2)

    @commands.group(name="statusreward", aliases=["sr", "vanityreward"], invoke_without_command=True, help="Configure rewards for users with specific status text.")
    @commands.has_permissions(administrator=True)
    async def sr_group(self, ctx):
        config = await self.get_config(ctx.guild.id)
        status = f"{ctx.e.success} Enabled" if config.get('enabled') else f"{ctx.e.error} Disabled"
        role = ctx.guild.get_role(config.get('role_id'))
        text = config.get('text', 'Not Set')
        
        representers = 0
        if config.get('enabled') and role:
            representers = len([m for m in ctx.guild.members if role in m.roles])

        desc = (
            f"**Status:** {status}\n"
            f"**Required Text:** `{text}`\n"
            f"**Reward Role:** {role.mention if role else 'Not Set'}\n"
            f"**Current Representers:** `{representers}`\n"
            f"**Log Channel:** {ctx.guild.get_channel(config.get('log_channel')).mention if config.get('log_channel') else 'Not Set'}"
        )
        await ctx.embed(desc, title=f"{ctx.e.presence} Status Reward Configuration")

    @sr_group.command(name="stats", help="View analytics for status representation.")
    async def sr_stats(self, ctx):
        config = await self.get_config(ctx.guild.id)
        role = ctx.guild.get_role(config.get('role_id'))
        if not role: return await ctx.error("Reward role not set.")
        
        reps = [m for m in ctx.guild.members if role in m.roles]
        
        embed = self.bot.embed_manager.generic(
            description=(
                f"📈 **Total Members Representing:** `{len(reps)}`\n"
                f"🎯 **Target Text:** `{config.get('text', 'None')}`\n\n"
                f"**Top Supporters:**\n" + ", ".join([m.mention for m in reps[:15]]) + (f" and {len(reps)-15} more" if len(reps) > 15 else "")
            ),
            title="Status Reward Analytics"
        )
        await ctx.send(embed=embed)

    @sr_group.command(name="enable", help="Enable the status reward system.")
    @commands.has_permissions(administrator=True)
    async def sr_enable(self, ctx):
        config = await self.get_config(ctx.guild.id)
        if not config.get('role_id') or not config.get('text'):
            return await ctx.error("Please set a role and text first using `sr role` and `sr text`.")
        
        await self.update_config(ctx.guild.id, {'enabled': True})
        await ctx.success("Status Reward system **enabled**.")

    @sr_group.command(name="disable", help="Disable the status reward system.")
    @commands.has_permissions(administrator=True)
    async def sr_disable(self, ctx):
        await self.update_config(ctx.guild.id, {'enabled': False})
        await ctx.success("Status Reward system **disabled**.")

    @sr_group.command(name="text", help="Set the text required in user status (e.g. your server vanity).")
    @commands.has_permissions(administrator=True)
    async def sr_text(self, ctx, *, text: str):
        await self.update_config(ctx.guild.id, {'text': text})
        await ctx.success(f"Required status text set to: `{text}`")

    @sr_group.command(name="role", help="Set the role to be rewarded.")
    @commands.has_permissions(administrator=True)
    async def sr_role(self, ctx, role: discord.Role):
        if role >= ctx.guild.me.top_role:
            return await ctx.error("I cannot manage this role as it is above me in the hierarchy.")
        
        await self.update_config(ctx.guild.id, {'role_id': role.id})
        await ctx.success(f"Reward role set to {role.mention}")

    @sr_group.command(name="logs", help="Set the channel for status reward logs.")
    @commands.has_permissions(administrator=True)
    async def sr_logs(self, ctx, channel: discord.TextChannel = None):
        cid = channel.id if channel else None
        await self.update_config(ctx.guild.id, {'log_channel': cid})
        await ctx.success(f"Status reward logs will be sent to {channel.mention if channel else 'nowhere'}.")

    @sr_group.command(name="check", help="Manually check a user for the status reward.")
    @commands.has_permissions(manage_roles=True)
    async def sr_check(self, ctx, member: discord.Member):
        config = await self.get_config(ctx.guild.id)
        if not config.get('enabled'): return await ctx.error("System is disabled.")
        
        await self._process_member(member, config)
        await ctx.success(f"Processed status check for {member.mention}.")

async def setup(bot):
    await bot.add_cog(StatusRewards(bot))
