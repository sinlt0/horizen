import discord
from discord.ext import commands
import asyncio
import random
import datetime
import unicodedata
import base64
import re

class TextTools(commands.Cog):
    category = 'utility'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager
        self._stopwatches = {}
        self._todos = {}

    @commands.command(name='encode', help='Encode text to Base64.')
    async def encode(self, ctx, *, text: str):
        encoded = base64.b64encode(text.encode()).decode()
        await ctx.send(f'```\n{encoded}\n```')

    @commands.command(name='decode', help='Decode Base64 text.')
    async def decode(self, ctx, *, text: str):
        try:
            decoded = base64.b64decode(text.encode()).decode()
            await ctx.send(f'```\n{decoded}\n```')
        except Exception:
            await ctx.error('Invalid Base64 string.')

    @commands.command(name='uppercase', aliases=['upper'], help='Convert text to UPPERCASE.')
    async def uppercase(self, ctx, *, text: str):
        await ctx.send(text.upper())

    @commands.command(name='lowercase', aliases=['lower'], help='Convert text to lowercase.')
    async def lowercase(self, ctx, *, text: str):
        await ctx.send(text.lower())

    @commands.command(name='bold', help='Make text **bold** in Discord markdown.')
    async def bold(self, ctx, *, text: str):
        await ctx.send(f'**{text}**')

    @commands.command(name='italic', help='Make text *italic* in Discord markdown.')
    async def italic(self, ctx, *, text: str):
        await ctx.send(f'*{text}*')

    @commands.command(name='strikethrough', aliases=['strike'], help='Make text ~~strikethrough~~ in Discord markdown.')
    async def strikethrough(self, ctx, *, text: str):
        await ctx.send(f'~~{text}~~')

    @commands.command(name='monospace', aliases=['mono', 'code'], help='Make text `monospace` in Discord markdown.')
    async def monospace(self, ctx, *, text: str):
        await ctx.send(f'`{text}`')

    @commands.command(name='spoilertext', aliases=['spoiler'], help='Wrap text in a spoiler tag.')
    async def spoilertext(self, ctx, *, text: str):
        await ctx.send(f'||{text}||')

    @commands.command(name='superscript', help='Convert text to superscript Unicode characters.')
    async def superscript(self, ctx, *, text: str):
        table = str.maketrans('abcdefghijklmnoprstuvwxyz0123456789', 'ᵃᵇᶜᵈᵉᶠᵍʰⁱʲᵏˡᵐⁿᵒᵖʳˢᵗᵘᵛʷˣʸᶻ⁰¹²³⁴⁵⁶⁷⁸⁹')
        await ctx.send(text.lower().translate(table))

    @commands.command(name='subscript', help='Convert text to subscript Unicode characters.')
    async def subscript(self, ctx, *, text: str):
        table = str.maketrans('abeiouv0123456789', 'ₐᵦₑᵢₒᵤᵥ₀₁₂₃₄₅₆₇₈₉')
        await ctx.send(text.lower().translate(table))

    @commands.command(name='zalgo', help='Convert text to z̵͔͔͋͊a̤̒l̝̿g̮̺͑o̬͖̓ text.')
    async def zalgo(self, ctx, *, text: str):
        combining = [chr(c) for c in range(0x0300, 0x036F)]
        result = ''
        for char in text:
            result += char
            if char != ' ':
                result += ''.join(random.choices(combining, k=random.randint(2, 6)))
        await ctx.send(result[:500])

    @commands.command(name='unzalgo', help='Strip zalgo combining characters from text.')
    async def unzalgo(self, ctx, *, text: str):
        cleaned = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        await ctx.send(cleaned or 'Nothing left after cleaning.')

    @commands.command(name='wordcount', aliases=['wc'], help='Count the words in a message.')
    async def wordcount(self, ctx, *, text: str):
        words = len(text.split())
        chars = len(text)
        chars_no_space = len(text.replace(' ', ''))
        embed = self.bot.embed_manager.generic(
            description=f'**Words:** `{words}`\n**Characters:** `{chars}`\n**Chars (no spaces):** `{chars_no_space}`',
            title='Word Count'
        )
        await ctx.send(embed=embed)

    @commands.command(name='lettercount', aliases=['lc'], help='Count the occurrences of each letter in text.')
    async def lettercount(self, ctx, *, text: str):
        freq = {}
        for c in text.lower():
            if c.isalpha():
                freq[c] = freq.get(c, 0) + 1
        if not freq:
            return await ctx.error('No letters found.')
        sorted_freq = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        desc = ' '.join([f'`{c}:{n}`' for c, n in sorted_freq[:30]])
        embed = self.bot.embed_manager.generic(description=desc, title='Letter Frequency')
        await ctx.send(embed=embed)

    @commands.command(name='calculate', aliases=['calc2', 'math2'], help='Evaluate a math expression safely.')
    async def calculate(self, ctx, *, expression: str):
        allowed = set('0123456789+-*/().% ')
        if not all(c in allowed for c in expression):
            return await ctx.error('Only basic math operators allowed.')
        try:
            result = eval(expression, {"__builtins__": {}})
            await ctx.send(f'`{expression}` = **{result}**')
        except Exception:
            await ctx.error('Invalid expression.')

    @commands.command(name='rng', aliases=['random'], help='Generate a random number between two values.')
    async def rng(self, ctx, low: int, high: int):
        if low >= high:
            return await ctx.error('First number must be less than the second.')
        result = random.randint(low, high)
        embed = self.bot.embed_manager.generic(
            description=f'Range: `{low}` — `{high}`\nResult: **{result}**',
            title='🎲 Random Number'
        )
        await ctx.send(embed=embed)

    @commands.command(name='stopwatch', aliases=['sw'], help='Start or stop a stopwatch.')
    async def stopwatch(self, ctx):
        uid = ctx.author.id
        if uid in self._stopwatches:
            elapsed = (datetime.datetime.utcnow() - self._stopwatches.pop(uid)).total_seconds()
            m, s = divmod(int(elapsed), 60)
            h, m = divmod(m, 60)
            await ctx.success(f'⏱️ Stopped! Time: `{h:02d}:{m:02d}:{s:02d}`')
        else:
            self._stopwatches[uid] = datetime.datetime.utcnow()
            await ctx.success('⏱️ Stopwatch started! Run again to stop.')

    @commands.command(name='timer2', aliases=['countdown'], help='Set a countdown timer. Usage: timer2 30s Do the thing')
    async def timer2(self, ctx, duration: str, *, label: str = 'Timer'):
        match = re.match(r'(\d+)([smh])', duration.lower())
        if not match:
            return await ctx.error('Invalid duration. Use `30s`, `5m`, `1h`.')
        amount, unit = int(match.group(1)), match.group(2)
        seconds = amount * {'s': 1, 'm': 60, 'h': 3600}[unit]
        if seconds > 3600:
            return await ctx.error('Maximum timer duration is 1 hour.')
        await ctx.success(f'⏲️ Timer set for `{duration}` — **{label}**')
        await asyncio.sleep(seconds)
        await ctx.send(f'⏲️ {ctx.author.mention} — **{label}** timer done!')

    @commands.command(name='remindme', help='Set a personal reminder. Usage: remindme 1h Take a break')
    async def remindme(self, ctx, duration: str, *, reminder: str):
        match = re.match(r'(\d+)([smhd])', duration.lower())
        if not match:
            return await ctx.error('Invalid duration. Use `30m`, `2h`, `1d`.')
        amount, unit = int(match.group(1)), match.group(2)
        seconds = amount * {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}[unit]
        if seconds > 604800:
            return await ctx.error('Maximum reminder duration is 7 days.')
        fire_at = int(datetime.datetime.utcnow().timestamp()) + seconds
        data = await self.db.find_one('reminders', {'_id': ctx.author.id}) or {'_id': ctx.author.id, 'reminders': []}
        rid = len(data['reminders']) + 1
        data['reminders'].append({'id': rid, 'content': reminder, 'channel': ctx.channel.id, 'at': fire_at})
        await self.db.update_one('reminders', {'_id': ctx.author.id}, data, upsert=True)
        await ctx.success(f'⏰ Reminder set for <t:{fire_at}:R> — **{reminder}**')

        async def fire():
            await asyncio.sleep(seconds)
            try:
                channel = self.bot.get_channel(ctx.channel.id)
                if channel:
                    await channel.send(f'⏰ {ctx.author.mention} — Reminder: **{reminder}**')
                data2 = await self.db.find_one('reminders', {'_id': ctx.author.id}) or {}
                data2['reminders'] = [r for r in data2.get('reminders', []) if r['id'] != rid]
                await self.db.update_one('reminders', {'_id': ctx.author.id}, data2, upsert=True)
            except Exception:
                pass

        self.bot.loop.create_task(fire())

    @commands.command(name='reminders', help='List your active reminders.')
    async def reminders(self, ctx):
        data = await self.db.find_one('reminders', {'_id': ctx.author.id})
        if not data or not data.get('reminders'):
            return await ctx.info('You have no active reminders.')
        now = int(datetime.datetime.utcnow().timestamp())
        active = [r for r in data['reminders'] if r['at'] > now]
        if not active:
            return await ctx.info('You have no active reminders.')
        desc = '\n'.join([f'`{r["id"]}.` <t:{r["at"]}:R> — {r["content"]}' for r in active])
        embed = self.bot.embed_manager.generic(description=desc, title='⏰ Your Reminders')
        await ctx.send(embed=embed)

    @commands.command(name='delreminder', help='Delete a reminder by its ID.')
    async def delreminder(self, ctx, reminder_id: int):
        data = await self.db.find_one('reminders', {'_id': ctx.author.id})
        if not data or not data.get('reminders'):
            return await ctx.error('You have no reminders.')
        before = len(data['reminders'])
        data['reminders'] = [r for r in data['reminders'] if r['id'] != reminder_id]
        if len(data['reminders']) == before:
            return await ctx.error(f'Reminder `{reminder_id}` not found.')
        await self.db.update_one('reminders', {'_id': ctx.author.id}, data, upsert=True)
        await ctx.success(f'{self.bot.e.success} Reminder `{reminder_id}` deleted.')

    @commands.command(name='clearreminders', help='Clear all your active reminders.')
    async def clearreminders(self, ctx):
        await self.db.update_one('reminders', {'_id': ctx.author.id}, {'reminders': []}, upsert=True)
        await ctx.success(f'{self.bot.e.success} All reminders cleared.')

    @commands.command(name='todo', help='View your to-do list.')
    async def todo(self, ctx):
        data = await self.db.find_one('todos', {'_id': ctx.author.id})
        if not data or not data.get('items'):
            return await ctx.info('Your to-do list is empty.')
        items = data['items']
        desc = '\n'.join([f'`{i+1}.` {"~~" if item.get("done") else ""}{item["text"]}{"~~" if item.get("done") else ""}' for i, item in enumerate(items)])
        embed = self.bot.embed_manager.generic(description=desc, title=f'📝 {ctx.author.name}\'s To-Do List')
        await ctx.send(embed=embed)

    @commands.command(name='addtodo', help='Add an item to your to-do list.')
    async def addtodo(self, ctx, *, text: str):
        data = await self.db.find_one('todos', {'_id': ctx.author.id}) or {'_id': ctx.author.id, 'items': []}
        if len(data['items']) >= 20:
            return await ctx.error('Max 20 items in your to-do list.')
        data['items'].append({'text': text, 'done': False})
        await self.db.update_one('todos', {'_id': ctx.author.id}, data, upsert=True)
        await ctx.success(f'{self.bot.e.success} Added to your to-do list.')

    @commands.command(name='removetodo', help='Remove an item from your to-do list by number.')
    async def removetodo(self, ctx, index: int):
        data = await self.db.find_one('todos', {'_id': ctx.author.id})
        if not data or not data.get('items'):
            return await ctx.error('Your to-do list is empty.')
        if index < 1 or index > len(data['items']):
            return await ctx.error(f'Index must be between 1 and `{len(data["items"])}`.')
        removed = data['items'].pop(index - 1)
        await self.db.update_one('todos', {'_id': ctx.author.id}, data, upsert=True)
        await ctx.success(f'{self.bot.e.success} Removed: **{removed["text"]}**')

    @commands.command(name='cleartodo', help='Clear your entire to-do list.')
    async def cleartodo(self, ctx):
        await self.db.update_one('todos', {'_id': ctx.author.id}, {'items': []}, upsert=True)
        await ctx.success(f'{self.bot.e.success} To-do list cleared.')

    @commands.command(name='hexinfo', help='Get detailed info about a hex color code.')
    async def hexinfo(self, ctx, color: str):
        try:
            color = color.lstrip('#')
            r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
            embed = self.bot.embed_manager.generic(
                description=(
                    f'**Hex:** `#{color.upper()}`\n'
                    f'**RGB:** `({r}, {g}, {b})`\n'
                    f'**HSL:** computed\n'
                    f'**Int:** `{int(color, 16)}`'
                ),
                title='🎨 Color Info'
            )
            embed.color = discord.Color(int(color, 16))
            embed.set_thumbnail(url=f'https://singlecolorimage.com/get/{color}/100x100')
            await ctx.send(embed=embed)
        except Exception:
            await ctx.error('Invalid hex color. Example: `#FF5733`')

    @commands.command(name='enlarge', help='Enlarge a custom emoji.')
    async def enlarge(self, ctx, emoji: str):
        match = re.match(r'<a?:(\w+):(\d+)>', emoji)
        if not match:
            return await ctx.error('Please provide a custom emoji.')
        name, eid = match.group(1), match.group(2)
        animated = emoji.startswith('<a:')
        ext = 'gif' if animated else 'png'
        url = f'https://cdn.discordapp.com/emojis/{eid}.{ext}?size=512'
        embed = self.bot.embed_manager.generic(description=f'**:{name}:**', title='Enlarged Emoji')
        embed.set_image(url=url)
        await ctx.send(embed=embed)

    @commands.command(name='afkstatus', help='Check the AFK status of a user.')
    async def afkstatus(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        afk_cog = self.bot.get_cog('AFK')
        if not afk_cog:
            return await ctx.error('AFK module not loaded.')
        data = await self.db.find_one('afk_users', {'_id': f'{ctx.guild.id}:{member.id}'})
        if not data:
            return await ctx.info(f'{member.mention} is not AFK.')
        embed = self.bot.embed_manager.generic(
            description=f'**Reason:** {data.get("reason", "No reason")}\n**Since:** <t:{data.get("since", 0)}:R>',
            title=f'{member} is AFK'
        )
        await ctx.send(embed=embed)

    @commands.command(name='mathsteps', help='Show step-by-step working for a simple math expression.')
    async def mathsteps(self, ctx, *, expression: str):
        allowed = set('0123456789+-*/().% ')
        if not all(c in allowed for c in expression):
            return await ctx.error('Only basic math operators allowed.')
        try:
            result = eval(expression, {"__builtins__": {}})
            embed = self.bot.embed_manager.generic(
                description=f'**Expression:** `{expression}`\n**Result:** `{result}`',
                title='🔢 Math Steps'
            )
            await ctx.send(embed=embed)
        except Exception:
            await ctx.error('Invalid expression.')

    @commands.command(name='gradient', help='Show a color gradient between two hex colors.')
    async def gradient(self, ctx, color1: str, color2: str, steps: int = 5):
        try:
            c1 = color1.lstrip('#')
            c2 = color2.lstrip('#')
            r1, g1, b1 = int(c1[0:2], 16), int(c1[2:4], 16), int(c1[4:6], 16)
            r2, g2, b2 = int(c2[0:2], 16), int(c2[2:4], 16), int(c2[4:6], 16)
            steps = max(2, min(10, steps))
            colors = []
            for i in range(steps):
                t = i / (steps - 1)
                r = int(r1 + (r2 - r1) * t)
                g = int(g1 + (g2 - g1) * t)
                b = int(b1 + (b2 - b1) * t)
                colors.append(f'`#{r:02X}{g:02X}{b:02X}`')
            embed = self.bot.embed_manager.generic(
                description=' → '.join(colors),
                title=f'🎨 Gradient: #{c1.upper()} → #{c2.upper()}'
            )
            await ctx.send(embed=embed)
        except Exception:
            await ctx.error('Invalid hex colors. Example: `#FF0000 #0000FF`')

async def setup(bot):
    await bot.add_cog(TextTools(bot))
