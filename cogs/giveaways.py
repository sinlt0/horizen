import discord
from discord.ext import commands, tasks
import asyncio
import random
import time
import datetime
import re

class GiveawayView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Enter Giveaway", style=discord.ButtonStyle.blurple, custom_id="gw_enter")
    async def enter_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        gw = await self.bot.db_manager.find_one('giveaways', {'_id': interaction.message.id, 'active': True})
        if not gw:
            return await interaction.response.send_message("This giveaway has ended.", ephemeral=True)

        req_roles = gw.get('required_roles', [])
        if req_roles:
            if not any(role.id in req_roles for role in interaction.user.roles):
                required_role_mentions = ", ".join([f"<@&{r_id}>" for r_id in req_roles])
                return await interaction.response.send_message(f"You don't have the required roles to join: {required_role_mentions}", ephemeral=True)

        if interaction.user.id in gw.get('entries', []):
            return await interaction.response.send_message("You have already entered this giveaway!", ephemeral=True)

        await self.bot.db_manager.update_one('giveaways', {'_id': interaction.message.id}, {'$addToSet': {'entries': interaction.user.id}}, upsert=True)
        
        bonus_roles = gw.get('bonus_roles', {})
        multiplier = 1
        for r_id, mult in bonus_roles.items():
            if any(role.id == int(r_id) for role in interaction.user.roles):
                multiplier = max(multiplier, mult)
        
        msg = "You have successfully entered the giveaway!"
        if multiplier > 1:
            msg += f" (Bonus: **{multiplier}x** entries applied)"
            
        await interaction.response.send_message(msg, ephemeral=True)

class Giveaways(commands.Cog):
    category = 'utility'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager
        self.giveaway_check_loop.start()

    async def cog_load(self):
        self.bot.add_view(GiveawayView(self.bot))

    def cog_unload(self):
        self.giveaway_check_loop.cancel()

    @giveaway_check_loop.before_loop
    async def before_giveaway_check(self):
        await self.bot.wait_until_ready()

    async def _resolve_time(self, time_str):
        match = re.match(r"(\d+)([smhd])", time_str.lower())
        if not match: return None
        amount = int(match.group(1))
        unit = match.group(2)
        if unit == 's': return amount
        if unit == 'm': return amount * 60
        if unit == 'h': return amount * 3600
        if unit == 'd': return amount * 86400
        return None

    @tasks.loop(seconds=10)
    async def giveaway_check_loop(self):
        now = int(time.time())
        active_giveaways = await self.db.find('giveaways', {'active': True})
        
        for gw in active_giveaways:
            if gw['end_at'] <= now:
                await self._end_giveaway(gw)

    async def _end_giveaway(self, gw_data):
        guild = self.bot.get_guild(gw_data['guild_id'])
        if not guild: return
        
        channel = guild.get_channel(gw_data['channel_id'])
        if not channel: return
        
        try:
            message = await channel.fetch_message(gw_data['_id'])
        except: 
            await self.db.update_one('giveaways', {'_id': gw_data['_id']}, {'active': False}, upsert=True)
            return

        entries = gw_data.get('entries', [])
        winners = []
        
        if len(entries) > 0:
            winner_count = min(len(set(entries)), gw_data['winner_count'])
            bonus_roles = gw_data.get('bonus_roles', {})
            
            final_pool = []
            for uid in entries:
                member = guild.get_member(uid)
                mult = 1
                if member:
                    for r_id, m in bonus_roles.items():
                        if any(role.id == int(r_id) for role in member.roles):
                            mult = max(mult, m)
                final_pool.extend([uid] * mult)
            
            while len(winners) < winner_count and final_pool:
                w = random.choice(final_pool)
                winners.append(w)
                final_pool = [u for u in final_pool if u != w]
        
        winners_mentions = ", ".join([f"<@{w_id}>" for w_id in winners])
        
        embed = message.embeds[0]
        embed.color = discord.Color.red()
        embed.description = f"**Prize:** {gw_data['prize']}\n**Winners:** {winners_mentions if winners else 'None'}"
        
        req_info = ""
        if gw_data.get('required_roles'):
            req_info = "\n**Requirements:** " + ", ".join([f"<@&{r_id}>" for r_id in gw_data['required_roles']])
        
        embed.description += req_info
        embed.set_footer(text=f"Ended at • {datetime.datetime.fromtimestamp(gw_data['end_at']).strftime('%Y-%m-%d %H:%M')}")
        
        await message.edit(embed=embed, view=None)
        
        if winners:
            announcement = f"{self.bot.e.giveaway} Congratulations {winners_mentions}! You won **{gw_data['prize']}**!"
            await channel.send(announcement)
            for w_id in winners:
                try:
                    user = await self.bot.fetch_user(w_id)
                    await user.send(embed=self.bot.embed_manager.success(f"You won **{gw_data['prize']}** in **{guild.name}**!", title="Giveaway Winner!"))
                except: pass
        else:
            await channel.send(f"{self.bot.e.giveaway} No one entered the giveaway for **{gw_data['prize']}**.")

        log_cog = self.bot.get_cog('Logging')
        if log_cog:
            log_embed = discord.Embed(
                title="Giveaway Ended", 
                description=f"**Prize:** {gw_data['prize']}\n**Winners:** {winners_mentions if winners else 'None'}", 
                color=discord.Color.red(), 
                timestamp=discord.utils.utcnow()
            )
            await log_cog.log_giveaways(guild, log_embed)

        await self.db.update_one('giveaways', {'_id': gw_data['_id']}, {'active': False, 'winners': winners}, upsert=True)

    @commands.group(name='gw', aliases=['giveaway'], invoke_without_command=True, help='Giveaway management commands.')
    async def gw_group(self, ctx):
        await ctx.send_help(ctx.command)

    @gw_group.command(name='start', help='Start a giveaway. Flags: --req @Role, --bonus @Role:multiplier')
    @commands.has_permissions(manage_guild=True)
    async def gw_start(self, ctx, duration: str, winners: int, *, args: str):
        prize = args
        req_roles = []
        bonus_roles = {}

        req_matches = re.findall(r"--req\s+<@&?(\d+)>", args)
        for r_id in req_matches:
            req_roles.append(int(r_id))
            prize = prize.replace(f"--req <@&{r_id}>", "").replace(f"--req <@!{r_id}>", "").replace(f"--req <@{r_id}>", "")

        bonus_matches = re.findall(r"--bonus\s+<@&?(\d+)>:(\d+)", args)
        for r_id, mult in bonus_matches:
            bonus_roles[r_id] = int(mult)
            prize = prize.replace(f"--bonus <@&{r_id}>:{mult}", "").replace(f"--bonus <@!{r_id}>:{mult}", "").replace(f"--bonus <@{r_id}>:{mult}", "")

        prize = prize.strip()
        if not prize: return await ctx.error("You must provide a prize!")

        seconds = await self._resolve_time(duration)
        if not seconds: return await ctx.error("Invalid duration format! Use `10s`, `5m`, `1h`, etc.")
        if winners < 1: return await ctx.error("Winner count must be at least 1.")

        end_at = int(time.time()) + seconds
        
        desc = (
            f"Click the button below to enter!\n\n"
            f"**Prize:** {prize}\n"
            f"**Ends:** <t:{end_at}:R> (<t:{end_at}:f>)\n"
            f"**Winners:** {winners}"
        )

        if req_roles:
            desc += "\n**Requirements:** " + ", ".join([f"<@&{r_id}>" for r_id in req_roles])
        
        if bonus_roles:
            desc += "\n**Bonus Entries:** " + ", ".join([f"<@&{r_id}> (**{m}x**)" for r_id, m in bonus_roles.items()])

        embed = self.bot.embed_manager.generic(
            description=desc,
            title=f"{self.bot.e.giveaway} Giveaway Start"
        )
        embed.set_footer(text="Good luck!")
        
        view = GiveawayView(self.bot)
        msg = await ctx.send(embed=embed, view=view)
        
        gw_data = {
            '_id': msg.id,
            'guild_id': ctx.guild.id,
            'channel_id': ctx.channel.id,
            'prize': prize,
            'winner_count': winners,
            'end_at': end_at,
            'entries': [],
            'active': True,
            'winners': [],
            'required_roles': req_roles,
            'bonus_roles': bonus_roles
        }
        await self.db.update_one('giveaways', {'_id': msg.id}, gw_data, upsert=True)

        log_cog = self.bot.get_cog('Logging')
        if log_cog:
            log_embed = discord.Embed(title="Giveaway Started", description=f"**Prize:** {prize}\n**Channel:** {ctx.channel.mention}\n**Winners:** {winners}\n**Ends:** <t:{end_at}:R>", color=discord.Color.green(), timestamp=discord.utils.utcnow())
            await log_cog.log_giveaways(ctx.guild, log_embed)

    @gw_group.command(name='reroll', help='Reroll a finished giveaway.')
    @commands.has_permissions(manage_guild=True)
    async def gw_reroll(self, ctx, message_id: int):
        gw = await self.db.find_one('giveaways', {'_id': message_id})
        if not gw: return await ctx.error("Giveaway not found.")
        if gw['active']: return await ctx.error("That giveaway is still running!")

        entries = gw.get('entries', [])
        if not entries: return await ctx.error("No entries found for this giveaway.")
        
        winner = random.choice(entries)
        await ctx.success(f"New winner for **{gw['prize']}**: <@{winner}>!")

    @gw_group.command(name='end', help='End an active giveaway early.')
    @commands.has_permissions(manage_guild=True)
    async def gw_end(self, ctx, message_id: int):
        gw = await self.db.find_one('giveaways', {'_id': message_id})
        if not gw: return await ctx.error("Giveaway not found.")
        if not gw['active']: return await ctx.error("Giveaway is already finished.")
        
        gw['end_at'] = int(time.time())
        await self._end_giveaway(gw)
        await ctx.success("Giveaway ended early.")

    @gw_group.command(name='list', help='List all active giveaways.')
    async def gw_list(self, ctx):
        active = await self.db.find('giveaways', {'guild_id': ctx.guild.id, 'active': True})
        if not active: return await ctx.info("No active giveaways in this server.")
        
        desc = "\n".join([f"• **{g['prize']}** - <t:{g['end_at']}:R> (ID: `{g['_id']}`)" for g in active])
        await ctx.embed(desc, title=f"Active Giveaways ({len(active)})")

async def setup(bot):
    await bot.add_cog(Giveaways(bot))
