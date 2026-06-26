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

    @discord.ui.button(label="Enter Giveaway", style=discord.ButtonStyle.blurple, emoji="🎉", custom_id="gw_enter")
    async def enter_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        gw = await self.bot.db_manager.find_one('giveaways', {'_id': interaction.message.id, 'active': True})
        if not gw:
            return await interaction.response.send_message("This giveaway has ended.", ephemeral=True)

        req_roles = gw.get('required_roles', [])
        if req_roles:
            if not any(role.id in req_roles for role in interaction.user.roles):
                mentions = ", ".join([f"<@&{r}>" for r in req_roles])
                return await interaction.response.send_message(f"You need one of these roles to enter: {mentions}", ephemeral=True)

        entries = gw.get('entries', [])
        if interaction.user.id in entries:
            return await interaction.response.send_message("You have already entered this giveaway!", ephemeral=True)

        await self.bot.db_manager.update_one('giveaways', {'_id': interaction.message.id}, {'$addToSet': {'entries': interaction.user.id}}, upsert=True)

        bonus_roles = gw.get('bonus_roles', {})
        multiplier = 1
        for r_id, mult in bonus_roles.items():
            if any(role.id == int(r_id) for role in interaction.user.roles):
                multiplier = max(multiplier, mult)

        total = len(entries) + 1
        msg = f"🎉 You're in! **{total}** {'entry' if total == 1 else 'entries'} so far."
        if multiplier > 1:
            msg += f"\n✨ Your **{multiplier}x** bonus applies when winners are drawn."

        await interaction.response.send_message(msg, ephemeral=True)

class GiveawayEndView(discord.ui.View):
    def __init__(self, bot, gw_id, guild_id, channel_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.gw_id = gw_id
        self.guild_id = guild_id
        self.channel_id = channel_id

    @discord.ui.button(label="Reroll Winner", style=discord.ButtonStyle.secondary, emoji="🔄", custom_id="gw_reroll_btn")
    async def reroll_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("You need `Manage Server` to reroll.", ephemeral=True)

        gw = await self.bot.db_manager.find_one('giveaways', {'_id': self.gw_id})
        if not gw or gw.get('active'):
            return await interaction.response.send_message("Giveaway data not found or still active.", ephemeral=True)

        entries = gw.get('entries', [])
        if not entries:
            return await interaction.response.send_message("No entries to reroll from.", ephemeral=True)

        winner = random.choice(entries)
        await interaction.response.send_message(f"🔄 Rerolled! New winner: <@{winner}>! Congratulations!", ephemeral=False)

class Giveaways(commands.Cog):
    category = 'utility'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager
        self._ending = set()

    async def cog_load(self):
        self.bot.add_view(GiveawayView(self.bot))
        self.giveaway_check_loop.start()

    def cog_unload(self):
        self.giveaway_check_loop.cancel()

    @tasks.loop(seconds=10)
    async def giveaway_check_loop(self):
        now = int(time.time())
        active = await self.db.find('giveaways', {'active': True})
        for gw in active:
            if gw['end_at'] <= now and gw['_id'] not in self._ending:
                self._ending.add(gw['_id'])
                self.bot.loop.create_task(self._safe_end(gw))

    @giveaway_check_loop.before_loop
    async def before_giveaway_check_loop(self):
        await self.bot.wait_until_ready()

    async def _safe_end(self, gw_data):
        try:
            await self._end_giveaway(gw_data)
        except Exception as e:
            print(f"Giveaways: Error ending giveaway {gw_data['_id']}: {e}")
        finally:
            self._ending.discard(gw_data['_id'])

    def _resolve_time(self, time_str):
        match = re.match(r"(\d+)([smhd])", time_str.lower())
        if not match:
            return None
        amount = int(match.group(1))
        unit = match.group(2)
        multipliers = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
        return amount * multipliers[unit]

    def _build_pool(self, entries, bonus_roles, guild):
        pool = []
        for uid in entries:
            member = guild.get_member(uid)
            mult = 1
            if member:
                for r_id, m in bonus_roles.items():
                    if any(role.id == int(r_id) for role in member.roles):
                        mult = max(mult, m)
            pool.extend([uid] * mult)
        return pool

    def _pick_winners(self, pool, count):
        winners = []
        pool = list(pool)
        while len(winners) < count and pool:
            w = random.choice(pool)
            winners.append(w)
            pool = [u for u in pool if u != w]
        return winners

    async def _end_giveaway(self, gw_data):
        guild = self.bot.get_guild(gw_data['guild_id'])
        if not guild:
            await self.db.update_one('giveaways', {'_id': gw_data['_id']}, {'active': False})
            return

        channel = guild.get_channel(gw_data['channel_id'])
        if not channel:
            await self.db.update_one('giveaways', {'_id': gw_data['_id']}, {'active': False})
            return

        try:
            message = await channel.fetch_message(gw_data['_id'])
        except (discord.NotFound, discord.Forbidden):
            await self.db.update_one('giveaways', {'_id': gw_data['_id']}, {'active': False})
            return

        entries = list(set(gw_data.get('entries', [])))
        bonus_roles = gw_data.get('bonus_roles', {})
        winner_count = min(len(entries), gw_data['winner_count'])

        pool = self._build_pool(entries, bonus_roles, guild)
        winners = self._pick_winners(pool, winner_count)
        winners_mentions = ", ".join([f"<@{w}>" for w in winners])

        embed = discord.Embed(
            title=f"🎉 Giveaway Ended — {gw_data['prize']}",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        embed.description = f"**Prize:** {gw_data['prize']}\n**Winners:** {winners_mentions if winners else 'No winners'}"
        if gw_data.get('required_roles'):
            embed.description += "\n**Requirements:** " + ", ".join([f"<@&{r}>" for r in gw_data['required_roles']])
        embed.add_field(name="Total Entries", value=f"`{len(entries)}`", inline=True)
        embed.add_field(name="Ended", value=f"<t:{gw_data['end_at']}:R>", inline=True)
        embed.set_footer(text=f"Giveaway ID: {gw_data['_id']}")

        end_view = GiveawayEndView(self.bot, gw_data['_id'], guild.id, channel.id)

        try:
            await message.edit(embed=embed, view=end_view)
        except Exception:
            pass

        if winners:
            await channel.send(
                f"🎉 Congratulations {winners_mentions}! You won **{gw_data['prize']}**!",
                reference=message
            )
            for w_id in winners:
                try:
                    user = await self.bot.fetch_user(w_id)
                    await user.send(embed=self.bot.embed_manager.success(
                        f"You won **{gw_data['prize']}** in **{guild.name}**!\n[Jump to giveaway]({message.jump_url})",
                        title="🎉 You Won!"
                    ))
                except Exception:
                    pass
        else:
            await channel.send(
                f"😔 No one entered the giveaway for **{gw_data['prize']}**.",
                reference=message
            )

        log_cog = self.bot.get_cog('Logging')
        if log_cog:
            log_embed = discord.Embed(
                title="Giveaway Ended",
                description=f"**Prize:** {gw_data['prize']}\n**Winners:** {winners_mentions if winners else 'None'}\n**Entries:** `{len(entries)}`",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
            await log_cog.log_giveaways(guild, log_embed)

        await self.db.update_one('giveaways', {'_id': gw_data['_id']}, {'active': False, 'winners': winners})

    @commands.group(name='gw', aliases=['giveaway'], invoke_without_command=True, help='Giveaway management commands.')
    async def gw_group(self, ctx):
        config = await self.db.find_one('giveaways', {'guild_id': ctx.guild.id, 'active': True})
        if not config:
            return await ctx.send_help(ctx.command)
        await ctx.invoke(self.gw_list)

    @gw_group.command(name='start', help='Start a giveaway. Flags: --req @Role, --bonus @Role:multiplier, --host @User')
    @commands.has_permissions(manage_guild=True)
    async def gw_start(self, ctx, duration: str, winners: int, *, args: str):
        prize = args
        req_roles = []
        bonus_roles = {}
        host = ctx.author

        host_match = re.search(r"--host\s+<@!?(\d+)>", args)
        if host_match:
            host_id = int(host_match.group(1))
            host = ctx.guild.get_member(host_id) or ctx.author
            prize = re.sub(r"--host\s+<@!?\d+>", "", prize)

        for r_id in re.findall(r"--req\s+<@&?(\d+)>", args):
            req_roles.append(int(r_id))
            prize = re.sub(rf"--req\s+<@&?{r_id}>", "", prize)

        for r_id, mult in re.findall(r"--bonus\s+<@&?(\d+)>:(\d+)", args):
            bonus_roles[r_id] = int(mult)
            prize = re.sub(rf"--bonus\s+<@&?{r_id}>:{mult}", "", prize)

        prize = prize.strip()
        if not prize:
            return await ctx.error("You must provide a prize!")

        seconds = self._resolve_time(duration)
        if not seconds:
            return await ctx.error("Invalid duration. Use `10s`, `5m`, `2h`, `1d`.")
        if winners < 1:
            return await ctx.error("Winner count must be at least 1.")
        if winners > 20:
            return await ctx.error("Winner count cannot exceed 20.")

        end_at = int(time.time()) + seconds

        embed = discord.Embed(
            title=f"🎉 {prize}",
            color=discord.Color.gold(),
            timestamp=datetime.datetime.fromtimestamp(end_at)
        )
        embed.description = (
            f"Click the button to enter!\n\n"
            f"**Ends:** <t:{end_at}:R> (<t:{end_at}:f>)\n"
            f"**Winners:** `{winners}`\n"
            f"**Hosted by:** {host.mention}"
        )
        if req_roles:
            embed.add_field(name="Requirements", value=" ".join([f"<@&{r}>" for r in req_roles]), inline=False)
        if bonus_roles:
            embed.add_field(
                name="Bonus Entries",
                value="\n".join([f"<@&{r}>: **{m}x**" for r, m in bonus_roles.items()]),
                inline=False
            )
        embed.set_footer(text="Ends at")

        view = GiveawayView(self.bot)
        msg = await ctx.send(embed=embed, view=view)

        gw_data = {
            '_id': msg.id,
            'guild_id': ctx.guild.id,
            'channel_id': ctx.channel.id,
            'prize': prize,
            'winner_count': winners,
            'end_at': end_at,
            'host_id': host.id,
            'entries': [],
            'active': True,
            'winners': [],
            'required_roles': req_roles,
            'bonus_roles': bonus_roles
        }
        await self.db.update_one('giveaways', {'_id': msg.id}, gw_data, upsert=True)

        log_cog = self.bot.get_cog('Logging')
        if log_cog:
            log_embed = discord.Embed(
                title="Giveaway Started",
                description=f"**Prize:** {prize}\n**Channel:** {ctx.channel.mention}\n**Winners:** {winners}\n**Host:** {host.mention}\n**Ends:** <t:{end_at}:R>",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )
            await log_cog.log_giveaways(ctx.guild, log_embed)

    @gw_group.command(name='reroll', help='Reroll winners for a finished giveaway.')
    @commands.has_permissions(manage_guild=True)
    async def gw_reroll(self, ctx, message_id: int, count: int = 1):
        gw = await self.db.find_one('giveaways', {'_id': message_id})
        if not gw:
            return await ctx.error("Giveaway not found.")
        if gw['active']:
            return await ctx.error("That giveaway is still running!")
        if count < 1 or count > 20:
            return await ctx.error("Reroll count must be between 1 and 20.")

        entries = list(set(gw.get('entries', [])))
        if not entries:
            return await ctx.error("No entries to reroll from.")

        guild = ctx.guild
        bonus_roles = gw.get('bonus_roles', {})
        pool = self._build_pool(entries, bonus_roles, guild)
        winners = self._pick_winners(pool, min(count, len(entries)))
        mentions = ", ".join([f"<@{w}>" for w in winners])

        await ctx.success(f"🔄 Rerolled **{gw['prize']}**!\nNew winner(s): {mentions}")

    @gw_group.command(name='end', help='End an active giveaway early.')
    @commands.has_permissions(manage_guild=True)
    async def gw_end(self, ctx, message_id: int):
        gw = await self.db.find_one('giveaways', {'_id': message_id})
        if not gw:
            return await ctx.error("Giveaway not found.")
        if not gw['active']:
            return await ctx.error("Giveaway is already finished.")
        if gw['_id'] in self._ending:
            return await ctx.error("This giveaway is already being processed.")

        gw['end_at'] = int(time.time())
        self._ending.add(gw['_id'])
        self.bot.loop.create_task(self._safe_end(gw))
        await ctx.success("Giveaway is being ended now.")

    @gw_group.command(name='cancel', help='Cancel an active giveaway without picking winners.')
    @commands.has_permissions(manage_guild=True)
    async def gw_cancel(self, ctx, message_id: int):
        gw = await self.db.find_one('giveaways', {'_id': message_id})
        if not gw:
            return await ctx.error("Giveaway not found.")
        if not gw['active']:
            return await ctx.error("Giveaway is already finished.")

        await self.db.update_one('giveaways', {'_id': message_id}, {'active': False})

        channel = ctx.guild.get_channel(gw['channel_id'])
        if channel:
            try:
                msg = await channel.fetch_message(message_id)
                embed = msg.embeds[0]
                embed.color = discord.Color.greyple()
                embed.title = f"❌ Cancelled — {gw['prize']}"
                await msg.edit(embed=embed, view=None)
            except Exception:
                pass

        await ctx.success(f"Giveaway for **{gw['prize']}** has been cancelled.")

    @gw_group.command(name='list', help='List all active giveaways in this server.')
    async def gw_list(self, ctx):
        active = await self.db.find('giveaways', {'guild_id': ctx.guild.id, 'active': True})
        if not active:
            return await ctx.info("No active giveaways in this server.")

        embed = self.bot.embed_manager.generic(
            description="\n".join([
                f"• **{g['prize']}** — ends <t:{g['end_at']}:R> | `{len(g.get('entries', []))}` entries | ID: `{g['_id']}`"
                for g in active
            ]),
            title=f"Active Giveaways ({len(active)})"
        )
        await ctx.send(embed=embed)

    @gw_group.command(name='info', help='View detailed information about a giveaway.')
    async def gw_info(self, ctx, message_id: int):
        gw = await self.db.find_one('giveaways', {'_id': message_id})
        if not gw:
            return await ctx.error("Giveaway not found.")

        entries = list(set(gw.get('entries', [])))
        host = ctx.guild.get_member(gw.get('host_id')) or f"<@{gw.get('host_id', 'Unknown')}>"
        status = "🟢 Active" if gw['active'] else "🔴 Ended"

        embed = self.bot.embed_manager.generic(
            description=(
                f"**Prize:** {gw['prize']}\n"
                f"**Status:** {status}\n"
                f"**Host:** {host.mention if isinstance(host, discord.Member) else host}\n"
                f"**Winners:** `{gw['winner_count']}`\n"
                f"**Entries:** `{len(entries)}`\n"
                f"**Ends:** <t:{gw['end_at']}:R>"
            ),
            title=f"Giveaway Info"
        )

        if not gw['active'] and gw.get('winners'):
            embed.add_field(
                name="Winners",
                value=", ".join([f"<@{w}>" for w in gw['winners']]),
                inline=False
            )
        if gw.get('required_roles'):
            embed.add_field(
                name="Requirements",
                value=" ".join([f"<@&{r}>" for r in gw['required_roles']]),
                inline=False
            )

        channel = ctx.guild.get_channel(gw['channel_id'])
        if channel:
            embed.add_field(name="Channel", value=channel.mention, inline=True)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Giveaways(bot))
