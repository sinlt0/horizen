import discord
from discord.ext import commands
import aiohttp
import random
import urllib.parse
import asyncio
import json
import io
from PIL import Image, ImageDraw, ImageFont

class FunCog(commands.Cog):
    """Fun and entertainment commands!"""
    category = "fun"

    def __init__(self, bot):
        self.bot = bot

    async def _generate_ship_card(self, user1, user2, percentage):
        w, h = 700, 300
        img = Image.new('RGB', (w, h), (15, 15, 20))
        draw = ImageDraw.Draw(img)
        
        async def get_av(user):
            try:
                async with aiohttp.ClientSession() as s:
                    async with s.get(str(user.display_avatar.with_format('png').url)) as r:
                        return Image.open(io.BytesIO(await r.read())).convert("RGBA").resize((150, 150), Image.Resampling.LANCZOS)
            except: return Image.new('RGBA', (150, 150), (50, 50, 50))

        av1 = await get_av(user1)
        av2 = await get_av(user2)
        
        mask = Image.new('L', (150, 150), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 150, 150), fill=255)
        
        img.paste(av1, (75, 40), mask)
        img.paste(av2, (475, 40), mask)
        
        bar_x, bar_y, bar_w, bar_h = 100, 230, 500, 30
        draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], radius=15, fill=(35, 35, 40))
        if percentage > 0:
            draw.rounded_rectangle([bar_x, bar_y, bar_x + int(bar_w * (percentage/100)), bar_y + bar_h], radius=15, fill=(255, 99, 132))
            
        f_p = "/data/data/com.termux/files/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"
        def get_f(s):
            try: return ImageFont.truetype(f_p, s)
            except: return ImageFont.load_default()
        
        draw.text((w//2 - 35, bar_y - 45), f"{percentage}%", font=get_f(30), fill=(255, 255, 255))
        draw.text((w//2 - 35, 80), "❤️", font=get_f(60), fill=(255, 0, 0))
        
        buf = io.BytesIO()
        img.save(buf, 'PNG')
        buf.seek(0)
        return discord.File(buf, filename="ship.png")

    @commands.command(name='meme', help='Fetch a random meme from Reddit.')
    async def meme(self, ctx):
        async with aiohttp.ClientSession() as session:
            async with session.get('https://meme-api.com/gimme') as response:
                if response.status == 200:
                    data = await response.json()
                    embed = self.bot.embed_manager.generic(description=f"**{data['title']}**", title="Random Meme")
                    embed.set_image(url=data['url'])
                    embed.set_footer(text=f"From r/{data['subreddit']}")
                    await ctx.send(embed=embed)
                else: await ctx.error("Failed to fetch meme.")

    @commands.command(name='cat', help='Shows a random cat image.')
    async def cat(self, ctx):
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.thecatapi.com/v1/images/search') as response:
                if response.status == 200:
                    data = await response.json()
                    embed = self.bot.embed_manager.generic(description="Here is a cute cat!", title="Random Cat")
                    embed.set_image(url=data[0]['url'])
                    await ctx.send(embed=embed)
                else: await ctx.error("Could not find any cats...")

    @commands.command(name='dog', help='Shows a random dog image.')
    async def dog(self, ctx):
        async with aiohttp.ClientSession() as session:
            async with session.get('https://dog.ceo/api/breeds/image/random') as response:
                if response.status == 200:
                    data = await response.json()
                    embed = self.bot.embed_manager.generic(description="Who's a good boy?", title="Random Dog")
                    embed.set_image(url=data['message'])
                    await ctx.send(embed=embed)
                else: await ctx.error("Could not find any dogs...")

    @commands.command(name='8ball', help='Ask the magic 8-ball a question.')
    async def eightball(self, ctx, *, question: str):
        responses = ["It is certain.", "It is decidedly so.", "Without a doubt.", "Yes - definitely.", "You may rely on it.", "As I see it, yes.", "Most likely.", "Outlook good.", "Yes.", "Signs point to yes.", "Reply hazy, try again.", "Ask again later.", "Better not tell you now.", "Cannot predict now.", "Don't count on it.", "My reply is no.", "My sources say no.", "Outlook not so good.", "Very doubtful."]
        await ctx.embed(f"**Question:** {question}\n**Answer:** {random.choice(responses)}", title="Magic 8-Ball")

    @commands.command(name='joke', help='Tells a random joke.')
    async def joke(self, ctx):
        async with aiohttp.ClientSession() as session:
            async with session.get('https://official-joke-api.appspot.com/random_joke') as response:
                if response.status == 200:
                    data = await response.json()
                    await ctx.embed(f"**{data['setup']}**\n\n*{data['punchline']}*", title="Random Joke")
                else: await ctx.error("Failed to fetch joke.")

    @commands.command(name='fact', help='Tells a random fun fact.')
    async def fact(self, ctx):
        async with aiohttp.ClientSession() as session:
            async with session.get('https://uselessfacts.jsph.pl/random.json?language=en') as response:
                if response.status == 200:
                    data = await response.json()
                    await ctx.embed(data['text'], title="Fun Fact")
                else: await ctx.error("I'm fresh out of facts!")

    @commands.command(name='coinflip', aliases=['flip', 'coin'], help='Flip a coin!')
    async def coinflip(self, ctx):
        await ctx.embed(f"The coin landed on... **{random.choice(['Heads', 'Tails'])}**!", title="Coin Flip")

    @commands.command(name='roll', aliases=['dice'], help='Roll a die.')
    async def roll(self, ctx, sides: int = 6):
        if sides < 1: return await ctx.error("A die must have at least 1 side!")
        await ctx.embed(f"You rolled a **{random.randint(1, sides)}**!", title=f"Dice Roll (d{sides})")

    @commands.command(name='ship', aliases=['lovecalculator', 'lovecalc'], help='Check compatibility between users with a visual card.')
    async def ship(self, ctx, user1: discord.Member, user2: discord.Member = None):
        user2 = user2 or ctx.author
        percentage = random.randint(0, 100)
        status = "Destiny 💍" if percentage > 90 else "Great Match ❤️" if percentage > 70 else "Just Friends 🤝" if percentage > 40 else "It's Complicated 💔" if percentage > 20 else "No Chance 💀"
        async with ctx.typing():
            file = await self._generate_ship_card(user1, user2, percentage)
            embed = self.bot.embed_manager.generic(description=f"💖 **{user1.display_name}** & **{user2.display_name}**\n\n**Compatibility:** `{percentage}%` — *{status}*", title="Love Meter")
            embed.set_image(url="attachment://ship.png")
            await ctx.send(file=file, embed=embed)

    @commands.command(name='hack', help='Perform a fake hack on a user.')
    async def hack(self, ctx, user: discord.Member):
        async with ctx.typing():
            msg = await ctx.info(f"Initiating hack on **{user.display_name}**...")
            await asyncio.sleep(1); await msg.edit(content="Accessing Discord data... [███░░░░░░░] 30%")
            await asyncio.sleep(1); await msg.edit(content="Injecting malware into DMs... [██████░░░░] 60%")
            await asyncio.sleep(1); await msg.edit(content="Downloading private info... [█████████░] 90%")
            p_info = [f"**Email:** {user.name}{random.randint(10,99)}@gmail.com", f"**Password:** `{'*'*random.randint(6,12)}`", f"**IP Address:** `192.168.{random.randint(0,255)}.{random.randint(1,255)}`", f"**Location:** {random.choice(['London', 'New York', 'Tokyo', 'Paris'])}"]
            await msg.edit(content=None, embed=self.bot.embed_manager.success(f"**User:** {user.mention}\n\n" + "\n".join(p_info), title="Hack Complete!"))

    @commands.command(name='slots', help='Play a simple slot machine.')
    async def slots(self, ctx):
        emojis = ["🍎", "🍊", "🍇", "🍒", "💎", "🎰"]
        a, b, c = random.choice(emojis), random.choice(emojis), random.choice(emojis)
        result = "YOU WIN! 🎉" if a == b == c else "So close! ❌"
        await ctx.send(embed=self.bot.embed_manager.generic(description=f"**[ {a} | {b} | {c} ]**\n\n{result}", title="Slot Machine"))

    @commands.command(name='emojify', help='Convert text into regional indicator emojis.')
    async def emojify(self, ctx, *, text: str):
        output = ""
        for char in text.lower():
            if char.isalpha(): output += f":regional_indicator_{char}: "
            elif char.isdigit(): output += f":{['zero','one','two','three','four','five','six','seven','eight','nine'][int(char)]}: "
            else: output += char
        if len(output) > 2000: return await ctx.error("Text too long.")
        await ctx.send(output)

    @commands.command(name='reverse', help='Reverse a message.')
    async def reverse(self, ctx, *, text: str): await ctx.send(text[::-1])

    @commands.command(name='howgay', aliases=['gaymeter'], help='Check how gay a user is.')
    async def howgay(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        await ctx.embed(f"**{user.display_name}** is `{random.randint(0, 100)}%` gay! 🏳️‍🌈", title="Gay Meter")

    @commands.command(name='howsimp', help='Check how much of a simp a user is.')
    async def howsimp(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        await ctx.embed(f"**{user.display_name}** is `{random.randint(0, 100)}%` a simp! 💖", title="Simp Meter")

    @commands.command(name='iq', help='Check the IQ of a user.')
    async def iq_meter(self, ctx, user: discord.Member = None):
        user = user or ctx.author; iq = random.randint(50, 150)
        status = "Genius 🧠" if iq > 130 else "Smart 🎓" if iq > 110 else "Average 😐" if iq > 90 else "Below Average 📉"
        await ctx.embed(f"**{user.display_name}** has an IQ of `{iq}`\n**Status:** {status}", title="IQ Meter")

    @commands.command(name='pick', aliases=['choose'], help='Let the bot pick between several options.')
    async def pick_option(self, ctx, *, options: str):
        choices = options.split(';')
        if len(choices) < 2: return await ctx.error("Provide at least two options separated by a semicolon (`;`).")
        await ctx.info(f"I choose: **{random.choice(choices).strip()}**", title="Bot's Choice")

    @commands.command(name='pp', aliases=['size'], help='Check the size of a user\'s pp.')
    async def pp_size(self, ctx, user: discord.Member = None):
        user = user or ctx.author; await ctx.embed(f"**{user.display_name}**'s size:\n8{'='*random.randint(0, 12)}D", title="PP Meter")

    @commands.command(name='nitro', help='Generate a totally real Nitro gift.')
    async def fake_nitro(self, ctx): await ctx.send(f"https://discord.gift/{''.join(random.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(16))}")

    @commands.command(name='rps', help='Play Rock Paper Scissors with the bot.')
    async def rps(self, ctx, choice: str):
        choice = choice.lower(); valid = ["rock", "paper", "scissors"]
        if choice not in valid: return await ctx.error("Choose `rock`, `paper`, or `scissors`.")
        bc = random.choice(valid)
        if choice == bc: res = "It's a tie! 🤝"
        elif (choice == "rock" and bc == "scissors") or (choice == "paper" and bc == "rock") or (choice == "scissors" and bc == "paper"): res = "You win! 🎉"
        else: res = "I win! 😈"
        await ctx.info(f"**You:** {choice.capitalize()}\n**Me:** {bc.capitalize()}\n\n{res}", title="Rock Paper Scissors")

    @commands.command(name='dadjoke', help='Tells a random dad joke.')
    async def dad_joke(self, ctx):
        async with aiohttp.ClientSession() as s:
            async with s.get('https://icanhazdadjoke.com/', headers={"Accept": "application/json"}) as r:
                if r.status == 200: d = await r.json(); await ctx.embed(d['joke'], title="Dad Joke 👨")
                else: await ctx.error("Failed to fetch joke.")

    @commands.command(name='minesweeper', help='Generate a minesweeper grid.')
    async def minesweeper(self, ctx, rows: int = 8, cols: int = 8, bombs: int = 10):
        if rows * cols > 100: return await ctx.error("Grid too large! Max 100 cells.")
        grid = [['0' for _ in range(cols)] for _ in range(rows)]; count = 0
        while count < bombs:
            r, c = random.randint(0, rows-1), random.randint(0, cols-1)
            if grid[r][c] != 'B': grid[r][c] = 'B'; count += 1
        for r in range(rows):
            for c in range(cols):
                if grid[r][c] == 'B': continue
                bomb_count = 0
                for dr in [-1, 0, 1]:
                    for dc in [-1, 0, 1]:
                        if 0 <= r+dr < rows and 0 <= c+dc < cols and grid[r+dr][c+dc] == 'B': bomb_count += 1
                grid[r][c] = str(bomb_count)
        emoji_map = {'B': '||💣||', '0': '||0️⃣||', '1': '||1️⃣||', '2': '||2️⃣||', '3': '||3️⃣||', '4': '||4️⃣||', '5': '||5️⃣||', '6': '||6️⃣||', '7': '||7️⃣||', '8': '||8️⃣||'}
        output = ""
        for row in grid: output += "".join([emoji_map[c] for c in row]) + "\n"
        await ctx.send(f"**Minesweeper ({rows}x{cols}, {bombs} bombs)**\n{output}")

    @commands.command(name='clap', help='R👏E👏P👏L👏A👏C👏E👏 👏S👏P👏A👏C👏E👏S👏')
    async def clap_text(self, ctx, *, text: str): await ctx.send(text.replace(" ", " 👏 ") + " 👏")

    @commands.command(name='shindeiru', help='Omae wa mou shindeiru...')
    async def shindeiru(self, ctx):
        await ctx.send("Omae wa mou shindeiru...")
        await asyncio.sleep(1); await ctx.send("**NANI?!**")

    @commands.command(name='roast', help='Roast a user.')
    async def roast(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        roasts = ["You're the reason the gene pool needs a lifeguard.", "You're like a cloud. When you disappear, it's a beautiful day.", "I'd slap you, but that would be animal abuse."]
        await ctx.send(f"{user.mention}, {random.choice(roasts)}")

    @commands.command(name='compliment', help='Compliment a user.')
    async def compliment(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        compliments = ["You're a gift to those around you.", "You have an amazing sense of humor.", "You're even more beautiful on the inside than you are on the outside."]
        await ctx.send(f"{user.mention}, {random.choice(compliments)}")

    @commands.command(name='hotness', aliases=['hotmeter'], help='Check how hot a user is.')
    async def hotness(self, ctx, user: discord.Member = None):
        user = user or ctx.author; await ctx.embed(f"**{user.display_name}** is `{random.randint(0, 100)}%` hot! 🔥", title="Hotness Meter")

    @commands.command(name='kill', help='Generate a funny kill message.')
    async def kill_cmd(self, ctx, user: discord.Member):
        if user == ctx.author: return await ctx.error("You can't kill yourself!")
        messages = [f"{ctx.author.mention} pushed {user.mention} off a cliff.", f"{ctx.author.mention} fed {user.mention} to a shark.", f"{ctx.author.mention} hit {user.mention} with a car."]
        await ctx.send(random.choice(messages))

    @commands.command(name='morse', help='Convert text to morse code.')
    async def morse_code(self, ctx, *, text: str):
        mapping = {'A': '.-', 'B': '-...', 'C': '-.-.', 'D': '-..', 'E': '.', 'F': '..-.', 'G': '--.', 'H': '....', 'I': '..', 'J': '.---', 'K': '-.-', 'L': '.-..', 'M': '--', 'N': '-.', 'O': '---', 'P': '.--.', 'Q': '--.-', 'R': '.-.', 'S': '...', 'T': '-', 'U': '..-', 'V': '...-', 'W': '.--', 'X': '-..-', 'Y': '-.--', 'Z': '--..', '1': '.----', '2': '..---', '3': '...--', '4': '....-', '5': '.....', '6': '-....', '7': '--...', '8': '---..', '9': '----.', '0': '-----', ' ': '/'}
        output = " ".join([mapping.get(c.upper(), c) for c in text])
        if len(output) > 2000: return await ctx.error("Text too long.")
        await ctx.send(f"`{output}`")

    @commands.command(name='owo', aliases=['owofy'], help='OwOfy your text.')
    async def owo_text(self, ctx, *, text: str):
        text = text.replace('L', 'W').replace('R', 'W').replace('l', 'w').replace('r', 'w').replace('o', 'owo').replace('u', 'uwu')
        if len(text) > 2000: return await ctx.error("Text too long.")
        await ctx.send(text)

    @commands.command(name='mock', help='mOcK sOmE tExT.')
    async def mock_text(self, ctx, *, text: str): await ctx.send("".join([c.upper() if i % 2 == 0 else c.lower() for i, c in enumerate(text)]))

    @commands.command(name='bird')
    async def bird(self, ctx):
        async with aiohttp.ClientSession() as s:
            async with s.get('https://some-random-api.com/img/bird') as r:
                if r.status == 200: d = await r.json(); await ctx.send(embed=self.bot.embed_manager.generic("Tweet tweet!", title="Random Bird").set_image(url=d['link']))

    @commands.command(name='panda')
    async def panda(self, ctx):
        async with aiohttp.ClientSession() as s:
            async with s.get('https://some-random-api.com/img/panda') as r:
                if r.status == 200: d = await r.json(); await ctx.send(embed=self.bot.embed_manager.generic("Panda!", title="Random Panda").set_image(url=d['link']))

    @commands.command(name='fox')
    async def fox(self, ctx):
        async with aiohttp.ClientSession() as s:
            async with s.get('https://some-random-api.com/img/fox') as r:
                if r.status == 200: d = await r.json(); await ctx.send(embed=self.bot.embed_manager.generic("What does the fox say?", title="Random Fox").set_image(url=d['link']))

    @commands.command(name='ascii', help='Convert text to ASCII art.')
    async def ascii_art(self, ctx, *, text: str):
        if len(text) > 20: return await ctx.error("Max 20 characters.")
        async with aiohttp.ClientSession() as s:
            async with s.get(f"https://artii.herokuapp.com/make?text={urllib.parse.quote(text)}") as r:
                if r.status == 200: o = await r.text(); await ctx.send(f"```\n{o}\n```")
                else: await ctx.error("Failed.")

    @commands.command(name='howlesbian', help='Check how lesbian a user is.')
    async def howlesbian(self, ctx, user: discord.Member = None):
        user = user or ctx.author; await ctx.embed(f"**{user.display_name}** is `{random.randint(0, 100)}%` lesbian! 👩‍❤️‍👩", title="Lesbian Meter")

    @commands.command(name='howtrans', help='Check how trans a user is.')
    async def howtrans(self, ctx, user: discord.Member = None):
        user = user or ctx.author; await ctx.embed(f"**{user.display_name}** is `{random.randint(0, 100)}%` trans! 🏳️‍⚧️", title="Trans Meter")

    @commands.command(name='trivia', help='Get a random trivia question.')
    async def trivia_cmd(self, ctx):
        async with aiohttp.ClientSession() as s:
            async with s.get('https://opentdb.com/api.php?amount=1&type=multiple') as r:
                if r.status == 200:
                    d = await r.json(); res = d['results'][0]; q = res['question'].replace('&quot;', '"').replace('&#039;', "'")
                    embed = self.bot.embed_manager.generic(description=f"**Category:** {res['category']}\n**Difficulty:** {res['difficulty'].capitalize()}\n\n**Question:**\n{q}\n\n*Reveal answer in 10 seconds...*", title="Trivia Time!")
                    msg = await ctx.send(embed=embed); await asyncio.sleep(10)
                    embed.description = f"**Category:** {res['category']}\n**Difficulty:** {res['difficulty'].capitalize()}\n\n**Question:**\n{q}\n\n**Answer:** ||{res['correct_answer']}||"; await msg.edit(embed=embed)
                else: await ctx.error("Failed.")

    @commands.command(name='advice', help='Get random life advice.')
    async def advice_cmd(self, ctx):
        async with aiohttp.ClientSession() as s:
            async with s.get('https://api.adviceslip.com/advice') as r:
                if r.status == 200: d = await r.json(content_type=None); await ctx.embed(d['slip']['advice'], title="Life Advice 💡")
                else: await ctx.error("Failed.")

    @commands.command(name='fortune', help='Get a random fortune cookie message.')
    async def fortune_cookie(self, ctx): await ctx.embed(random.choice(["Success is in your future.", "Happiness lies ahead.", "Adventure can be real happiness."]), title="Fortune Cookie 🥠")

    @commands.command(name='truth', aliases=['tod_t'], help='Get a random truth question.')
    async def truth_cmd(self, ctx):
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get('https://api.truthordarebot.xyz/v1/truth') as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        await ctx.embed(data['question'], title="Truth? 🤔")
                    else: await ctx.embed("What is your biggest fear?", title="Truth? 🤔")

    @commands.command(name='dare', aliases=['tod_d'], help='Get a random dare challenge.')
    async def dare_cmd(self, ctx):
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get('https://api.truthordarebot.xyz/v1/dare') as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        await ctx.embed(data['question'], title="Dare! 😈")
                    else: await ctx.embed("Do 20 pushups.", title="Dare! 😈")

    @commands.command(name='wouldyourather', aliases=['wyr'], help='Get a random Would You Rather question.')
    async def wyr_cmd(self, ctx):
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get('https://api.truthordarebot.xyz/v1/wyr') as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        await ctx.embed(data['question'], title="Would You Rather? 🤔")
                    else: await ctx.error("Failed to fetch.")

    @commands.command(name='topic', aliases=['nhie'], help='Get a random conversation starter.')
    async def random_topic(self, ctx):
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get('https://api.truthordarebot.xyz/v1/nhie') as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        await ctx.embed(data['question'], title="Topic / NHIE 💬")
                    else: await ctx.error("Failed to fetch.")

    @commands.command(name='cap', help='Check how much cap is in a message.')
    async def cap_meter(self, ctx, user: discord.Member = None):
        user = user or ctx.author; await ctx.embed(f"**{user.display_name}** is `{random.randint(0, 100)}%` cap! 🧢", title="Cap Meter")

    @commands.command(name='sus', help='Check how sus a user is.')
    async def sus_meter(self, ctx, user: discord.Member = None):
        user = user or ctx.author; await ctx.embed(f"**{user.display_name}** is `{random.randint(0, 100)}%` sus! 📮", title="Sus Meter")

    @commands.command(name='token', help='Generate a totally real Discord token.')
    async def fake_token(self, ctx, user: discord.Member = None):
        user = user or ctx.author; import base64, string; p1 = base64.b64encode(str(user.id).encode()).decode(); p2 = "".join(random.choice(string.ascii_letters + string.digits + "-_") for _ in range(24)); p3 = "".join(random.choice(string.ascii_letters + string.digits + "-_") for _ in range(30)); await ctx.send(f"`{p1}.{p2}.{p3}`")

    @commands.command(name='ip', help='Generate a totally real IP address.')
    async def fake_ip(self, ctx, user: discord.Member = None):
        user = user or ctx.author; ip = f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"; await ctx.info(f"**User:** {user.mention}\n**IP:** `{ip}`", title="IP Logger (Fake)")

    @commands.command(name='waifusfw', help='Shows a random SFW anime waifu.')
    async def waifu_sfw(self, ctx):
        async with aiohttp.ClientSession() as s:
            async with s.get('https://api.waifu.pics/sfw/waifu') as r:
                if r.status == 200: d = await r.json(); await ctx.send(embed=self.bot.embed_manager.generic("Here is a waifu!", title="Anime Waifu").set_image(url=d['url']))

    @commands.command(name='husbando', help='Shows a random SFW anime husbando.')
    async def husbando_sfw(self, ctx):
        async with aiohttp.ClientSession() as s:
            async with s.get('https://api.waifu.pics/sfw/husbando') as r:
                if r.status == 200: d = await r.json(); await ctx.send(embed=self.bot.embed_manager.generic("Here is a husbando!", title="Anime Husbando").set_image(url=d['url']))

    @commands.command(name='nekosfw', help='Shows a random SFW neko image.')
    async def neko_sfw(self, ctx):
        async with aiohttp.ClientSession() as s:
            async with s.get('https://api.waifu.pics/sfw/neko') as r:
                if r.status == 200: d = await r.json(); await ctx.send(embed=self.bot.embed_manager.generic("Nyan~", title="SFW Neko").set_image(url=d['url']))

    @commands.command(name='catfact', help='Get a random cat fact.')
    async def cat_fact(self, ctx):
        async with aiohttp.ClientSession() as s:
            async with s.get('https://catfact.ninja/fact') as r:
                if r.status == 200: d = await r.json(); await ctx.embed(d['fact'], title="Cat Fact 🐱")

    @commands.command(name='dogfact', help='Get a random dog fact.')
    async def dog_fact(self, ctx):
        async with aiohttp.ClientSession() as s:
            async with s.get('https://dogapi.dog/api/v2/facts') as r:
                if r.status == 200: d = await r.json(); await ctx.embed(d['data'][0]['attributes']['body'], title="Dog Fact 🐶")

    @commands.command(name='rate', help='Rate something from 1 to 10.')
    async def rate_something(self, ctx, *, item: str):
        rating = random.randint(1, 10)
        await ctx.embed(f"I would rate **{item}** a `{rating}/10`!", title="Bot Rating")

    @commands.command(name='whowouldwin', help='See who would win in a fight between two things.')
    async def whowouldwin(self, ctx, item1: str, item2: str):
        winner = random.choice([item1, item2])
        await ctx.embed(f"In a legendary battle between **{item1}** and **{item2}**, the winner is... **{winner}**! 🏆", title="Death Battle")

    @commands.command(name='cowsay', help='Make a cow say your message.')
    async def cowsay_cmd(self, ctx, *, text: str):
        if len(text) > 100: return await ctx.error("Text too long.")
        url = f"https://helloacm.com/api/cowsay/?msg={urllib.parse.quote(text)}"
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        await ctx.send(f"```\n{data}\n```")
                    else: await ctx.error("Failed to generate cowsay.")

    @commands.command(name='figlet', help='Generate large ASCII text.')
    async def figlet_cmd(self, ctx, *, text: str):
        if len(text) > 20: return await ctx.error("Text too long.")
        url = f"https://artii.herokuapp.com/make?text={urllib.parse.quote(text)}&font=big"
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        output = await resp.text()
                        await ctx.send(f"```\n{output}\n```")
                    else: await ctx.error("Failed.")

    @commands.command(name='kanye', aliases=['kanyequote'], help='Get a random Kanye West quote.')
    async def kanye_quote(self, ctx):
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.kanye.rest/') as resp:
                if resp.status == 200:
                    data = await resp.json()
                    await ctx.embed(f"\"{data['quote']}\"", title="Kanye Says...")
                else: await ctx.error("Kanye is silent right now.")

    @commands.command(name='trump', help='Get a random Donald Trump quote.')
    async def trump_quote(self, ctx):
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.tronalddump.io/random/quote') as resp:
                if resp.status == 200:
                    data = await resp.json()
                    await ctx.embed(f"\"{data['value']}\"", title="Trump Says...")
                else: await ctx.error("No quotes found.")

    @commands.command(name='activity', help='Get a suggestion for something to do.')
    async def activity_cmd(self, ctx):
        async with aiohttp.ClientSession() as session:
            async with session.get('https://www.boredapi.com/api/activity') as resp:
                if resp.status == 200:
                    data = await resp.json()
                    await ctx.embed(f"**Activity:** {data['activity']}\n**Type:** {data['type'].capitalize()}\n**Participants:** {data['participants']}", title="Are you bored?")
                else: await ctx.error("I'm bored too.")

async def setup(bot):
    await bot.add_cog(FunCog(bot))
