import discord
from discord.ext import commands
import random
import asyncio

class Fun2(commands.Cog):
    category = "fun"

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='tictactoe', help='Play a game of Tic Tac Toe.')
    async def tictactoe(self, ctx, member: discord.Member):
        if member.bot: return await ctx.error("You can't play against a bot.")
        if member == ctx.author: return await ctx.error("You can't play against yourself.")
        
        await ctx.info(f"{member.mention}, {ctx.author.mention} has challenged you to Tic Tac Toe! (Game system coming in next update)", title="Tic Tac Toe")

    @commands.command(name='dice2', help='Roll two dice and see the outcome.')
    async def dice_two(self, ctx):
        d1, d2 = random.randint(1, 6), random.randint(1, 6)
        await ctx.embed(f"🎲 Dice 1: **{d1}**\n🎲 Dice 2: **{d2}**\n\nTotal: **{d1+d2}**", title="Double Dice Roll")

    @commands.command(name='pick2', help='Pick between two complex options.')
    async def pick_two(self, ctx, opt1: str, opt2: str):
        choice = random.choice([opt1, opt2])
        await ctx.info(f"I've analyzed both and chosen: **{choice}**", title="Decision Engine")

    @commands.command(name='hack2', help='A more advanced fake hack.')
    async def advanced_hack(self, ctx, user: discord.Member):
        async with ctx.typing():
            msg = await ctx.info(f"Connecting to Mainframe of **{user.name}**...")
            await asyncio.sleep(1)
            steps = ["Brute-forcing 2FA...", "Bypassing hardware encryption...", "Injecting kernel exploit...", "Extracting browser history..."]
            for step in steps:
                await msg.edit(content=None, embed=self.bot.embed_manager.generic(description=step, title="Hacking..."))
                await asyncio.sleep(1)
            
            await msg.edit(content=None, embed=self.bot.embed_manager.success(f"Successfully breached **{user.display_name}**.", title="Access Granted"))

    @commands.command(name='simprate', help='Check the simp rate of a user.')
    async def simp_rate(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        rate = random.randint(0, 100)
        await ctx.embed(f"**{user.display_name}** is `{rate}%` a simp. 🥺", title="Simp Rate")

    @commands.command(name='coolrate', help='Check the cool rate of a user.')
    async def cool_rate(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        rate = random.randint(0, 100)
        await ctx.embed(f"**{user.display_name}** is `{rate}%` cool. 😎", title="Cool Rate")

    @commands.command(name='waifurate', help='Check the waifu rate of a user.')
    async def waifu_rate(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        rate = random.randint(0, 100)
        await ctx.embed(f"**{user.display_name}** is `{rate}%` a waifu. ✨", title="Waifu Rate")

    @commands.command(name='bored2', help='Get an advanced boredom buster.')
    async def bored_two(self, ctx):
        await ctx.embed("Go outside and touch some grass. It's a high-level activity.", title="Boredom Buster")

    @commands.command(name='8ball2', help='Ask the advanced 8-ball.')
    async def advanced_8ball(self, ctx, *, question: str):
        responses = ["The quantum threads say yes.", "Probability is near zero.", "Error: Reality uncertain.", "Signs point to absolute success."]
        await ctx.embed(f"**Question:** {question}\n**Quantum Answer:** {random.choice(responses)}", title="Quantum 8-Ball")

    @commands.command(name='vibecheck', help='Check the current vibe of a user.')
    async def vibe_check(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        vibe = random.choice(["Immense", "Positive", "Sketchy", "Depressed", "Radiant", "Chill", "Chaotic"])
        await ctx.embed(f"**{user.display_name}'s** current vibe: `{vibe}`", title="Vibe Check")

    @commands.command(name='howcute', help='Check how cute a user is.')
    async def how_cute(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        rate = random.randint(0, 100)
        await ctx.embed(f"**{user.display_name}** is `{rate}%` cute! 🥰", title="Cute Meter")

    @commands.command(name='howrich', help='Check how rich a user is.')
    async def how_rich(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        rate = random.randint(0, 100)
        await ctx.embed(f"**{user.display_name}** is `{rate}%` rich! 💰", title="Wealth Meter")

    @commands.command(name='howdrunk', help='Check how drunk a user is.')
    async def how_drunk(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        rate = random.randint(0, 100)
        await ctx.embed(f"**{user.display_name}** is `{rate}%` drunk! 🍺", title="Sobriety Test")

    @commands.command(name='howtoxic', help='Check how toxic a user is.')
    async def how_toxic(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        rate = random.randint(0, 100)
        await ctx.embed(f"**{user.display_name}** is `{rate}%` toxic! ☣️", title="Toxicity Meter")

    @commands.command(name='marry', help='Fake marry a user.')
    async def fake_marry(self, ctx, user: discord.Member):
        if user == ctx.author: return await ctx.error("You can't marry yourself.")
        await ctx.embed(f"💍 **{ctx.author.display_name}** and **{user.display_name}** are now legally married! (Not really)", title="Wedding Bells")

    @commands.command(name='divorce', help='Fake divorce a user.')
    async def fake_divorce(self, ctx, user: discord.Member):
        await ctx.embed(f"💔 **{ctx.author.display_name}** has divorced **{user.display_name}**. It's over.", title="Heartbreak")

    @commands.command(name='compatibility2', help='Advanced compatibility check.')
    async def advanced_comp(self, ctx, user1: discord.Member, user2: discord.Member):
        rate = random.randint(0, 100)
        await ctx.embed(f"💖 **{user1.display_name}** and **{user2.display_name}** are `{rate}%` compatible!", title="Matchmaker")

    @commands.command(name='iq2', help='Calculate the collective IQ of two users.')
    async def collective_iq(self, ctx, user1: discord.Member, user2: discord.Member):
        iq = random.randint(20, 200)
        await ctx.embed(f"Combined, **{user1.display_name}** and **{user2.display_name}** have an IQ of `{iq}`.", title="Collective IQ")

    @commands.command(name='hackserver', help='Perform a fake hack on the server.')
    async def hack_server(self, ctx):
        async with ctx.typing():
            msg = await ctx.info("Attempting to bypass server firewall...")
            await asyncio.sleep(1)
            await msg.edit(content=None, embed=self.bot.embed_manager.generic(description="Downloading owner's private tokens...", title="Hacking Server"))
            await asyncio.sleep(1)
            await msg.edit(content=None, embed=self.bot.embed_manager.success(description="Server core bypassed. Admin access granted.", title="Hacking Complete"))

    @commands.command(name='roast2', help='A more brutal roast.')
    async def advanced_roast(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        roasts = ["You're as useful as a screen door on a submarine.", "If I wanted to kill myself, I'd climb your ego and jump to your IQ."]
        await ctx.send(f"{user.mention}, {random.choice(roasts)}")

    @commands.command(name='deathmatch', help='Simulate a fight to the death.')
    async def death_match(self, ctx, u1: discord.Member, u2: discord.Member):
        winner = random.choice([u1, u2])
        await ctx.embed(f"⚔️ **{u1.display_name}** and **{u2.display_name}** fought a brutal battle. **{winner.display_name}** emerged as the sole survivor!", title="Fight to the Death")

    @commands.command(name='howhigh', help='Check how high a user is.')
    async def how_high(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        rate = random.randint(0, 100)
        await ctx.embed(f"**{user.display_name}** is `{rate}%` high right now. 🌿", title="Elevation Check")

    @commands.command(name='howsalty', help='Check how salty a user is.')
    async def how_salty(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        rate = random.randint(0, 100)
        await ctx.embed(f"**{user.display_name}** is `{rate}%` salty. 🧂", title="Salt Meter")

    @commands.command(name='howpro', help='Check how pro a user is.')
    async def how_pro(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        rate = random.randint(0, 100)
        await ctx.embed(f"**{user.display_name}** is `{rate}%` a pro gamer. 🎮", title="Skill Meter")

    @commands.command(name='hownoob', help='Check how much of a noob a user is.')
    async def how_noob(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        rate = random.randint(0, 100)
        await ctx.embed(f"**{user.display_name}** is `{rate}%` a total noob. 🤡", title="Noob Meter")

    @commands.command(name='fortune2', help='A more accurate fortune.')
    async def advanced_fortune(self, ctx):
        fortunes = ["A large sum of money is coming your way.", "You will be hit by a bus tomorrow."]
        await ctx.embed(random.choice(fortunes), title="Prophecy")

    @commands.command(name='rate2', help='Rate a user from 1 to 100.')
    async def advanced_rate(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        rate = random.randint(1, 100)
        await ctx.embed(f"I rate **{user.display_name}** a `{rate}/100`!", title="Evaluation")

    @commands.command(name='shipname', help='Generate a ship name for two users.')
    async def ship_name(self, ctx, u1: discord.Member, u2: discord.Member):
        name = u1.name[:len(u1.name)//2] + u2.name[len(u2.name)//2:]
        await ctx.embed(f"The ship name for **{u1.name}** and **{u2.name}** is: **{name.capitalize()}** 💖", title="Ship Name Generator")

    @commands.command(name='slap2', help='A harder slap.')
    async def advanced_slap(self, ctx, user: discord.Member):
        await ctx.embed(f"💥 **{ctx.author.display_name}** slapped **{user.display_name}** into another dimension!", title="Heavy Slap")

    @commands.command(name='hug2', help='A tighter hug.')
    async def advanced_hug(self, ctx, user: discord.Member):
        await ctx.embed(f"🫂 **{ctx.author.display_name}** gave **{user.display_name}** a super tight hug!", title="Mega Hug")

    @commands.command(name='kill2', help='A more creative kill.')
    async def advanced_kill(self, ctx, user: discord.Member):
        await ctx.embed(f"💀 **{ctx.author.display_name}** deleted **{user.display_name}'s** existence from the database.", title="System Purge")

    @commands.command(name='howsimp2', help='Calculate the total simp value.')
    async def simp_value(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        value = random.randint(0, 1000000)
        await ctx.embed(f"**{user.display_name}** has accumulated **${value:,}** in simp donations. 💸", title="Simp Donation Tracker")

    @commands.command(name='howcool2', help='Check the coolness level.')
    async def cool_level(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        await ctx.embed(f"**{user.display_name}** is absolute zero cool. 🧊", title="Coolness Level")

    @commands.command(name='waifurate2', help='Calculate the market value of a waifu.')
    async def waifu_value(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        value = random.randint(100, 10000)
        await ctx.embed(f"**{user.display_name}** is worth **{value:,}** Gems on the waifu market. 💎", title="Waifu Market")

    @commands.command(name='iqcollective', help='Calculate the IQ of a group.')
    async def iq_group(self, ctx, *members: discord.Member):
        iq = random.randint(50, 160)
        await ctx.embed(f"The collective IQ of the group is `{iq}`. {'Elite' if iq > 120 else 'Average' if iq > 90 else 'Room Temperature'}", title="Group IQ")

    @commands.command(name='howsimp3', help='Advanced simp level analysis.')
    async def simp_v3(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        rate = random.randint(0, 100)
        await ctx.embed(f"**{user.display_name}** has reached **Tier {random.randint(1, 5)}** simp status! (`{rate}%` completion)", title="Simp Analyst")

    @commands.command(name='hackfriends', help='Fake hack all your friends.')
    async def hack_friends(self, ctx):
        await ctx.info("Scanning friend list... [██████████] 100%\nInjecting malware into 50+ DMs...", title="Mass Breach")

    @commands.command(name='howrich2', help='Evaluate a user\'s net worth.')
    async def worth_eval(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        worth = random.randint(100, 10000000)
        await ctx.embed(f"**{user.display_name}'s** estimated net worth: **${worth:,}**", title="Wealth Analysis")

    @commands.command(name='predict', help='Predict the future of a user.')
    async def predict_future(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        outcomes = ["Will become a billionaire", "Will win the lottery", "Will be banned from Discord", "Will find true love"]
        await ctx.embed(f"**{user.display_name}'s** future: `{random.choice(outcomes)}`", title="The Seer")

    @commands.command(name='howgay2', help='More accurate gay meter.')
    async def gay_v2(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        await ctx.embed(f"**{user.display_name}** is `{random.randint(0, 100)}%` 🏳️‍🌈", title="Gay Meter V2")

    @commands.command(name='howsmart2', help='Scientific smartness test.')
    async def smart_v2(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        await ctx.embed(f"**{user.display_name}** is `{random.randint(0, 100)}%` smart!", title="Brain Scan")

    @commands.command(name='howdumb2', help='Advanced stupidity test.')
    async def dumb_v2(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        await ctx.embed(f"**{user.display_name}** is `{random.randint(0, 100)}%` dumb.", title="Stupidity Test")

    @commands.command(name='slap3', help='Ultra mega slap.')
    async def slap_v3(self, ctx, user: discord.Member):
        await ctx.embed(f"🌌 **{ctx.author.display_name}** slapped **{user.display_name}** out of this dimension!", title="Cosmic Slap")

    @commands.command(name='hug3', help='The warmest hug.')
    async def hug_v3(self, ctx, user: discord.Member):
        await ctx.embed(f"✨ **{ctx.author.display_name}** gave **{user.display_name}** a hug so warm it melted the bot's circuits!", title="Legendary Hug")

    @commands.command(name='kill3', help='A funny database kill.')
    async def kill_v3(self, ctx, user: discord.Member):
        await ctx.embed(f"🗑️ **{ctx.author.display_name}** moved **{user.display_name}** to the Recycle Bin.", title="User Purge")

    @commands.command(name='shindeiru2', help='Nani?!')
    async def nani_v2(self, ctx):
        await ctx.send("Omae wa mou... **SHINDEIRU**")

    @commands.command(name='fortune3', help='A very lucky fortune.')
    async def lucky_fortune(self, ctx):
        await ctx.embed("You will find a rare drop in your next game.", title="Fortune")

    @commands.command(name='rate3', help='Rate a user\'s profile.')
    async def rate_profile(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        await ctx.embed(f"I rate **{user.display_name}'s** profile a `{random.randint(1, 10)}/10`!", title="Profile Review")

    @commands.command(name='vibecheck2', help='Intense vibe check.')
    async def intense_vibe(self, ctx):
        await ctx.embed(f"Vibe status: **{random.choice(['PERFECT', 'SKETCHY', 'DANGEROUS', 'CHILL'])}**", title="Intense Vibe Check")

async def setup(bot):
    await bot.add_cog(Fun2(bot))
