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

    @commands.command(name='hackserver', help='Perform a fake hack on the server.')
    async def hack_server(self, ctx):
        async with ctx.typing():
            msg = await ctx.info("Attempting to bypass server firewall...")
            await asyncio.sleep(1)
            await msg.edit(content=None, embed=self.bot.embed_manager.generic(description="Downloading owner's private tokens...", title="Hacking Server"))
            await asyncio.sleep(1)
            await msg.edit(content=None, embed=self.bot.embed_manager.success(description="Server core bypassed. Admin access granted.", title="Hacking Complete"))

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

    @commands.command(name='shipname', help='Generate a ship name for two users.')
    async def ship_name(self, ctx, u1: discord.Member, u2: discord.Member):
        name = u1.name[:len(u1.name)//2] + u2.name[len(u2.name)//2:]
        await ctx.embed(f"The ship name for **{u1.name}** and **{u2.name}** is: **{name.capitalize()}** 💖", title="Ship Name Generator")

    @commands.command(name='hackfriends', help='Fake hack all your friends.')
    async def hack_friends(self, ctx):
        await ctx.info("Scanning friend list... [██████████] 100%\nInjecting malware into 50+ DMs...", title="Mass Breach")

    @commands.command(name='predict', help='Predict the future of a user.')
    async def predict_future(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        outcomes = ["Will become a billionaire", "Will win the lottery", "Will be banned from Discord", "Will find true love"]
        await ctx.embed(f"**{user.display_name}'s** future: `{random.choice(outcomes)}`", title="The Seer")

async def setup(bot):
    await bot.add_cog(Fun2(bot))
