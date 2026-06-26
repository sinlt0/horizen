import discord
from discord.ext import commands
import time
import asyncio
import re
import aiohttp
import io

class Booster(commands.Cog):
    category = 'config'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager

    async def get_config(self, guild_id):
        return await self.bot.get_config('booster_config', guild_id)

    async def update_config(self, guild_id, data):
        await self.bot.update_config('booster_config', guild_id, data)

    async def get_user_data(self, guild_id, user_id):
        data = await self.db.find_one('booster_users', {'_id': f"{guild_id}:{user_id}"})
        return data or {'boosts': 0, 'custom_role_id': None}

    async def get_boost_count(self, member):
        if member.id == member.guild.owner_id: return 99
        if await self.bot.is_owner(member): return 99
        if self.bot.dev_manager.is_dev(member.id, self.bot): return 99
        
        data = await self.get_user_data(member.guild.id, member.id)
        if data['boosts'] == 0 and member.premium_since:
            return 1
        return data['boosts']

    async def update_tiered_roles(self, member):
        config = await self.get_config(member.guild.id)
        tiers = config.get('tiers', {})
        if not tiers: return
        
        count = await self.get_boost_count(member)
        to_add = []
        to_remove = []
        
        for t_count, roles in tiers.items():
            t_roles = [member.guild.get_role(rid) for rid in roles if member.guild.get_role(rid)]
            if count >= int(t_count):
                to_add.extend(t_roles)
            else:
                to_remove.extend(t_roles)
                
        if to_remove:
            to_remove = [r for r in to_remove if r in member.roles]
            if to_remove:
                try: await member.remove_roles(*to_remove, reason="Booster System: Tier Update")
                except: pass
        if to_add:
            to_add = [r for r in to_add if r not in member.roles]
            if to_add:
                try: await member.add_roles(*to_add, reason="Booster System: Tier Update")
                except: pass

    @commands.group(name='booster', invoke_without_command=True, help='Manage the advanced booster system.')
    async def booster_group(self, ctx):
        config = await self.get_config(ctx.guild.id)
        if not config: return await ctx.info("Booster system is not configured. Use `booster setup`.")
        
        is_premium, _ = await self.bot.premium_manager.get_premium_status(ctx.guild.id)
        embed = self.bot.embed_manager.generic(title="Booster System Configuration")
        
        req = config.get('requirements', {})
        h_status = "Enabled" if config.get('hoist_enabled', True) else "Disabled"
        anchor = config.get('anchor', {})
        anchor_val = f"<@&{anchor['role_id']}> ({anchor.get('position', 'below')})" if anchor.get('role_id') else "Not Set"
        
        embed.add_field(name="Settings", value=f"• Global Hoist: `{h_status}`\n• Anchor Role: {anchor_val}\n• Blacklist: `{len(config.get('blacklist_names', []))}` words", inline=False)
        embed.add_field(name="Requirements", value=f"• Claim Role: `{req.get('claim', 1)} Boosts`\n• Role Icon: `{req.get('icon', 1)} Boosts`\n• Hoist Role: `{req.get('hoist', 2)} Boosts`", inline=False)
        
        tiers = config.get('tiers', {})
        if tiers:
            tier_desc = ""
            for count, roles in sorted(tiers.items(), key=lambda x: int(x[0])):
                role_mentions = ", ".join([f"<@&{r}>" for r in roles])
                tier_desc += f"**{count}x Boosts:** {role_mentions}\n"
            embed.add_field(name="Tiered Rewards", value=tier_desc, inline=False)
            
        await ctx.send(embed=embed)

    @booster_group.command(name='setup', help='Set the base requirements for custom roles.')
    @commands.has_permissions(administrator=True)
    async def booster_setup(self, ctx, claim: int = 1, icon: int = 1, hoist: int = 2):
        await self.db.update_one('booster_config', {'_id': ctx.guild.id}, {
            'requirements': {
                'claim': claim,
                'icon': icon,
                'hoist': hoist
            }
        }, upsert=True)

        await ctx.success(f"Booster requirements updated.\nClaim: `{claim}` | Icon: `{icon}` | Hoist: `{hoist}`")

    @booster_group.group(name='anchor', invoke_without_command=True, help='Manage the anchor role for hierarchy control.')
    @commands.has_permissions(administrator=True)
    async def anchor_group(self, ctx):
        await ctx.send_help(ctx.command)

    @anchor_group.command(name='set', help='Set the anchor role and its positioning.')
    async def anchor_set(self, ctx, role: discord.Role, position: str = 'below'):
        if position.lower() not in ['above', 'below']:
            return await ctx.error("Position must be either `above` or `below`.")
        
        await self.db.update_one('booster_config', {'_id': ctx.guild.id}, {
            'anchor': {
                'role_id': role.id,
                'position': position.lower()
            }
        }, upsert=True)

        await ctx.success(f"Anchor role set to {role.mention}. Custom roles will be created **{position}** it.")

    @booster_group.group(name='blacklist', invoke_without_command=True, help='Manage forbidden role names.')
    @commands.has_permissions(administrator=True)
    async def blacklist_group(self, ctx):
        await ctx.send_help(ctx.command)

    @blacklist_group.command(name='add', help='Add a word to the role name blacklist.')
    async def blacklist_add(self, ctx, word: str):
        is_premium, _ = await self.bot.premium_manager.get_premium_status(ctx.guild.id)
        config = await self.get_config(ctx.guild.id)
        bl = config.get('blacklist_names', [])
        
        limit = 100 if is_premium else 10
        if len(bl) >= limit:
            return await ctx.error(f"You have reached the blacklist limit of {limit}. Upgrade to Premium for more.")

        if word.lower() not in bl:
            bl.append(word.lower())
            await self.db.update_one('booster_config', {'_id': ctx.guild.id}, {'blacklist_names': bl}, upsert=True)
    
            await ctx.success(f"Added `{word}` to the booster role name blacklist.")
        else:
            await ctx.error("That word is already blacklisted.")

    @blacklist_group.command(name='remove', help='Remove a word from the blacklist.')
    async def blacklist_remove(self, ctx, word: str):
        config = await self.get_config(ctx.guild.id)
        bl = config.get('blacklist_names', [])
        if word.lower() in bl:
            bl.remove(word.lower())
            await self.db.update_one('booster_config', {'_id': ctx.guild.id}, {'blacklist_names': bl})
    
            await ctx.success(f"Removed `{word}` from the blacklist.")
        else:
            await ctx.error("That word is not in the blacklist.")

    @booster_group.group(name='tier', invoke_without_command=True, help='Manage role rewards for boost tiers.')
    @commands.has_permissions(administrator=True)
    async def tier_group(self, ctx):
        await ctx.send_help(ctx.command)

    @tier_group.command(name='add', help='Add a role reward to a specific boost tier.')
    async def tier_add(self, ctx, count: int, role: discord.Role):
        is_premium, _ = await self.bot.premium_manager.get_premium_status(ctx.guild.id)
        config = await self.get_config(ctx.guild.id)
        tiers = config.get('tiers', {})
        
        limit = 30 if is_premium else 5
        if len(tiers) >= limit:
            return await ctx.error(f"You have reached the limit of {limit} tiered rewards.")

        s_count = str(count)
        if s_count not in tiers: tiers[s_count] = []
        if role.id not in tiers[s_count]:
            tiers[s_count].append(role.id)
            
        await self.db.update_one('booster_config', {'_id': ctx.guild.id}, {'tiers': tiers}, upsert=True)

        
        await ctx.success(f"Added {role.mention} to the **{count}x Boost** tier. Syncing boosters...")
        # Background sync
        for member in ctx.guild.members:
            if member.premium_since: await self.update_tiered_roles(member)

    @tier_group.command(name='remove', help='Remove a role reward from a boost tier.')
    async def tier_remove(self, ctx, count: int, role: discord.Role):
        config = await self.get_config(ctx.guild.id)
        tiers = config.get('tiers', {})
        s_count = str(count)
        
        if s_count in tiers and role.id in tiers[s_count]:
            tiers[s_count].remove(role.id)
            if not tiers[s_count]: del tiers[s_count]
            await self.db.update_one('booster_config', {'_id': ctx.guild.id}, {'tiers': tiers})
    
            await ctx.success(f"Removed {role.mention} from the **{count}x Boost** tier.")
        else:
            await ctx.error("That role is not in that tier.")

    @booster_group.command(name='requirements', help='Set granular requirements for custom role features.')
    @commands.has_permissions(administrator=True)
    async def booster_requirements(self, ctx, claim: int, color: int, icon: int, hoist: int):
        await self.db.update_one('booster_config', {'_id': ctx.guild.id}, {
            'requirements': {
                'claim': claim,
                'color': color,
                'icon': icon,
                'hoist': hoist
            }
        }, upsert=True)

        await ctx.success(f"Requirements updated:\nClaim: `{claim}` | Color: `{color}` | Icon: `{icon}` | Hoist: `{hoist}`")

    @booster_group.command(name='perks', help='View your unlocked booster perks.')
    async def booster_perks(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        config = await self.get_config(ctx.guild.id)
        if not config: return await ctx.error("Booster system not setup.")
        
        count = await self.get_boost_count(member)
        req = config.get('requirements', {})
        
        embed = self.bot.embed_manager.generic(title=f"Booster Perks - {member.display_name}")
        embed.description = f"Current Boosts: `{count}`"
        
        def status(req_val): return "✅ Unlocked" if count >= req_val else f"❌ Locked (Needs {req_val})"

        embed.add_field(name="Custom Role Features", value=(
            f"• Claim Role: {status(req.get('claim', 1))}\n"
            f"• Role Icon: {status(req.get('icon', 1))}\n"
            f"• Hoist Role: {status(req.get('hoist', 2))}"
        ), inline=False)
        
        tiers = config.get('tiers', {})
        if tiers:
            tier_text = ""
            for t_count, roles in sorted(tiers.items(), key=lambda x: int(x[0])):
                s = "✅" if count >= int(t_count) else "🔒"
                role_mentions = ", ".join([f"<@&{r}>" for r in roles])
                tier_text += f"{s} **{t_count}x:** {role_mentions}\n"
            embed.add_field(name="Tiered Roles", value=tier_text, inline=False)
            
        await ctx.send(embed=embed)

    @booster_group.command(name='stats', help='View server boost statistics.')
    async def booster_stats(self, ctx):
        guild = ctx.guild
        embed = self.bot.embed_manager.generic(title=f"Boost Stats - {guild.name}")
        
        total_boosts = guild.premium_subscription_count
        level = guild.premium_tier
        
        next_level = level + 1 if level < 3 else "Max"
        boosts_needed = {1: 2, 2: 7, 3: 14}
        
        progress = ""
        if level < 3:
            needed = boosts_needed[next_level] - total_boosts
            progress = f"\nNext Level: **Level {next_level}** (Need `{max(0, needed)}` more)"
            
        embed.description = f"Current Level: **Level {level}**\nTotal Boosts: `{total_boosts}`{progress}"
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        
        # Count boosters from our DB or member list
        boosters = [m for m in guild.members if m.premium_since]
        embed.add_field(name="Boosters", value=f"Total: `{len(boosters)}`", inline=True)
        
        await ctx.send(embed=embed)

    @booster_group.group(name='role', aliases=['br'], invoke_without_command=True, help='Manage your custom booster role.')
    async def role_group(self, ctx):
        await ctx.send_help(ctx.command)

    @role_group.command(name='claim', help='Claim your custom booster role.')
    async def role_claim(self, ctx, *, name: str):
        count = await self.get_boost_count(ctx.author)
        config = await self.get_config(ctx.guild.id)
        req = config.get('requirements', {}).get('claim', 1)
        
        if count < req:
            return await ctx.error(f"You need at least `{req}` boosts to claim a custom role. You have `{count}`.")
            
        # Blacklist check
        bl = config.get('blacklist_names', [])
        if any(word in name.lower() for word in bl):
            return await ctx.error("That role name contains blacklisted words.")

        user_data = await self.get_user_data(ctx.guild.id, ctx.author.id)
        if user_data.get('custom_role_id'):
            return await ctx.error("You already have a custom role.")

        try:
            role = await ctx.guild.create_role(name=name, reason=f"Booster custom role: {ctx.author}")
            
            # Anchor Logic
            anchor = config.get('anchor', {})
            pos_role = ctx.guild.get_role(anchor.get('role_id'))
            if pos_role:
                new_pos = pos_role.position + (1 if anchor.get('position') == 'above' else -1)
                # Clamp position to avoid breaking bot perms
                new_pos = max(1, min(new_pos, ctx.guild.me.top_role.position - 1))
                await role.edit(position=new_pos)
            else:
                await role.edit(position=ctx.guild.me.top_role.position - 1)
                
            await ctx.author.add_roles(role)
            
            await self.db.update_one('booster_users', {'_id': f"{ctx.guild.id}:{ctx.author.id}"}, {
                'custom_role_id': role.id,
                'guild_id': ctx.guild.id,
                'user_id': ctx.author.id
            }, upsert=True)
            
            await ctx.success(f"Custom role **{name}** created and assigned!")
        except Exception as e:
            await ctx.error(f"Failed to create role: {e}")

    @role_group.command(name='edit', help='Staff command to edit a users custom role.')
    @commands.has_permissions(manage_roles=True)
    async def role_edit_staff(self, ctx, user: discord.Member, *, name: str):
        user_data = await self.get_user_data(ctx.guild.id, user.id)
        if not user_data.get('custom_role_id'): return await ctx.error("That user doesn't have a custom role.")
        
        role = ctx.guild.get_role(user_data['custom_role_id'])
        if not role: return await ctx.error("Custom role not found.")
        
        try:
            await role.edit(name=name)
            await ctx.success(f"Role for {user.mention} renamed to **{name}**.")
        except Exception as e:
            await ctx.error(f"Failed to edit: {e}")

    @role_group.command(name='name', help='Rename your custom role.')
    async def role_name(self, ctx, *, name: str):
        config = await self.get_config(ctx.guild.id)
        bl = config.get('blacklist_names', [])
        if any(word in name.lower() for word in bl):
            return await ctx.error("That role name contains blacklisted words.")
            
        user_data = await self.get_user_data(ctx.guild.id, ctx.author.id)
        if not user_data.get('custom_role_id'): return await ctx.error("You don't have a custom role.")
        
        role = ctx.guild.get_role(user_data['custom_role_id'])
        if not role: return await ctx.error("Custom role not found.")
        
        try:
            await role.edit(name=name)
            await ctx.success(f"Custom role renamed to **{name}**.")
        except Exception as e:
            await ctx.error(f"Failed to rename role: {e}")

    @role_group.command(name='color', help='Change the color of your custom role.')
    async def role_color(self, ctx, hex_code: str):
        user_data = await self.get_user_data(ctx.guild.id, ctx.author.id)
        if not user_data.get('custom_role_id'): return await ctx.error("You don't have a custom role.")
        
        role = ctx.guild.get_role(user_data['custom_role_id'])
        if not role: return await ctx.error("Custom role not found.")
        
        try:
            color = discord.Color.from_str(hex_code)
            await role.edit(color=color)
            await ctx.success(f"Custom role color updated to `{hex_code}`.")
        except:
            await ctx.error("Invalid hex code. Example: `#FF0000`")

    @role_group.command(name='icon', help='Set an icon for your custom role.')
    async def role_icon(self, ctx, url: str = None):
        user_data = await self.get_user_data(ctx.guild.id, ctx.author.id)
        if not user_data.get('custom_role_id'): return await ctx.error("You don't have a custom role.")
        
        count = await self.get_boost_count(ctx.author)
        config = await self.get_config(ctx.guild.id)
        req = config.get('requirements', {}).get('icon', 1)
        
        if count < req:
            return await ctx.error(f"You need at least `{req}` boosts for a role icon. You have `{count}`.")

        role = ctx.guild.get_role(user_data['custom_role_id'])
        if not role: return await ctx.error("Custom role not found.")
        
        icon_data = None
        if ctx.message.attachments:
            icon_data = await ctx.message.attachments[0].read()
        elif url:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        icon_data = await resp.read()
        
        if not icon_data: return await ctx.error("No image provided.")

        try:
            await role.edit(display_icon=icon_data)
            await ctx.success("Custom role icon updated!")
        except Exception as e:
            await ctx.error(f"Failed to update icon: {e}")

    @role_group.command(name='hoist', help='Toggle if your role is displayed separately.')
    async def role_hoist(self, ctx, status: bool):
        config = await self.get_config(ctx.guild.id)
        if not config.get('hoist_enabled', True):
            return await ctx.error("The hoist feature is globally disabled for custom roles in this server.")
            
        user_data = await self.get_user_data(ctx.guild.id, ctx.author.id)
        if not user_data.get('custom_role_id'): return await ctx.error("You don't have a custom role.")
        
        count = await self.get_boost_count(ctx.author)
        req = config.get('requirements', {}).get('hoist', 2)
        
        if count < req:
            return await ctx.error(f"You need at least `{req}` boosts to hoist your role. You have `{count}`.")

        role = ctx.guild.get_role(user_data['custom_role_id'])
        if not role: return await ctx.error("Custom role not found.")
        
        try:
            await role.edit(hoist=status)
            await ctx.success(f"Custom role hoist set to **{status}**.")
        except Exception as e:
            await ctx.error(f"Failed to update hoist: {e}")

    @role_group.command(name='delete', help='Delete your custom booster role.')
    async def role_delete(self, ctx):
        user_data = await self.get_user_data(ctx.guild.id, ctx.author.id)
        if not user_data.get('custom_role_id'): return await ctx.error("You don't have a custom role.")
        
        role = ctx.guild.get_role(user_data['custom_role_id'])
        if role:
            try: await role.delete(reason=f"Booster {ctx.author} deleted their custom role.")
            except: pass
            
        await self.db.update_one('booster_users', {'_id': f"{ctx.guild.id}:{ctx.author.id}"}, {'custom_role_id': None})
        await ctx.success("Your custom role has been deleted.")

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.premium_since == after.premium_since:
            return
            
        guild = after.guild
        # Stopped boosting
        if before.premium_since and not after.premium_since:
            user_data = await self.get_user_data(guild.id, after.id)
            if user_data.get('custom_role_id'):
                role = guild.get_role(user_data['custom_role_id'])
                if role:
                    try: await role.delete(reason="User stopped boosting.")
                    except: pass
                await self.db.update_one('booster_users', {'_id': f"{guild.id}:{after.id}"}, {'custom_role_id': None})
            
            await self.db.update_one('booster_users', {'_id': f"{guild.id}:{after.id}"}, {'boosts': 0}, upsert=True)
            await self.update_tiered_roles(after)

        # Started boosting
        elif not before.premium_since and after.premium_since:
            # We treat starting to boost as 1 boost count. 
            # Manually can be increased with set-boosts
            await self.db.update_one('booster_users', {'_id': f"{guild.id}:{after.id}"}, {'boosts': 1}, upsert=True)
            await self.update_tiered_roles(after)

async def setup(bot):
    await bot.add_cog(Booster(bot))
