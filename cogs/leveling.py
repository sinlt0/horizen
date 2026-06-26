import discord
from discord.ext import commands
import random
import time
import asyncio
import re
import io
from PIL import Image, ImageDraw, ImageFont
import aiohttp

class Leveling(commands.Cog):
    category = 'leveling'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager
        self._cooldowns = {}

    async def get_config(self, guild_id):
        return await self.db.find_one('leveling_config', {'_id': guild_id}) or {}

    def _get_xp_for_level(self, level):
        if level < 0: return 0
        return int(5 * (level ** 2) + (50 * level) + 100)

    def _get_level_from_xp(self, total_xp):
        level = 0
        while total_xp >= self._get_xp_for_level(level):
            total_xp -= self._get_xp_for_level(level)
            level += 1
        return level, total_xp

    def _parse_variables(self, text, member: discord.Member, level_data: dict = None):
        if not text: return ""
        guild = member.guild
        now = discord.utils.utcnow()
        variables = {
            '{user}': member.mention, '{user_mention}': member.mention,
            '{user_name}': member.name, '{user_display}': member.display_name,
            '{user_id}': str(member.id), '{user_avatar}': member.display_avatar.url,
            '{server_name}': guild.name, '{server_icon}': guild.icon.url if guild.icon else "",
            '{member_count}': str(guild.member_count), '{boost_count}': str(guild.premium_subscription_count),
            '{boost_level}': str(guild.premium_tier), '{current_time}': f"<t:{int(now.timestamp())}:T>",
            '{current_date}': f"<t:{int(now.timestamp())}:D>"
        }
        if level_data:
            variables.update({
                '{level}': str(level_data.get('level', 0)),
                '{old_level}': str(level_data.get('old_level', 0)),
                '{total_xp}': str(level_data.get('total_xp', 0)),
                '{xp_to_next}': str(level_data.get('xp_to_next', 0)),
                '{rank}': str(level_data.get('rank', 'Unknown')),
                '{new_roles}': level_data.get('new_roles', 'None')
            })
        for key, value in variables.items():
            text = text.replace(key, str(value))
        return text

    async def _handle_level_up(self, member, level, old_level, total_xp):
        config = await self.get_config(member.guild.id)
        if not config.get('enabled', True): return

        rewards = config.get('rewards', {})
        new_roles_list = []
        roles_to_add = []
        roles_to_remove = []
        mode = config.get('reward_mode', 'stacking')
        all_milestones = sorted([int(k) for k in rewards.keys()])
        
        for m_level in all_milestones:
            r_ids = rewards[str(m_level)]
            m_roles = [member.guild.get_role(rid) for rid in r_ids if member.guild.get_role(rid)]
            if level >= m_level:
                if mode == 'stacking': roles_to_add.extend(m_roles)
                else:
                    highest_reached = max([m for m in all_milestones if level >= m])
                    if m_level == highest_reached: roles_to_add.extend(m_roles)
                    else: roles_to_remove.extend(m_roles)
            if level == m_level: new_roles_list.extend([r.mention for r in m_roles])

        try:
            if roles_to_remove:
                roles_to_remove = [r for r in roles_to_remove if r in member.roles]
                if roles_to_remove: await member.remove_roles(*roles_to_remove, reason="Leveling Reward Update")
            if roles_to_add:
                roles_to_add = [r for r in roles_to_add if r not in member.roles]
                if roles_to_add: await member.add_roles(*roles_to_add, reason="Leveling Reward Reached")
        except: pass

        notify_type = config.get('notify_type', 'channel')
        if notify_type == 'disabled': return

        all_guild_xp = await self.db.find('users_xp', {'guild_id': member.guild.id}, sort=[('xp', -1)])
        rank = "N/A"
        for i, entry in enumerate(all_guild_xp):
            if str(entry.get('user_id')) == str(member.id):
                rank = i + 1
                break

        level_data = {
            'level': level, 'old_level': old_level, 'total_xp': total_xp,
            'xp_to_next': self._get_xp_for_level(level),
            'new_roles': ", ".join(new_roles_list) if new_roles_list else "None",
            'rank': rank
        }

        msg_content = config.get('notify_msg', "GG {user}, you just leveled up to **Level {level}**!")
        parsed_content = self._parse_variables(msg_content, member, level_data)
        embed_data = config.get('notify_embed')
        embed = None
        if embed_data:
            embed = discord.Embed(
                title=self._parse_variables(embed_data.get('title', 'Level Up!'), member, level_data),
                description=self._parse_variables(embed_data.get('description', ''), member, level_data),
                color=int(str(embed_data.get('color', '#4A3F5F')).replace('#', ''), 16)
            )
            if embed_data.get('footer'): embed.set_footer(text=self._parse_variables(embed_data['footer'], member, level_data))
            if embed_data.get('thumbnail'): embed.set_thumbnail(url=member.display_avatar.url)

        try:
            if notify_type == 'dm': await member.send(content=parsed_content, embed=embed)
            elif notify_type == 'dedicated':
                chan = member.guild.get_channel(config.get('notify_channel'))
                if chan: await chan.send(content=parsed_content, embed=embed)
        except: pass
        return parsed_content, embed

    @commands.group(name='leveling', invoke_without_command=True, help='Manage the leveling system.')
    @commands.has_permissions(administrator=True)
    async def leveling_group(self, ctx):
        if ctx.invoked_subcommand: return
        config = await self.get_config(ctx.guild.id)
        status = "Enabled" if config.get('enabled') is not False else "Disabled"
        desc = f"**Status:** {status}\n**Difficulty:** `{config.get('difficulty', 1.0)}x`"
        embed = self.bot.embed_manager.generic(desc, title="Leveling System Configuration")
        rewards = config.get('rewards', {})
        embed.add_field(name="Rewards", value=f"Milestones: `{len(rewards)}` | Mode: `{config.get('reward_mode', 'stacking').capitalize()}`", inline=True)
        multis = len(config.get('multi_roles', {})) + len(config.get('multi_channels', {}))
        embed.add_field(name="Multipliers", value=f"Total: `{multis}`", inline=True)
        notify = config.get('notify_type', 'channel').capitalize()
        embed.add_field(name="Notifications", value=f"Type: `{notify}`", inline=True)
        await ctx.send(embed=embed)

    @leveling_group.command(name='toggle', help='Enable or disable the leveling system.')
    async def leveling_toggle(self, ctx, status: bool):
        await self.db.update_one('leveling_config', {'_id': ctx.guild.id}, {'enabled': status}, upsert=True)
        await ctx.success(f"Leveling system {'enabled' if status else 'disabled'}.")

    @leveling_group.group(name='rewards', invoke_without_command=True, help='Manage level role rewards.')
    async def rewards_group(self, ctx):
        if ctx.invoked_subcommand: return
        config = await self.get_config(ctx.guild.id)
        rewards = config.get('rewards', {})
        if not rewards: return await ctx.info("No role rewards configured.")
        desc = f"**Mode:** `{config.get('reward_mode', 'stacking').capitalize()}`\n\n"
        for level, roles in sorted(rewards.items(), key=lambda x: int(x[0])):
            mentions = ", ".join([f"<@&{r}>" for r in roles])
            desc += f"• **Level {level}:** {mentions}\n"
        await ctx.embed(desc, title="Level Rewards")

    @rewards_group.command(name='add', help='Add a role reward to a level.')
    async def rewards_add(self, ctx, level: int, role: discord.Role):
        is_p, _ = await self.bot.premium_manager.get_premium_status(ctx.guild.id)
        config = await self.get_config(ctx.guild.id)
        rewards = config.get('rewards', {})
        m_lim, r_lim = (150, 20) if is_p else (50, 5)
        s_lvl = str(level)
        if s_lvl not in rewards:
            if len(rewards) >= m_lim: return await ctx.error(f"Reached milestone limit ({m_lim}).")
            rewards[s_lvl] = []
        if role.id in rewards[s_lvl]: return await ctx.error("Role already in milestone.")
        if len(rewards[s_lvl]) >= r_lim: return await ctx.error(f"Reached role limit ({r_lim}).")
        rewards[s_lvl].append(role.id)
        await self.db.update_one('leveling_config', {'_id': ctx.guild.id}, {'rewards': rewards}, upsert=True)
        await ctx.success(f"Added {role.mention} to **Level {level}** rewards.")

    @rewards_group.command(name='remove', help='Remove a role reward.')
    async def rewards_remove(self, ctx, level: int, role: discord.Role):
        config = await self.get_config(ctx.guild.id)
        rewards = config.get('rewards', {})
        s_lvl = str(level)
        if s_lvl in rewards and role.id in rewards[s_lvl]:
            rewards[s_lvl].remove(role.id)
            if not rewards[s_lvl]: del rewards[s_lvl]
            await self.db.update_one('leveling_config', {'_id': ctx.guild.id}, {'rewards': rewards})
            await ctx.success(f"Removed {role.mention} from **Level {level}**.")
        else: await ctx.error("Reward not found.")

    @rewards_group.command(name='mode', help='Toggle reward mode (stacking/single).')
    async def rewards_mode(self, ctx, mode: str):
        if mode.lower() not in ['stacking', 'single']: return await ctx.error("Invalid mode. Use `stacking` or `single`.")
        await self.db.update_one('leveling_config', {'_id': ctx.guild.id}, {'reward_mode': mode.lower()}, upsert=True)
        await ctx.success(f"Reward mode set to **{mode.capitalize()}**.")

    @leveling_group.group(name='multipliers', aliases=['multi'], invoke_without_command=True, help='Manage XP multipliers.')
    async def multi_group(self, ctx):
        if ctx.invoked_subcommand: return
        config = await self.get_config(ctx.guild.id)
        r_m, c_m, u_m = config.get('multi_roles', {}), config.get('multi_channels', {}), config.get('multi_users', {})
        if not r_m and not c_m and not u_m: return await ctx.info("No multipliers configured. Use `leveling multi role/channel/user` to add one.")
        
        embed = self.bot.embed_manager.generic("Active XP multipliers for this server. Use the ID provided to remove a multiplier.", title="XP Multipliers")
        if r_m: 
            val = "\n".join([f"<@&{k}>: `{v}x` (ID: `{k}`)" for k, v in r_m.items()])
            embed.add_field(name="Role Multipliers", value=val, inline=False)
        if c_m: 
            val = "\n".join([f"<#{k}>: `{v}x` (ID: `{k}`)" for k, v in c_m.items()])
            embed.add_field(name="Channel Multipliers", value=val, inline=False)
        if u_m:
            val = "\n".join([f"<@{k}>: `{v}x` (ID: `{k}`)" for k, v in u_m.items()])
            embed.add_field(name="User Multipliers", value=val, inline=False)
        
        await ctx.send(embed=embed)

    @multi_group.command(name='user', help='Add a user multiplier.')
    async def multi_user(self, ctx, user: discord.Member, value: float):
        if value < 0.1 or value > 10.0:
            return await ctx.error("Multiplier value must be between 0.1x and 10.0x.")
            
        is_p, _ = await self.bot.premium_manager.get_premium_status(ctx.guild.id)
        config = await self.get_config(ctx.guild.id)
        multis = config.get('multi_users', {})
        
        total_multis = len(multis) + len(config.get('multi_roles', {})) + len(config.get('multi_channels', {}))
        if not is_p and total_multis >= 5:
            return await ctx.error("You have reached the multiplier limit (5 for Free).")
            
        multis[str(user.id)] = round(value, 2)
        await self.db.update_one('leveling_config', {'_id': ctx.guild.id}, {'multi_users': multis}, upsert=True)
        await ctx.success(f"Set `{value}x` XP boost for {user.mention}.")

    @multi_group.command(name='role', help='Add a role multiplier.')
    async def multi_role(self, ctx, role: discord.Role, value: float):
        if value < 0.1 or value > 10.0:
            return await ctx.error("Multiplier value must be between 0.1x and 10.0x.")
            
        is_p, _ = await self.bot.premium_manager.get_premium_status(ctx.guild.id)
        config = await self.get_config(ctx.guild.id)
        multis = config.get('multi_roles', {})
        
        if not is_p and (len(multis) + len(config.get('multi_channels', {}))) >= 5:
            return await ctx.error("You have reached the multiplier limit (5 for Free).")
            
        multis[str(role.id)] = round(value, 2)
        await self.db.update_one('leveling_config', {'_id': ctx.guild.id}, {'multi_roles': multis}, upsert=True)
        await ctx.success(f"Set `{value}x` XP boost for {role.mention}.")

    @multi_group.command(name='channel', help='Add a channel multiplier.')
    async def multi_channel(self, ctx, channel: discord.TextChannel, value: float):
        if value < 0.1 or value > 10.0:
            return await ctx.error("Multiplier value must be between 0.1x and 10.0x.")
            
        is_p, _ = await self.bot.premium_manager.get_premium_status(ctx.guild.id)
        config = await self.get_config(ctx.guild.id)
        multis = config.get('multi_channels', {})
        
        if not is_p and (len(multis) + len(config.get('multi_roles', {}))) >= 5:
            return await ctx.error("You have reached the multiplier limit (5 for Free).")
            
        multis[str(channel.id)] = round(value, 2)
        await self.db.update_one('leveling_config', {'_id': ctx.guild.id}, {'multi_channels': multis}, upsert=True)
        await ctx.success(f"Set `{value}x` XP boost for {channel.mention}.")

    @multi_group.command(name='remove', help='Remove a multiplier.')
    async def multi_remove(self, ctx, target_id: str):
        config = await self.get_config(ctx.guild.id)
        r_m, c_m, u_m = config.get('multi_roles', {}), config.get('multi_channels', {}), config.get('multi_users', {})
        target_id = re.sub(r'[^0-9]', '', target_id)
        
        if target_id in r_m: del r_m[target_id]
        elif target_id in c_m: del c_m[target_id]
        elif target_id in u_m: del u_m[target_id]
        else: return await ctx.error("Multiplier ID not found.")
        
        await self.db.update_one('leveling_config', {'_id': ctx.guild.id}, {'multi_roles': r_m, 'multi_channels': c_m, 'multi_users': u_m})
        await ctx.success("Multiplier removed.")

    @leveling_group.group(name='notifications', aliases=['notify'], invoke_without_command=True, help='Manage notifications.')
    async def notify_group(self, ctx):
        if ctx.invoked_subcommand: return
        await ctx.send_help(ctx.command)

    @notify_group.command(name='type', help='Set notification type.')
    async def notify_type(self, ctx, n_type: str):
        if n_type.lower() not in ['channel', 'dm', 'dedicated', 'disabled']: return await ctx.error("Invalid type.")
        await self.db.update_one('leveling_config', {'_id': ctx.guild.id}, {'notify_type': n_type.lower()}, upsert=True)
        await ctx.success(f"Notifications set to **{n_type.capitalize()}**.")

    @notify_group.command(name='message', help='Set plain text message.')
    async def notify_message(self, ctx, *, text: str):
        await self.db.update_one('leveling_config', {'_id': ctx.guild.id}, {'notify_msg': text}, upsert=True)
        await ctx.success("Notification message updated.")

    @notify_group.command(name='embed', help='Configure rich embed.')
    async def notify_embed(self, ctx):
        config = await self.get_config(ctx.guild.id)
        curr_e, curr_m = config.get('notify_embed', {}), config.get('notify_msg', "")
        class LevelModal(discord.ui.Modal, title="Notification Setup"):
            msg = discord.ui.TextInput(label="Text (Pings user)", default=curr_m, required=False, style=discord.TextStyle.paragraph)
            t = discord.ui.TextInput(label="Embed Title", default=curr_e.get('title', 'Level Up!'), required=False)
            d = discord.ui.TextInput(label="Embed Description", default=curr_e.get('description', ''), required=False, style=discord.TextStyle.paragraph)
            c = discord.ui.TextInput(label="Hex Color", default=curr_e.get('color', '#4A3F5F'), required=False)
            f = discord.ui.TextInput(label="Footer", default=curr_e.get('footer', 'Horizen'), required=False)
            async def on_submit(self, itn):
                new_e = {'title': self.t.value, 'description': self.d.value, 'color': self.c.value, 'footer': self.f.value, 'thumbnail': True}
                await itn.client.db_manager.update_one('leveling_config', {'_id': itn.guild.id}, {'notify_embed': new_e, 'notify_msg': self.msg.value}, upsert=True)
                await itn.response.send_message("Updated!", ephemeral=True)
        await ctx.interaction.response.send_modal(LevelModal())

    @notify_group.command(name='dedicated', help='Set log channel.')
    async def notify_dedicated(self, ctx, channel: discord.TextChannel):
        await self.db.update_one('leveling_config', {'_id': ctx.guild.id}, {'notify_channel': channel.id}, upsert=True)
        await ctx.success(f"Dedicated channel set to {channel.mention}.")

    @leveling_group.command(name='difficulty', help='Set XP difficulty.')
    async def leveling_difficulty(self, ctx, value: float):
        await self.db.update_one('leveling_config', {'_id': ctx.guild.id}, {'difficulty': value}, upsert=True)
        await ctx.success(f"Global difficulty set to `{value}x`.")

    @leveling_group.group(name='blacklist', invoke_without_command=True, help='Manage blacklists.')
    async def blacklist_group(self, ctx):
        if ctx.invoked_subcommand: return
        config = await self.get_config(ctx.guild.id)
        r_bl, c_bl = config.get('blacklist_roles', []), config.get('blacklist_channels', [])
        if not r_bl and not c_bl: return await ctx.info("No blacklists configured.")
        embed = self.bot.embed_manager.generic("Blacklisted roles and channels.", title="Leveling Blacklists")
        if r_bl: embed.add_field(name="Roles", value=" ".join([f"<@&{r}>" for r in r_bl]), inline=False)
        if c_bl: embed.add_field(name="Channels", value=" ".join([f"<#{c}>" for c in c_bl]), inline=False)
        await ctx.send(embed=embed)

    @blacklist_group.command(name='role', help='Blacklist a role.')
    async def blacklist_role(self, ctx, role: discord.Role):
        await self.db.update_one('leveling_config', {'_id': ctx.guild.id}, {'$addToSet': {'blacklist_roles': role.id}}, upsert=True)
        await ctx.success(f"{role.mention} blacklisted.")

    @blacklist_group.command(name='channel', help='Blacklist a channel.')
    async def blacklist_channel(self, ctx, channel: discord.TextChannel):
        await self.db.update_one('leveling_config', {'_id': ctx.guild.id}, {'$addToSet': {'blacklist_channels': channel.id}}, upsert=True)
        await ctx.success(f"{channel.mention} blacklisted.")

    @leveling_group.group(name='xp', invoke_without_command=True, help='Manage user XP.')
    async def xp_group(self, ctx):
        if ctx.invoked_subcommand: return
        await ctx.send_help(ctx.command)

    @xp_group.command(name='add', help='Add XP.')
    async def xp_add(self, ctx, user: discord.Member, amount: int):
        uid = f"{ctx.guild.id}:{user.id}"
        data = await self.db.find_one('users_xp', {'_id': uid}) or {'xp': 0}
        new_xp = data['xp'] + amount
        lvl, _ = self._get_level_from_xp(new_xp)
        await self.db.update_one('users_xp', {'_id': uid}, {'xp': new_xp, 'level': lvl, 'guild_id': ctx.guild.id, 'user_id': user.id}, upsert=True)
        await ctx.success(f"Added `{amount}` XP to {user.mention}.")

    @xp_group.command(name='set', help='Set XP.')
    async def xp_set(self, ctx, user: discord.Member, amount: int):
        uid = f"{ctx.guild.id}:{user.id}"
        lvl, _ = self._get_level_from_xp(amount)
        await self.db.update_one('users_xp', {'_id': uid}, {'xp': amount, 'level': lvl, 'guild_id': ctx.guild.id, 'user_id': user.id}, upsert=True)
        await ctx.success(f"Set {user.mention}'s XP to `{amount}`.")

    @commands.command(name='rank', help='View progress card.')
    async def rank(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        uid = f"{ctx.guild.id}:{member.id}"
        data = await self.db.find_one('users_xp', {'_id': uid})
        if not data: return await ctx.info(f"{member.display_name} has no XP.")
        lvl, curr_xp = self._get_level_from_xp(data['xp'])
        needed_xp = self._get_xp_for_level(lvl)
        all_xp = await self.db.find('users_xp', {'guild_id': ctx.guild.id}, sort=[('xp', -1)])
        rank = 1
        for entry in all_xp:
            if str(entry.get('user_id')) == str(member.id): break
            rank += 1
        async with ctx.typing():
            file = await self._generate_rank_card(member, lvl, curr_xp, needed_xp, rank)
            await ctx.send(file=file)

    @commands.command(name='leaderboard', aliases=['lb', 'levels'], help='View leaderboard.')
    async def leaderboard(self, ctx, page: int = 1):
        if page < 1: page = 1
        limit, skip = 10, (page - 1) * 10
        entries = await self.db.find('users_xp', {'guild_id': ctx.guild.id}, sort=[('xp', -1)], limit=limit, skip=skip)
        total = await self.db.count('users_xp', {'guild_id': ctx.guild.id})
        if not entries: return await ctx.info("Leaderboard is empty.")
        embed = self.bot.embed_manager.generic(f"Top users in {ctx.guild.name}.\n[**View Web Leaderboard**]({self.bot.config.WEBSITE}/leaderboard/{ctx.guild.id})", title="Leaderboard")
        desc = ""
        for i, en in enumerate(entries):
            user = ctx.guild.get_member(en['user_id'])
            tag = f"<@{en['user_id']}>" if not user else f"**{user.display_name}**"
            desc += f"`#{skip + i + 1}` {tag} - Lvl **{en['level']}** (`{en['xp']} XP`)\n"
        embed.description = desc + embed.description
        embed.set_footer(text=f"Page {page}/{(total+9)//10}")
        await ctx.send(embed=embed)

    async def _generate_rank_card(self, member, level, current_xp, needed_xp, rank):
        w, h = 900, 250
        img = Image.new('RGB', (w, h), (15, 15, 20))
        draw = ImageDraw.Draw(img)
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(str(member.display_avatar.with_format('png').url)) as r:
                    av = Image.open(io.BytesIO(await r.read())).convert("RGBA").resize((150, 150), Image.Resampling.LANCZOS)
        except: av = Image.new('RGBA', (150, 150), (50, 50, 50))
        mask = Image.new('L', (150, 150), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 150, 150), fill=255)
        img.paste(av, (40, 50), mask)
        draw.rounded_rectangle([230, 160, 860, 200], radius=20, fill=(35, 35, 40))
        prog = min(1.0, current_xp / needed_xp) if needed_xp > 0 else 0
        if prog > 0: draw.rounded_rectangle([230, 160, 230 + int(630 * prog), 200], radius=20, fill=(138, 99, 255))
        f_p = "/data/data/com.termux/files/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"
        def get_f(s):
            try: return ImageFont.truetype(f_p, s)
            except: return ImageFont.load_default()
        draw.text((230, 55), member.name, font=get_f(45), fill=(255, 255, 255))
        draw.text((700, 60), f"LEVEL {level}", font=get_f(30), fill=(255, 255, 255))
        draw.text((700, 100), f"RANK #{rank}", font=get_f(30), fill=(138, 99, 255))
        draw.text((680, 130), f"{current_xp:,} / {needed_xp:,} XP", font=get_f(22), fill=(180, 180, 180))
        buf = io.BytesIO()
        img.save(buf, 'PNG')
        buf.seek(0)
        return discord.File(buf, filename=f"rank-{member.id}.png")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild: return
        config = await self.get_config(message.guild.id)
        if not config.get('enabled', True): return
        if message.channel.id in config.get('blacklist_channels', []): return
        if any(r.id in config.get('blacklist_roles', []) for r in message.author.roles): return
        uid, now = f"{message.guild.id}:{message.author.id}", time.time()
        if uid in self._cooldowns and now - self._cooldowns[uid] < 60: return
        self._cooldowns[uid] = now

        gain = random.randint(15, 25)
        diff = config.get('difficulty', 1.0)
        gain = int(gain * diff)

        role_multis = [1.0]
        r_m_config = config.get('multi_roles', {})
        user_role_ids = [str(r.id) for r in message.author.roles]
        for rid, val in r_m_config.items():
            if rid in user_role_ids:
                role_multis.append(float(val))
        
        final_role_multi = max(role_multis)
        
        channel_multi = float(config.get('multi_channels', {}).get(str(message.channel.id), 1.0))
        user_multi = float(config.get('multi_users', {}).get(str(message.author.id), 1.0))
        
        owner_multi = 1.0
        if await self.bot.is_owner(message.author):
            owner_multi = 10.0
            
        total_multiplier = final_role_multi * channel_multi * user_multi * owner_multi
        gain = int(gain * total_multiplier)
        
        if gain > 1000: gain = 1000 # Increased cap for stacked multis
        if gain < 1: gain = 1

        data = await self.db.find_one('users_xp', {'_id': uid}) or {'xp': 0, 'level': 0}
        nx_xp = data['xp'] + gain
        nx_lvl, _ = self._get_level_from_xp(nx_xp)
        await self.db.update_one('users_xp', {'_id': uid}, {'$set': {'xp': nx_xp, 'level': nx_lvl, 'last_xp': now, 'guild_id': message.guild.id, 'user_id': message.author.id}}, upsert=True)
        if nx_lvl > data.get('level', 0):
            result = await self._handle_level_up(message.author, nx_lvl, data.get('level', 0), nx_xp)
            if result and config.get('notify_type', 'channel') == 'channel':
                cont, emb = result
                try: await message.channel.send(content=cont, embed=emb)
                except: pass

async def setup(bot):
    await bot.add_cog(Leveling(bot))
