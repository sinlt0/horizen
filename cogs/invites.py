import discord
from discord.ext import commands, tasks
import datetime
import asyncio
import collections
import time

class Invites(commands.Cog):
    category = 'utility'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager
        self.invite_cache = {}
        self.bot.loop.create_task(self._initialize_cache())

    async def _initialize_cache(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            try:
                invs = await guild.invites()
                self.invite_cache[guild.id] = {i.code: i.uses for i in invs}
                if guild.vanity_url_code:
                    try:
                        vanity = await guild.vanity_invite()
                        self.invite_cache[guild.id][vanity.code] = vanity.uses
                    except: pass
            except discord.Forbidden:
                continue

    async def get_config(self, guild_id):
        return await self.bot.get_config('invite_config', guild_id)

    async def update_config(self, guild_id, data):
        await self.bot.update_config('invite_config', guild_id, data)

    async def get_user_data(self, guild_id, user_id):
        key = f"{guild_id}-{user_id}"
        return await self.db.find_one('invite_data', {'_id': key}) or {
            'regular': 0, 'fake': 0, 'bonus': 0, 'leaves': 0, 'invited_users': []
        }

    async def update_user_data(self, guild_id, user_id, data):
        key = f"{guild_id}-{user_id}"
        await self.db.update_one('invite_data', {'_id': key}, data, upsert=True)

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        if invite.guild.id not in self.invite_cache:
            self.invite_cache[invite.guild.id] = {}
        self.invite_cache[invite.guild.id][invite.code] = invite.uses

    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        if invite.guild.id in self.invite_cache:
            self.invite_cache[invite.guild.id].pop(invite.code, None)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        try:
            invs = await guild.invites()
            self.invite_cache[guild.id] = {i.code: i.uses for i in invs}
        except: pass

    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild = member.guild
        if guild.id not in self.invite_cache: return
        
        cached_invs = self.invite_cache[guild.id]
        try: current_invs = await guild.invites()
        except discord.Forbidden: return

        inviter = None
        used_invite = None

        for inv in current_invs:
            if inv.code in cached_invs and inv.uses > cached_invs[inv.code]:
                inviter = inv.inviter
                used_invite = inv
                break
            cached_invs[inv.code] = inv.uses

        self.invite_cache[guild.id] = {i.code: i.uses for i in current_invs}

        if not inviter and guild.vanity_url_code:
            try:
                vanity = await guild.vanity_invite()
                if vanity.code in cached_invs and vanity.uses > cached_invs[vanity.code]:
                    inviter = "Vanity"
                    used_invite = vanity
                cached_invs[vanity.code] = vanity.uses
            except: pass

        if inviter:
            config = await self.get_config(guild.id)
            if inviter == "Vanity":
                inviter_id = "Vanity"
                inviter_name = "Vanity URL"
            else:
                inviter_id = inviter.id
                inviter_name = inviter.name
                
                inviter_data = await self.get_user_data(guild.id, inviter_id)
                is_fake = False
                min_age = config.get('min_age', 0)
                if (discord.utils.utcnow() - member.created_at).days < min_age:
                    is_fake = True
                
                if is_fake:
                    inviter_data['fake'] = inviter_data.get('fake', 0) + 1
                else:
                    inviter_data['regular'] = inviter_data.get('regular', 0) + 1
                    inviter_data.setdefault('invited_users', []).append(member.id)
                
                await self.update_user_data(guild.id, inviter_id, inviter_data)
                await self._check_rewards(member, inviter, inviter_data)

            await self.db.update_one('joined_members_map', {'_id': f"{guild.id}-{member.id}"}, {'inviter_id': inviter_id}, upsert=True)

            log_channel_id = config.get('channel_id')
            if log_channel_id:
                channel = guild.get_channel(log_channel_id)
                if channel:
                    if inviter_id == "Vanity":
                        desc = f"{self.bot.e.joined} {member.mention} joined using the **Vanity URL**."
                    else:
                        total = inviter_data['regular'] + inviter_data['bonus'] - inviter_data['leaves'] - inviter_data['fake']
                        desc = f"{self.bot.e.joined} {member.mention} joined using **{inviter_name}**'s invite.\n> **Total Invites:** `{total}`"
                    
                    embed = self.bot.embed_manager.generic(description=desc, title="Member Joined")
                    embed.set_thumbnail(url=member.display_avatar.url)
                    embed.set_footer(text=f"ID: {member.id} | Code: {used_invite.code}")
                    await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        guild = member.guild
        mapping = await self.db.find_one('joined_members_map', {'_id': f"{guild.id}-{member.id}"})
        if not mapping: return
        
        inviter_id = mapping.get('inviter_id')
        await self.db.delete_one('joined_members_map', {'_id': f"{guild.id}-{member.id}"})
        
        if inviter_id and inviter_id != "Vanity":
            inv_data = await self.get_user_data(guild.id, inviter_id)
            if member.id in inv_data.get('invited_users', []):
                inv_data['invited_users'].remove(member.id)
            inv_data['leaves'] = inv_data.get('leaves', 0) + 1
            await self.update_user_data(guild.id, inviter_id, inv_data)
            
            config = await self.get_config(guild.id)
            log_channel_id = config.get('channel_id')
            if log_channel_id:
                channel = guild.get_channel(log_channel_id)
                if channel:
                    inviter = guild.get_member(inviter_id) or await self.bot.fetch_user(inviter_id)
                    total = inv_data['regular'] + inv_data['bonus'] - inv_data['leaves'] - inv_data['fake']
                    embed = self.bot.embed_manager.generic(
                        description=f"{self.bot.e.error} {member.mention} left. Invited by **{inviter}**.\n> **Total Invites:** `{total}`",
                        title="Member Left",
                        color=discord.Color.red()
                    )
                    await channel.send(embed=embed)

    async def _check_rewards(self, member, inviter, data):
        if not isinstance(inviter, discord.Member): return
        config = await self.get_config(member.guild.id)
        rewards = config.get('rewards', {})
        if not rewards: return
        
        total = data['regular'] + data['bonus'] - data['leaves'] - data['fake']
        for count, role_id in rewards.items():
            if total >= int(count):
                role = member.guild.get_role(int(role_id))
                if role and role not in inviter.roles:
                    try: await inviter.add_roles(role, reason="Invite Reward")
                    except: pass

    @commands.group(name="invites", aliases=["inv"], invoke_without_command=True, help="View invite statistics.")
    async def invites_group(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        data = await self.get_user_data(ctx.guild.id, member.id)
        
        total = data['regular'] + data['bonus'] - data['leaves'] - data['fake']
        
        desc = (
            f"{ctx.e.members} **Total Invites:** `{total}`\n\n"
            f"{ctx.e.success} Regular: `{data['regular']}`\n"
            f"{ctx.e.error} Leaves: `{data['leaves']}`\n"
            f"{ctx.e.warning} Fake: `{data['fake']}`\n"
            f"{ctx.e.boost} Bonus: `{data['bonus']}`"
        )
        
        await ctx.embed(desc, title=f"{ctx.e.user} Invites: {member.name}")

    @invites_group.command(name="leaderboard", aliases=["lb", "top"], help="Show the top inviters in the server.")
    async def invites_leaderboard(self, ctx):
        res = await self.db.find('invite_data', {'_id': {'$regex': f'^{ctx.guild.id}-'}})
        if not res: return await ctx.error("No invite data found for this server.")
        
        lb_data = []
        for doc in res:
            uid = int(doc['_id'].split('-')[1])
            total = doc.get('regular', 0) + doc.get('bonus', 0) - doc.get('leaves', 0) - doc.get('fake', 0)
            if total > 0:
                lb_data.append((uid, total))
        
        lb_data.sort(key=lambda x: x[1], reverse=True)
        if not lb_data: return await ctx.info("The leaderboard is currently empty.")
        
        desc = ""
        for i, (uid, total) in enumerate(lb_data[:10], 1):
            user = self.bot.get_user(uid) or f"Unknown ({uid})"
            desc += f"`{i}.` **{user}** — `{total}` invites\n"
            
        await ctx.embed(desc, title=f"{ctx.e.members} Invite Leaderboard")

    @invites_group.command(name="details", help="View the list of members invited by a user.")
    async def invites_details(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        data = await self.get_user_data(ctx.guild.id, member.id)
        
        invited_ids = data.get('invited_users', [])
        if not invited_ids:
            return await ctx.info(f"**{member.name}** hasn't invited anyone yet.")
            
        mentions = []
        for uid in invited_ids[-20:]:
            u = self.bot.get_user(uid)
            mentions.append(u.mention if u else f"`{uid}`")
            
        desc = f"**Last 20 invited members:**\n" + ", ".join(mentions)
        if len(invited_ids) > 20:
            desc += f"\n\n*... and {len(invited_ids) - 20} more.*"
            
        await ctx.embed(desc, title=f"{ctx.e.user} Invite Details: {member.name}")

    @invites_group.command(name="config", help="Configure invite tracking.")
    @commands.has_permissions(administrator=True)
    async def invites_config(self, ctx, channel: discord.TextChannel = None):
        if not channel:
            config = await self.get_config(ctx.guild.id)
            ch = ctx.guild.get_channel(config.get('channel_id'))
            return await ctx.info(f"**Logging:** {ch.mention if ch else 'Not Set'}\n**Min Account Age:** `{config.get('min_age', 0)}` days")
        
        await self.update_config(ctx.guild.id, {'channel_id': channel.id})
        await ctx.success(f"Invite logging channel set to {channel.mention}")

    @invites_group.command(name="minage", help="Set minimum account age for valid invites.")
    @commands.has_permissions(administrator=True)
    async def invites_minage(self, ctx, days: int):
        await self.update_config(ctx.guild.id, {'min_age': days})
        await ctx.success(f"Minimum account age set to **{days} days**.")

    @invites_group.command(name="addreward", help="Add an invite role reward.")
    @commands.has_permissions(administrator=True)
    async def invites_addreward(self, ctx, count: int, role: discord.Role):
        await self.update_config(ctx.guild.id, {'$set': {f'rewards.{count}': role.id}})
        await ctx.success(f"Added reward: {role.mention} at `{count}` invites.")

    @invites_group.command(name="removereward", help="Remove an invite reward.")
    @commands.has_permissions(administrator=True)
    async def invites_removereward(self, ctx, count: int):
        await self.update_config(ctx.guild.id, {'$unset': {f'rewards.{count}': ""}})
        await ctx.success(f"Removed reward for `{count}` invites.")

    @invites_group.command(name="addbonus", help="Add bonus invites to a user.")
    @commands.has_permissions(manage_guild=True)
    async def invites_add_bonus(self, ctx, member: discord.Member, amount: int):
        data = await self.get_user_data(ctx.guild.id, member.id)
        data['bonus'] = data.get('bonus', 0) + amount
        await self.update_user_data(ctx.guild.id, member.id, data)
        await ctx.success(f"Added **{amount}** bonus invites to {member.mention}.")

    @invites_group.command(name="reset", help="Reset invite data.")
    @commands.has_permissions(administrator=True)
    async def invites_reset(self, ctx, member: discord.Member = None):
        if member:
            await self.db.delete_one('invite_data', {'_id': f"{ctx.guild.id}-{member.id}"})
            await ctx.success(f"Reset invites for {member.mention}.")
        else:
            await self.db.delete_one('invite_data', {'_id': {'$regex': f'^{ctx.guild.id}-'}})
            await self.db.delete_one('joined_members_map', {'_id': {'$regex': f'^{ctx.guild.id}-'}})
            await ctx.success("Reset all invite data for this server.")

async def setup(bot):
    await bot.add_cog(Invites(bot))
