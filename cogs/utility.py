import discord
from discord.ext import commands
import aiohttp
import urllib.parse
import datetime
import re

class Utility(commands.Cog):
    category = 'utility'

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="steal", aliases=["addemoji", "emojiadd"], help="Adds an emoji from another server using its URL or ID.")
    @commands.has_permissions(manage_expressions=True)
    @commands.bot_has_permissions(manage_expressions=True)
    async def steal_cmd(self, ctx, emoji: str, *, name: str = None):
        emoji_pattern = re.compile(r"<(a?):([a-zA-Z0-9_]+):([0-9]+)>")
        match = emoji_pattern.match(emoji)
        
        if match:
            is_animated = bool(match.group(1))
            emoji_name = name or match.group(2)
            emoji_id = match.group(3)
            extension = "gif" if is_animated else "png"
            url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{extension}"
        elif emoji.isdigit():
            emoji_name = name or f"emoji_{emoji}"
            url = f"https://cdn.discordapp.com/emojis/{emoji}.png"
        else:
            if not (emoji.startswith("http://") or emoji.startswith("https://")):
                return await ctx.error("Invalid emoji format.")
            url = emoji
            emoji_name = name or "stolen_emoji"

        async with ctx.typing():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status != 200:
                            return await ctx.error("Failed to fetch image.")
                        img_data = await response.read()
                
                new_emoji = await ctx.guild.create_custom_emoji(
                    name=emoji_name,
                    image=img_data,
                    reason=f"Emoji stolen by {ctx.author}"
                )
                await ctx.success(f"Successfully added {new_emoji}!")
            except Exception as e:
                await ctx.error(f"Error adding emoji: {str(e)}")

    @commands.command(name="urban", aliases=["ud"], help="Search for a definition on Urban Dictionary.")
    async def urban_search(self, ctx, *, term: str):
        url = f"https://api.urbandictionary.com/v0/define?term={urllib.parse.quote(term)}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return await ctx.error("Failed to connect to Urban Dictionary.")
                data = await resp.json()

        if not data['list']:
            return await ctx.error(f"No results found for `{term}`.")

        # Get the first result
        result = data['list'][0]
        definition = result['definition'].replace('[', '').replace(']', '')
        example = result['example'].replace('[', '').replace(']', '')
        
        embed = self.bot.embed_manager.generic(
            description=definition[:2000],
            title=f"Urban Dictionary: {result['word']}"
        )
        if example:
            embed.add_field(name="Example", value=example[:1024], inline=False)
        
        embed.set_footer(text=f"👍 {result['thumbs_up']} | 👎 {result['thumbs_down']} | Author: {result['author']}")
        await ctx.send(embed=embed)

    @commands.command(name="calculator", aliases=["calc", "math"], help="Perform a simple math calculation.")
    async def calculator(self, ctx, *, expression: str):
        # Extremely basic security for eval-like behavior
        # Only allow numbers, basic operators, and spaces
        clean_expr = re.sub(r'[^0-9+\-*/().\s]', '', expression)
        if not clean_expr.strip():
            return await ctx.error("Invalid expression. Use only numbers and `+ - * / ( )`.")

        try:
            # We use a limited namespace for safety, though math is still risky with eval
            # Better to use a dedicated math library if available, but for now simple eval is common
            result = eval(clean_expr, {"__builtins__": None}, {})
            await ctx.info(f"**Expression:** `{expression}`\n**Result:** `{result}`", title="Calculator")
        except ZeroDivisionError:
            await ctx.error("Cannot divide by zero.")
        except Exception as e:
            await ctx.error(f"Error calculating: {str(e)}")

    @commands.command(name="translate", aliases=["tr"], help="Translate text to another language.")
    async def translate(self, ctx, lang: str, *, text: str):
        # Using a free translation API wrapper or direct google translate link
        # For a professional bot, using a proper API is better. 
        # Here we'll use a simple proxy or just provide a link if no reliable free API is found.
        # Let's try a common free endpoint pattern
        encoded_text = urllib.parse.quote(text)
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={lang}&dt=t&q={encoded_text}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return await ctx.error("Failed to connect to Translation service. Make sure you used a valid language code (e.g., `en`, `es`, `fr`).")
                data = await resp.json()

        try:
            translated_text = "".join([s[0] for s in data[0]])
            source_lang = data[2]
            
            embed = self.bot.embed_manager.generic(
                description=translated_text,
                title=f"Translation: {source_lang.upper()} ➔ {lang.upper()}"
            )
            await ctx.send(embed=embed)
        except Exception:
            await ctx.error("Error parsing translation result.")

    @commands.command(name="weather", help="Get weather information for a location.")
    async def weather(self, ctx, *, location: str):
        # We'll use a common free weather API if possible, or a public endpoint
        # For simplicity in this environment, we'll use wttr.in (excellent for bots)
        url = f"https://wttr.in/{urllib.parse.quote(location)}?format=j1"
        
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return await ctx.error("Could not find weather for that location.")
                    data = await resp.json()

        try:
            current = data['current_condition'][0]
            temp_c = current['temp_C']
            temp_f = current['temp_F']
            desc = current['weatherDesc'][0]['value']
            humidity = current['humidity']
            wind = current['windspeedKmph']
            
            area = data['nearest_area'][0]
            city = area['areaName'][0]['value']
            country = area['country'][0]['value']

            embed = self.bot.embed_manager.generic(
                description=f"**Condition:** {desc}\n**Temperature:** {temp_c}°C ({temp_f}°F)\n**Humidity:** {humidity}%\n**Wind:** {wind} km/h",
                title=f"Weather in {city}, {country}"
            )
            await ctx.send(embed=embed)
        except Exception:
            await ctx.error("Error parsing weather data.")

    @commands.command(name="remind", aliases=["reminder"], help="Set a reminder. Usage: `!remind 1h take out trash`")
    async def remind(self, ctx, duration: str, *, task: str):
        # Very simple duration parser (s, m, h, d)
        match = re.match(r"(\d+)([smhd])", duration.lower())
        if not match:
            return await ctx.error("Invalid duration format. Use e.g., `10m`, `1h`, `1d`.")
        
        amount = int(match.group(1))
        unit = match.group(2)
        
        seconds = amount
        if unit == 'm': seconds *= 60
        elif unit == 'h': seconds *= 3600
        elif unit == 'd': seconds *= 86400
        
        if seconds > 2592000: # 30 days limit
            return await ctx.error("Reminders cannot be longer than 30 days.")

        await ctx.success(f"I will remind you about `{task}` in {duration}.")
        
        await asyncio.sleep(seconds)
        
        try:
            embed = self.bot.embed_manager.generic(
                description=f"You asked to be reminded: **{task}**",
                title="Reminder! ⏰"
            )
            await ctx.author.send(embed=embed)
        except:
            # Fallback to channel if DM closed
            await ctx.send(content=ctx.author.mention, embed=embed)

    @commands.command(name="jumbo", aliases=["bigemoji"], help="View a larger version of an emoji.")
    async def jumbo(self, ctx, emoji: str):
        # Match custom emoji format <a:name:id> or <:name:id>
        match = re.search(r"<(a?):([a-zA-Z0-9_]+):([0-9]+)>", emoji)
        if not match:
            return await ctx.error("Please provide a custom Discord emoji.")
        
        is_animated = bool(match.group(1))
        emoji_id = match.group(3)
        extension = "gif" if is_animated else "png"
        url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{extension}?size=1024"
        
        embed = self.bot.embed_manager.generic(description=f"[Download Emoji]({url})", title=f"Emoji: {match.group(2)}")
        embed.set_image(url=url)
        await ctx.send(embed=embed)

    @commands.command(name="poll", help="Create a simple reaction-based poll. Usage: `!poll What is better? Pizza;Burger`")
    async def poll(self, ctx, *, content: str):
        if ";" not in content:
            # Simple Yes/No poll
            question = content
            options = ["👍 Yes", "👎 No"]
            emojis = ["👍", "👎"]
        else:
            parts = content.split(";")
            question = parts[0]
            options_text = parts[1:]
            
            if len(options_text) > 10:
                return await ctx.error("Maximum 10 options allowed.")
            
            emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
            options = []
            for i, opt in enumerate(options_text):
                options.append(f"{emojis[i]} {opt.strip()}")
            emojis = emojis[:len(options)]

        embed = self.bot.embed_manager.generic(
            description="\n".join(options),
            title=f"📊 Poll: {question}"
        )
        embed.set_footer(text=f"Poll by {ctx.author.display_name}")
        
        msg = await ctx.send(embed=embed)
        for emoji in emojis:
            await msg.add_reaction(emoji)

    @commands.command(name="servericon", aliases=["icon", "sicon"], help="View the server's high-resolution icon.")
    async def server_icon(self, ctx):
        if not ctx.guild.icon:
            return await ctx.error("This server does not have an icon.")
        
        url = ctx.guild.icon.url
        embed = self.bot.embed_manager.generic(description=f"[Download Icon]({url})", title=f"Icon: {ctx.guild.name}")
        embed.set_image(url=url)
        await ctx.send(embed=embed)

    @commands.command(name="qr", help="Generate a QR code from a URL or text.")
    async def generate_qr(self, ctx, *, content: str):
        url = f"https://api.qrserver.com/v1/create-qr-code/?size=1024x1024&data={urllib.parse.quote(content)}"
        
        embed = self.bot.embed_manager.generic(description=f"**Content:** `{content}`", title="QR Code Generated")
        embed.set_image(url=url)
        await ctx.send(embed=embed)

    @commands.command(name="shorten", aliases=["tinyurl"], help="Shorten a long URL.")
    async def shorten_url(self, ctx, url: str):
        if not (url.startswith("http://") or url.startswith("https://")):
            return await ctx.error("Please provide a valid URL starting with http:// or https://")

        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                # Using CleanURI - a free, no-key shortener
                async with session.post("https://cleanuri.com/api/v1/shorten", data={"url": url}) as resp:
                    if resp.status != 200:
                        return await ctx.error("Failed to shorten URL. The service might be down.")
                    data = await resp.json()
                    short_url = data['result_url']

        await ctx.success(f"**Original:** <{url}>\n**Shortened:** {short_url}")

    @commands.command(name="screenshot", aliases=["webshot"], help="Take a screenshot of a website.")
    async def screenshot(self, ctx, url: str):
        if not (url.startswith("http://") or url.startswith("https://")):
            url = f"https://{url}"

        async with ctx.typing():
            # Using Thum.io - free tier allows simple screenshots
            ss_url = f"https://image.thum.io/get/width/1200/crop/800/noanimate/{url}"
            
            embed = self.bot.embed_manager.generic(description=f"**URL:** <{url}>", title="Website Screenshot")
            embed.set_image(url=ss_url)
            await ctx.send(embed=embed)

    @commands.command(name="timer", help="Set a quick timer. Usage: `!timer 5m`")
    async def timer(self, ctx, duration: str):
        match = re.match(r"(\d+)([smhd])", duration.lower())
        if not match:
            return await ctx.error("Invalid format. Use e.g., `5m`, `10s`, `1h`.")
        
        amount = int(match.group(1))
        unit = match.group(2)
        seconds = amount
        if unit == 'm': seconds *= 60
        elif unit == 'h': seconds *= 3600
        elif unit == 'd': seconds *= 86400
        
        if seconds > 86400: # 24 hours limit
            return await ctx.error("Timers cannot be longer than 24 hours.")

        await ctx.success(f"Timer set for {duration}!")
        await asyncio.sleep(seconds)
        await ctx.send(f"{ctx.author.mention}, your **{duration}** timer is up!")

    @commands.command(name="wikipedia", aliases=["wiki"], help="Search for a summary on Wikipedia.")
    async def wikipedia_search(self, ctx, *, query: str):
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(query.replace(' ', '_'))}"
        
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 404:
                        return await ctx.error(f"No Wikipedia article found for `{query}`.")
                    if resp.status != 200:
                        return await ctx.error("Failed to connect to Wikipedia.")
                    data = await resp.json()

        embed = self.bot.embed_manager.generic(
            description=data.get('extract', 'No summary available.')[:2000],
            title=f"Wikipedia: {data.get('title', query)}"
        )
        if 'thumbnail' in data:
            embed.set_thumbnail(url=data['thumbnail']['source'])
        
        embed.set_footer(text="Source: en.wikipedia.org")
        await ctx.send(embed=embed)

    @commands.command(name="google", help="Search Google. Usage: `!google how to build a bot` ")
    async def google_search(self, ctx, *, query: str):
        url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        await ctx.info(f"Click the link to view results for: **{query}**\n\n[**Google Search Result**]({url})", title="Google Search")

    @commands.command(name="pingweb", aliases=["webstatus"], help="Check if a website is online.")
    async def ping_web(self, ctx, url: str):
        if not (url.startswith("http://") or url.startswith("https://")):
            url = f"https://{url}"
            
        async with ctx.typing():
            try:
                async with aiohttp.ClientSession() as session:
                    start = time.monotonic()
                    async with session.get(url, timeout=10) as resp:
                        end = time.monotonic()
                        latency = round((end - start) * 1000)
                        status = "Online ✅" if resp.status < 400 else f"Error ❌ ({resp.status})"
                        await ctx.info(f"**URL:** {url}\n**Status:** {status}\n**Response Time:** `{latency}ms`", title="Web Ping")
            except Exception as e:
                await ctx.error(f"Failed to connect to `{url}`: {str(e)}")

    @commands.command(name="base64", help="Encode or decode text in Base64. Usage: `!base64 encode hello` or `!base64 decode aGVsbG8=`")
    async def base64_cmd(self, ctx, action: str, *, text: str):
        if action.lower() == "encode":
            result = base64.b64encode(text.encode()).decode()
            await ctx.info(f"**Result:** `{result}`", title="Base64 Encode")
        elif action.lower() == "decode":
            try:
                result = base64.b64decode(text.encode()).decode()
                await ctx.info(f"**Result:** `{result}`", title="Base64 Decode")
            except:
                await ctx.error("Invalid Base64 string.")
        else:
            await ctx.error("Action must be `encode` or `decode`.")

    @commands.command(name="binary", help="Convert text to binary or vice versa. Usage: `!binary encode hello` ")
    async def binary_cmd(self, ctx, action: str, *, text: str):
        if action.lower() == "encode":
            result = ' '.join(format(ord(x), '08b') for x in text)
            await ctx.info(f"**Result:** `{result}`", title="Binary Encode")
        elif action.lower() == "decode":
            try:
                binary_values = text.split()
                ascii_string = ""
                for binary_value in binary_values:
                    an_integer = int(binary_value, 2)
                    ascii_character = chr(an_integer)
                    ascii_string += ascii_character
                await ctx.info(f"**Result:** `{ascii_string}`", title="Binary Decode")
            except:
                await ctx.error("Invalid binary sequence.")
        else:
            await ctx.error("Action must be `encode` or `decode`.")

    @commands.command(name="color", help="View a preview of a hex color.")
    async def color_preview(self, ctx, hex_code: str):
        clean_hex = hex_code.replace("#", "").upper()
        if len(clean_hex) != 6:
            return await ctx.error("Hex code must be 6 characters long (e.g., `#8A63FF`).")
            
        url = f"https://singlecolorimage.com/get/{clean_hex}/200x200"
        embed = self.bot.embed_manager.generic(
            description=f"**HEX:** `#{clean_hex}`\n**RGB:** `{tuple(int(clean_hex[i:i+2], 16) for i in (0, 2, 4))}`",
            title=f"Color: #{clean_hex}",
            color=int(clean_hex, 16)
        )
        embed.set_thumbnail(url=url)
        await ctx.send(embed=embed)

    @commands.command(name="genpw", aliases=["password", "genpass"], help="Generate a secure random password.")
    async def gen_password(self, ctx, length: int = 16):
        if length > 200: return await ctx.error("Maximum length is 200.")
        import string
        chars = string.ascii_letters + string.digits + string.punctuation
        password = "".join(random.choice(chars) for _ in range(length))
        
        try:
            await ctx.author.send(embed=self.bot.embed_manager.success(f"Your generated password: `{password}`", title="Secure Password"))
            await ctx.success("Password sent to your DMs!")
        except:
            await ctx.error("Your DMs are closed! I couldn't send the password.")

    @commands.command(name="timestamp", aliases=["ts"], help="Convert a specific time to Discord timestamp format.")
    async def timestamp_gen(self, ctx, *, time_str: str = "now"):
        # Very basic parser, 'now' or 'YYYY-MM-DD HH:MM:SS'
        try:
            if time_str.lower() == "now":
                dt = datetime.datetime.now()
            else:
                dt = datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            
            ts = int(dt.timestamp())
            embed = self.bot.embed_manager.generic(
                description=(
                    f"**Relative:** `<t:{ts}:R>` → <t:{ts}:R>\n"
                    f"**Short Time:** `<t:{ts}:t>` → <t:{ts}:t>\n"
                    f"**Long Time:** `<t:{ts}:T>` → <t:{ts}:T>\n"
                    f"**Short Date:** `<t:{ts}:d>` → <t:{ts}:d>\n"
                    f"**Long Date:** `<t:{ts}:D>` → <t:{ts}:D>\n"
                    f"**Short Date/Time:** `<t:{ts}:f>` → <t:{ts}:f>\n"
                    f"**Long Date/Time:** `<t:{ts}:F>` → <t:{ts}:F>"
                ),
                title="Discord Timestamps"
            )
            await ctx.send(embed=embed)
        except Exception:
            await ctx.error("Invalid format. Use `YYYY-MM-DD HH:MM:SS` or `now`.")

    @commands.command(name="permissions", aliases=["perms"], help="View permissions of a user or role in the current channel.")
    async def view_permissions(self, ctx, target: discord.Member | discord.Role = None):
        target = target or ctx.author
        perms = ctx.channel.permissions_for(target)
        
        allowed = []
        denied = []
        
        for name, value in perms:
            name = name.replace('_', ' ').title()
            if value: allowed.append(f"✅ {name}")
            else: denied.append(f"❌ {name}")
            
        embed = self.bot.embed_manager.generic(
            description=f"Showing permissions for {target.mention} in {ctx.channel.mention}",
            title="Channel Permissions"
        )
        # Split into two fields to avoid character limit
        embed.add_field(name="Allowed", value="\n".join(allowed[:20]) or "None", inline=True)
        embed.add_field(name="Denied", value="\n".join(denied[:20]) or "None", inline=True)
        
        await ctx.send(embed=embed)

    @commands.command(name="crypto", help="Check the current price of a cryptocurrency (e.g. BTC, ETH).")
    async def crypto_price(self, ctx, symbol: str = "BTC"):
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={symbol.lower()}&vs_currencies=usd"
        # CoinGecko uses IDs not symbols for simple price, but let's try a common mapping or just use a different API
        # Better: use Cryptocompare or similar
        url = f"https://min-api.cryptocompare.com/data/price?fsym={symbol.upper()}&tsyms=USD,EUR,GBP"
        
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return await ctx.error("Failed to fetch crypto data.")
                    data = await resp.json()
        
        if "Response" in data and data["Response"] == "Error":
            return await ctx.error(f"Could not find cryptocurrency: `{symbol}`")

        embed = self.bot.embed_manager.generic(
            description=f"**USD:** `${data['USD']:,}`\n**EUR:** `€{data['EUR']:,}`\n**GBP:** `£{data['GBP']:,}`",
            title=f"Crypto Price: {symbol.upper()}"
        )
        embed.set_thumbnail(url="https://cdn.pixabay.com/photo/2017/01/25/12/31/bitcoin-2007769_1280.png")
        await ctx.send(embed=embed)

    @commands.command(name="idinfo", aliases=["id"], help="Get information from a Discord ID.")
    async def id_info(self, ctx, discord_id: int):
        try:
            # Snowflake logic to get creation date
            created_at = discord.utils.snowflake_time(discord_id)
            
            embed = self.bot.embed_manager.generic(
                description=(
                    f"**ID:** `{discord_id}`\n"
                    f"**Created At:** <t:{int(created_at.timestamp())}:F>\n"
                    f"**Relative:** <t:{int(created_at.timestamp())}:R>"
                ),
                title="ID Information"
            )
            await ctx.send(embed=embed)
        except Exception:
            await ctx.error("Invalid Discord ID.")

    @commands.command(name="hasinvite", aliases=["inviteinfo"], help="Get information about a Discord invite link.")
    async def invite_info(self, ctx, invite: discord.Invite):
        embed = self.bot.embed_manager.generic(
            description=(
                f"**Guild:** {invite.guild.name} ({invite.guild.id})\n"
                f"**Channel:** #{invite.channel.name}\n"
                f"**Inviter:** {invite.inviter}\n"
                f"**Members:** {invite.approximate_member_count}\n"
                f"**Online:** {invite.approximate_presence_count}"
            ),
            title="Invite Information"
        )
        if invite.guild.icon: embed.set_thumbnail(url=invite.guild.icon.url)
        await ctx.send(embed=embed)

    @commands.command(name="userbanner", aliases=["ubanner"], help="View a users banner.")
    async def user_banner(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        user = await self.bot.fetch_user(member.id)
        if not user.banner:
            return await ctx.error(f"{member.name} does not have a banner.")
        
        url = user.banner.url
        embed = self.bot.embed_manager.generic(description=f"[Download Banner]({url})", title=f"Banner: {member.name}")
        embed.set_image(url=url)
        await ctx.send(embed=embed)

    @commands.command(name="emojilist", aliases=["emojis"], help="View all emojis in the server.")
    async def emoji_list(self, ctx):
        emojis = [str(e) for e in ctx.guild.emojis]
        if not emojis: return await ctx.info("This server has no custom emojis.")
        
        # Paginate if too many emojis
        pages = []
        chunk_size = 50
        for i in range(0, len(emojis), chunk_size):
            pages.append(" ".join(emojis[i:i+chunk_size]))
            
        embed = self.bot.embed_manager.generic(description=pages[0], title=f"Server Emojis ({len(emojis)})")
        if len(pages) > 1:
            embed.set_footer(text=f"Showing page 1 of {len(pages)}")
        await ctx.send(embed=embed)

    @commands.command(name="rolelist", aliases=["roles"], help="View all roles in the server.")
    async def role_list(self, ctx):
        roles = sorted(ctx.guild.roles, key=lambda r: r.position, reverse=True)
        # Filter out @everyone
        roles = [r.mention for r in roles if r.name != "@everyone"]
        
        if not roles: return await ctx.info("This server has no custom roles.")
        
        pages = []
        chunk_size = 20
        for i in range(0, len(roles), chunk_size):
            pages.append("\n".join(roles[i:i+chunk_size]))
            
        embed = self.bot.embed_manager.generic(description=pages[0], title=f"Server Roles ({len(roles)})")
        if len(pages) > 1:
            embed.set_footer(text=f"Showing page 1 of {len(pages)}")
        await ctx.send(embed=embed)

    @commands.command(name="firstmessage", aliases=["firstmsg"], help="Get a link to the first message in the current channel.")
    async def first_message(self, ctx):
        async for message in ctx.channel.history(limit=1, oldest_first=True):
            await ctx.info(f"The first message in this channel was sent by {message.author.mention}.\n\n[**Jump to Message**]({message.jump_url})", title="First Message")
            return

    @commands.command(name="serversplash", aliases=["splash"], help="View the server's invite splash image.")
    async def server_splash(self, ctx):
        if not ctx.guild.splash:
            return await ctx.error("This server does not have an invite splash image.")
        
        url = ctx.guild.splash.url
        embed = self.bot.embed_manager.generic(description=f"[Download Splash]({url})", title=f"Splash: {ctx.guild.name}")
        embed.set_image(url=url)
        await ctx.send(embed=embed)

    @commands.command(name="roleicon", help="View a high-resolution icon of a role.")
    async def role_icon(self, ctx, *, role: discord.Role):
        if not role.display_icon:
            return await ctx.error("This role does not have an icon.")
        
        url = role.display_icon.url if hasattr(role.display_icon, 'url') else str(role.display_icon)
        embed = self.bot.embed_manager.generic(description=f"[Download Icon]({url})", title=f"Role Icon: {role.name}")
        embed.set_image(url=url)
        await ctx.send(embed=embed)

    @commands.command(name="serverdiscovery", aliases=["discovery"], help="View the server's discovery splash image.")
    async def server_discovery(self, ctx):
        if not ctx.guild.discovery_splash:
            return await ctx.error("This server does not have a discovery splash image.")
        
        url = ctx.guild.discovery_splash.url
        embed = self.bot.embed_manager.generic(description=f"[Download Discovery Splash]({url})", title=f"Discovery Splash: {ctx.guild.name}")
        embed.set_image(url=url)
        await ctx.send(embed=embed)

    @commands.command(name="randomuser", aliases=["ruser"], help="Pick a random user from the server.")
    async def random_user(self, ctx):
        user = random.choice(ctx.guild.members)
        await ctx.info(f"The lucky user is: {user.mention} (`{user.id}`)", title="Random User")

    @commands.command(name="randomcolor", aliases=["rcolor"], help="Generate a random hex color.")
    async def random_color(self, ctx):
        color = "".join([random.choice("0123456789ABCDEF") for _ in range(6)])
        await self.color_preview(ctx, color)

    @commands.command(name="serverid", help="Get the current server's ID.")
    async def server_id_cmd(self, ctx):
        await ctx.send(f"`{ctx.guild.id}`")

    @commands.command(name="channelid", help="Get the current channel's ID.")
    async def channel_id_cmd(self, ctx, channel: discord.abc.GuildChannel = None):
        channel = channel or ctx.channel
        await ctx.send(f"`{channel.id}`")

    @commands.command(name="roleid", help="Get the ID of a role.")
    async def role_id_cmd(self, ctx, *, role: discord.Role):
        await ctx.send(f"`{role.id}`")

    @commands.command(name="userid", help="Get the ID of a user.")
    async def user_id_cmd(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        await ctx.send(f"`{member.id}`")

    @commands.command(name="invitelist", help="List all active invites in the server.")
    @commands.has_permissions(manage_guild=True)
    async def invite_list(self, ctx):
        invites = await ctx.guild.invites()
        if not invites: return await ctx.info("This server has no active invites.")
        
        desc = "\n".join([f"• `{i.code}` - {i.channel.mention} (Uses: {i.uses})" for i in invites[:20]])
        if len(invites) > 20: desc += f"\n... and {len(invites) - 20} more."
        
        await ctx.embed(desc, title=f"Server Invites ({len(invites)})")

    @commands.command(name="botinvite", aliases=["binvite"], help="Get the bot's invite link.")
    async def invite_bot_cmd(self, ctx):
        await ctx.info(f"Invite me to your server!\n\n[**Click Here to Invite**]({self.bot.config.INVITE_LINK})", title="Bot Invite")

    @commands.command(name="uptime", help="Show how long the bot has been online.")
    async def uptime_cmd(self, ctx):
        uptime = str(datetime.timedelta(seconds=int(round(time.time() - self.bot.get_cog('Information').start_time))))
        await ctx.info(f"Bot has been online for: `{uptime}`", title="Bot Uptime")

    @commands.command(name="inrole", help="List all members with a specific role.")
    async def members_in_role(self, ctx, *, role: discord.Role):
        members = role.members
        if not members: return await ctx.info(f"No members have the {role.mention} role.")
        
        desc = "\n".join([f"• {m.mention} ({m.id})" for m in members[:20]])
        if len(members) > 20: desc += f"\n... and {len(members) - 20} more."
        
        await ctx.embed(desc, title=f"Members with Role: {role.name} ({len(members)})")

    @commands.command(name="roleperms", aliases=["rp"], help="List all permissions of a specific role.")
    async def role_permissions_list(self, ctx, *, role: discord.Role):
        perms = [p[0].replace('_', ' ').title() for p in role.permissions if p[1]]
        if not perms: return await ctx.info(f"The {role.mention} role has no permissions.")
        
        desc = "\n".join([f"✅ {p}" for p in perms])
        await ctx.embed(desc, title=f"Permissions for Role: {role.name}")

    @commands.command(name="shard", help="View shard information for this server.")
    async def shard_info(self, ctx):
        shard = self.bot.get_shard(ctx.guild.shard_id)
        await ctx.info(f"**Shard ID:** `{ctx.guild.shard_id}`\n**Status:** `Connected`\n**Latency:** `{round(shard.latency * 1000)}ms`", title="Shard Information")

    @commands.command(name="shards", help="View information for all bot shards.")
    async def shards_info(self, ctx):
        desc = ""
        for shard_id, shard in self.bot.shards.items():
            status = "Online ✅" if not shard.is_closed() else "Offline ❌"
            desc += f"**Shard {shard_id}:** {status} (`{round(shard.latency * 1000)}ms`)\n"
            
        await ctx.embed(desc, title=f"Bot Shards ({len(self.bot.shards)})")

    @commands.command(name="dictionary", aliases=["define"], help="Get the definition of a word.")
    async def dictionary_search(self, ctx, *, word: str):
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{urllib.parse.quote(word)}"
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 404:
                        return await ctx.error(f"No definition found for `{word}`.")
                    if resp.status != 200:
                        return await ctx.error("Failed to connect to the Dictionary service.")
                    data = await resp.json()

        entry = data[0]
        meaning = entry['meanings'][0]
        definition = meaning['definitions'][0]['definition']
        
        embed = self.bot.embed_manager.generic(
            description=f"**Type:** {meaning['partOfSpeech']}\n\n**Definition:**\n{definition}",
            title=f"Dictionary: {entry['word'].capitalize()}"
        )
        if 'phonetic' in entry: embed.set_footer(text=f"Phonetic: {entry['phonetic']}")
        await ctx.send(embed=embed)

    @commands.command(name="country", help="Get information about a country.")
    async def country_info(self, ctx, *, country: str):
        url = f"https://restcountries.com/v3.1/name/{urllib.parse.quote(country)}"
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 404:
                        return await ctx.error(f"Could not find country: `{country}`")
                    if resp.status != 200:
                        return await ctx.error("Failed to connect to the Country API.")
                    data = await resp.json()

        c = data[0]
        name = c['name']['common']
        capital = c.get('capital', ['None'])[0]
        region = c['region']
        pop = c['population']
        flag = c['flags']['png']
        
        embed = self.bot.embed_manager.generic(
            description=(
                f"🌍 **Capital:** {capital}\n"
                f"📍 **Region:** {region}\n"
                f"👥 **Population:** {pop:,}\n"
                f"🏳️ **Official Name:** {c['name']['official']}"
            ),
            title=f"Country Info: {name}"
        )
        embed.set_thumbnail(url=flag)
        await ctx.send(embed=embed)

    @commands.command(name="timezone", aliases=["time"], help="Get the current time in a city.")
    async def timezone_cmd(self, ctx, *, city: str):
        # We'll use the worldtimeapi.org
        url = f"http://worldtimeapi.org/api/timezone"
        # This API requires full paths (Area/City), but we can search or just use a simpler one
        # Let's use wttr.in which also provides time/location info simply
        url = f"https://wttr.in/{urllib.parse.quote(city)}?format=%T+%Z"
        
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return await ctx.error("Could not find timezone for that location.")
                    data = await resp.text()

        await ctx.info(f"Current time in **{city.title()}**:\n`{data.strip()}`", title="World Clock 🕰️")

    @commands.command(name="github", aliases=["gh"], help="Search for a user on GitHub.")
    async def github_search(self, ctx, *, username: str):
        url = f"https://api.github.com/users/{urllib.parse.quote(username)}"
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 404:
                        return await ctx.error(f"No GitHub user found: `{username}`")
                    data = await resp.json()

        embed = self.bot.embed_manager.generic(
            description=(
                f"**Bio:** {data.get('bio', 'No bio.')}\n"
                f"**Followers:** {data['followers']} | **Following:** {data['following']}\n"
                f"**Public Repos:** {data['public_repos']}\n"
                f"**Location:** {data.get('location', 'Unknown')}"
            ),
            title=f"GitHub Profile: {data['login']}"
        )
        embed.set_thumbnail(url=data['avatar_url'])
        embed.add_field(name="Link", value=f"[Click Here]({data['html_url']})")
        await ctx.send(embed=embed)

    @commands.command(name="minecraft", aliases=["mcserver"], help="Check the status of a Minecraft server.")
    async def minecraft_server(self, ctx, ip: str):
        url = f"https://api.mcsrvstat.us/2/{urllib.parse.quote(ip)}"
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return await ctx.error("Failed to connect to Minecraft status service.")
                    data = await resp.json()

        if not data.get('online'):
            return await ctx.error(f"The server `{ip}` is currently offline.")

        players_online = data['players']['online']
        players_max = data['players']['max']
        version = data.get('version', 'Unknown')
        motd = "\n".join(data.get('motd', {}).get('clean', []))
        
        embed = self.bot.embed_manager.generic(
            description=f"**MOTD:**\n```{motd}```\n**Players:** `{players_online}/{players_max}`\n**Version:** `{version}`",
            title=f"Minecraft Server: {ip}"
        )
        embed.set_thumbnail(url=f"https://api.mcsrvstat.us/icon/{ip}")
        await ctx.send(embed=embed)

    @commands.command(name="ipinfo", aliases=["geoip"], help="Get information about an IP address.")
    async def ip_info_real(self, ctx, ip: str):
        url = f"http://ip-api.com/json/{urllib.parse.quote(ip)}"
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return await ctx.error("Failed to connect to IP information service.")
                    data = await resp.json()

        if data.get('status') == 'fail':
            return await ctx.error(f"Failed to find info for `{ip}`: {data.get('message')}")

        embed = self.bot.embed_manager.generic(
            description=(
                f"**Country:** {data.get('country')} ({data.get('countryCode')})\n"
                f"**City:** {data.get('city')}\n"
                f"**ISP:** {data.get('isp')}\n"
                f"**Org:** {data.get('org')}\n"
                f"**Timezone:** {data.get('timezone')}"
            ),
            title=f"IP Info: {ip}"
        )
        await ctx.send(embed=embed)

    @commands.command(name="anime", help="Search for information about an anime.")
    async def anime_search(self, ctx, *, title: str):
        url = f"https://api.jikan.moe/v4/anime?q={urllib.parse.quote(title)}&limit=1"
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return await ctx.error("Failed to connect to Anime service.")
                    data = await resp.json()

        if not data['data']:
            return await ctx.error(f"No anime found for `{title}`.")

        anime = data['data'][0]
        title_display = anime['title_english'] or anime['title']
        
        embed = self.bot.embed_manager.generic(
            description=anime.get('synopsis', 'No description available.')[:1000] + "...",
            title=f"Anime: {title_display}"
        )
        embed.add_field(name="Episodes", value=f"`{anime.get('episodes', 'Unknown')}`", inline=True)
        embed.add_field(name="Score", value=f"`⭐ {anime.get('score', 'N/A')}`", inline=True)
        embed.add_field(name="Status", value=f"`{anime.get('status', 'Unknown')}`", inline=True)
        if anime.get('images'): embed.set_image(url=anime['images']['jpg']['large_image_url'])
        
        await ctx.send(embed=embed)

    @commands.command(name="manga", help="Search for information about a manga.")
    async def manga_search(self, ctx, *, title: str):
        url = f"https://api.jikan.moe/v4/manga?q={urllib.parse.quote(title)}&limit=1"
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return await ctx.error("Failed to connect to Manga service.")
                    data = await resp.json()

        if not data['data']:
            return await ctx.error(f"No manga found for `{title}`.")

        manga = data['data'][0]
        
        embed = self.bot.embed_manager.generic(
            description=manga.get('synopsis', 'No description available.')[:1000] + "...",
            title=f"Manga: {manga['title']}"
        )
        embed.add_field(name="Chapters", value=f"`{manga.get('chapters', 'Unknown')}`", inline=True)
        embed.add_field(name="Volumes", value=f"`{manga.get('volumes', 'Unknown')}`", inline=True)
        embed.add_field(name="Score", value=f"`⭐ {manga.get('score', 'N/A')}`", inline=True)
        if manga.get('images'): embed.set_image(url=manga['images']['jpg']['large_image_url'])
        
        await ctx.send(embed=embed)

    @commands.command(name="currency", aliases=["convert"], help="Convert currency. Usage: `!currency 100 USD EUR` ")
    async def convert_currency(self, ctx, amount: float, from_curr: str, to_curr: str):
        url = f"https://api.exchangerate-api.com/v4/latest/{from_curr.upper()}"
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return await ctx.error(f"Invalid currency code: `{from_curr}`")
                    data = await resp.json()

        rates = data.get('rates', {})
        if to_curr.upper() not in rates:
            return await ctx.error(f"Invalid currency code: `{to_curr}`")
            
        rate = rates[to_curr.upper()]
        result = amount * rate
        
        await ctx.info(f"**{amount:,} {from_curr.upper()}** ➔ **{result:,.2f} {to_curr.upper()}**\nRate: `{rate}`", title="Currency Converter")

    @commands.command(name="pypi", help="Search for a Python package on PyPI.")
    async def pypi_search(self, ctx, *, package: str):
        url = f"https://pypi.org/pypi/{urllib.parse.quote(package)}/json"
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 404:
                        return await ctx.error(f"No PyPI package found: `{package}`")
                    data = await resp.json()

        info = data['info']
        embed = self.bot.embed_manager.generic(
            description=info.get('summary', 'No description available.'),
            title=f"PyPI: {info['name']} v{info['version']}"
        )
        embed.add_field(name="Author", value=info.get('author') or "Unknown", inline=True)
        embed.add_field(name="License", value=info.get('license') or "Unknown", inline=True)
        embed.add_field(name="Link", value=f"[PyPI Page]({info['package_url']})", inline=True)
        await ctx.send(embed=embed)

    @commands.command(name="npm", help="Search for an NPM package.")
    async def npm_search(self, ctx, *, package: str):
        url = f"https://registry.npmjs.org/{urllib.parse.quote(package)}"
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 404:
                        return await ctx.error(f"No NPM package found: `{package}`")
                    data = await resp.json()

        version = data.get('dist-tags', {}).get('latest', 'Unknown')
        latest_data = data.get('versions', {}).get(version, {})
        
        embed = self.bot.embed_manager.generic(
            description=data.get('description', 'No description available.'),
            title=f"NPM: {data['name']} v{version}"
        )
        if 'homepage' in data: embed.add_field(name="Website", value=f"[Click Here]({data['homepage']})", inline=True)
        embed.add_field(name="Maintainers", value=len(data.get('maintainers', [])), inline=True)
        await ctx.send(embed=embed)

    @commands.command(name="itunes", help="Search for a song or artist on iTunes.")
    async def itunes_search(self, ctx, *, query: str):
        url = f"https://itunes.apple.com/search?term={urllib.parse.quote(query)}&limit=1&entity=song"
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return await ctx.error("Failed to connect to iTunes service.")
                    data = await resp.json()

        if not data['results']:
            return await ctx.error(f"No results found for `{query}`.")

        result = data['results'][0]
        embed = self.bot.embed_manager.generic(
            description=f"**Artist:** {result['artistName']}\n**Album:** {result['collectionName']}\n**Release Date:** {result['releaseDate'][:10]}",
            title=f"iTunes: {result['trackName']}"
        )
        embed.set_thumbnail(url=result['artworkUrl100'].replace("100x100", "512x512"))
        embed.add_field(name="Link", value=f"[Listen on Apple Music]({result['trackViewUrl']})")
        await ctx.send(embed=embed)

    @commands.command(name="githubrepo", aliases=["ghrepo"], help="Search for a GitHub repository.")
    async def github_repo_search(self, ctx, owner: str, repo: str):
        url = f"https://api.github.com/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(repo)}"
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 404:
                        return await ctx.error(f"Repository `{owner}/{repo}` not found.")
                    data = await resp.json()

        embed = self.bot.embed_manager.generic(
            description=data.get('description', 'No description.'),
            title=f"GitHub: {data['full_name']}"
        )
        embed.add_field(name="Stars", value=f"⭐ {data['stargazers_count']:,}", inline=True)
        embed.add_field(name="Forks", value=f"🍴 {data['forks_count']:,}", inline=True)
        embed.add_field(name="Language", value=f"💻 {data.get('language', 'Unknown')}", inline=True)
        embed.add_field(name="License", value=data.get('license', {}).get('name', 'None') if data.get('license') else 'None', inline=True)
        embed.add_field(name="Link", value=f"[View on GitHub]({data['html_url']})", inline=False)
        embed.set_thumbnail(url=data['owner']['avatar_url'])
        await ctx.send(embed=embed)

    @commands.command(name="whois", aliases=["domain"], help="Get registration info for a domain.")
    async def whois_domain(self, ctx, domain: str):
        url = f"https://whois.enclout.com/api/v1/whois/show?domain={urllib.parse.quote(domain)}"
        # Free API might be limited, let's use a simpler one if possible.
        # rdap.org is standard and free
        url = f"https://rdap.org/domain/{urllib.parse.quote(domain)}"
        
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 404:
                        return await ctx.error(f"Domain `{domain}` not found.")
                    if resp.status != 200:
                        return await ctx.error("Failed to fetch WHOIS data.")
                    data = await resp.json()

        events = {e['eventAction']: e['eventDate'] for e in data.get('events', [])}
        created = events.get('registration', 'Unknown')
        
        embed = self.bot.embed_manager.generic(
            description=f"**Domain:** {domain.upper()}\n**Created:** {created}\n**Registrar:** {data.get('entities', [{}])[0].get('vcardArray', [[None, [['fn', {}, 'text', 'Unknown']]]])[1][0][3]}",
            title="WHOIS Domain Lookup"
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Utility(bot))
