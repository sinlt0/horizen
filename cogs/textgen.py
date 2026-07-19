import discord
from discord.ext import commands
import random

class TextGen(commands.Cog):
    category = 'fun'

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='namegen', aliases=['randomname'], help='Generate a random fantasy character name.')
    async def namegen(self, ctx):
        first = ['Aer', 'Bal', 'Cor', 'Dra', 'El', 'Fen', 'Gal', 'Hyr', 'Il', 'Jor', 'Kael', 'Lor']
        second = ['ion', 'wyn', 'dor', 'ric', 'las', 'mir', 'thas', 'via', 'nor', 'dan']
        name = random.choice(first) + random.choice(second)
        await ctx.send(f'🧙 Generated name: **{name}**')

    @commands.command(name='usernamegen', help='Generate a random gamer-style username.')
    async def usernamegen(self, ctx):
        adjectives = ['Shadow', 'Silent', 'Crimson', 'Frost', 'Dark', 'Swift', 'Iron', 'Ghost', 'Storm', 'Blaze']
        nouns = ['Wolf', 'Reaper', 'Phoenix', 'Dragon', 'Hunter', 'Knight', 'Ranger', 'Viper', 'Falcon', 'Titan']
        name = f'{random.choice(adjectives)}{random.choice(nouns)}{random.randint(1,999)}'
        await ctx.send(f'🎮 Generated username: **{name}**')

    @commands.command(name='bandnamegen', help='Generate a random band name.')
    async def bandnamegen(self, ctx):
        w1 = ['Electric', 'Velvet', 'Neon', 'Broken', 'Crystal', 'Midnight', 'Wild', 'Silent']
        w2 = ['Wolves', 'Machine', 'Hearts', 'Dreams', 'Echoes', 'Riot', 'Kings', 'Ashes']
        await ctx.send(f'🎸 Band name: **The {random.choice(w1)} {random.choice(w2)}**')

    @commands.command(name='storyprompt', help='Get a random creative writing story prompt.')
    async def storyprompt(self, ctx):
        prompts = [
            "A locked door in your house that wasn't there yesterday.",
            "You wake up with a memory that isn't yours.",
            "The last person on Earth receives a knock at the door.",
            "Your reflection starts moving independently.",
            "A letter arrives addressed to you, postmarked 50 years in the future.",
            "Every mirror in the world shows a five-second delay.",
            "You discover you can hear people's thoughts, but only their regrets.",
        ]
        await ctx.send(f'✍️ **Story Prompt:** {random.choice(prompts)}')

    @commands.command(name='namethisband', help='Get a band name suggestion based on a genre.')
    async def namethisband(self, ctx, genre: str = 'rock'):
        genre_words = {
            'rock': ['Thunder', 'Riot', 'Voltage', 'Rebels'],
            'metal': ['Inferno', 'Carnage', 'Doom', 'Wraith'],
            'pop': ['Sunset', 'Sparkle', 'Bliss', 'Candy'],
            'jazz': ['Velvet', 'Smoke', 'Blue', 'Midnight'],
        }
        words = genre_words.get(genre.lower(), genre_words['rock'])
        await ctx.send(f'🎵 Band name for **{genre}**: **{random.choice(words)} {random.choice(["Collective", "Society", "Project", "Ensemble"])}**')

    @commands.command(name='titlegen', help='Generate a random book/movie title.')
    async def titlegen(self, ctx):
        templates = [
            "The {adj} {noun}",
            "{noun} of {place}",
            "The Last {noun}",
            "A {adj} {noun} in {place}",
        ]
        adj = random.choice(['Silent', 'Broken', 'Golden', 'Lost', 'Hidden', 'Final'])
        noun = random.choice(['Kingdom', 'Secret', 'Journey', 'Shadow', 'Promise', 'Legacy'])
        place = random.choice(['Winter', 'the North', 'Nowhere', 'Tomorrow'])
        title = random.choice(templates).format(adj=adj, noun=noun, place=place)
        await ctx.send(f'📖 Generated title: **"{title}"**')

    @commands.command(name='slogangen', help='Generate a random company slogan.')
    async def slogangen(self, ctx, *, company: str = 'Your Company'):
        templates = [
            f'{company}: Where Innovation Meets Excellence.',
            f'{company} — Built For Tomorrow.',
            f'Experience the Difference with {company}.',
            f'{company}: Trusted by Millions.',
            f'{company} — Redefining the Future.',
        ]
        await ctx.send(f'📢 {random.choice(templates)}')

    @commands.command(name='wordoftheday', help='Get a random interesting word and its meaning.')
    async def wordoftheday(self, ctx):
        words = [
            ('Serendipity', 'The occurrence of events by chance in a happy way.'),
            ('Ephemeral', 'Lasting for a very short time.'),
            ('Petrichor', 'The pleasant smell after rain.'),
            ('Sonder', 'The realization each passerby has a life as vivid as yours.'),
            ('Ineffable', 'Too great to be expressed in words.'),
            ('Mellifluous', 'A sound that is sweet and smooth to hear.'),
            ('Wanderlust', 'A strong desire to travel and explore.'),
        ]
        word, meaning = random.choice(words)
        embed = discord.Embed(title=f'📖 {word}', description=meaning, color=discord.Color.blue())
        await ctx.send(embed=embed)

    @commands.command(name='synonym', help='Get synonyms for a common word.')
    async def synonym(self, ctx, word: str):
        synonym_map = {
            'happy': ['joyful', 'content', 'elated', 'cheerful', 'pleased'],
            'sad': ['unhappy', 'sorrowful', 'gloomy', 'downcast', 'melancholy'],
            'fast': ['quick', 'swift', 'rapid', 'speedy', 'brisk'],
            'big': ['large', 'huge', 'massive', 'enormous', 'gigantic'],
            'small': ['tiny', 'little', 'miniature', 'petite', 'compact'],
            'smart': ['intelligent', 'clever', 'bright', 'sharp', 'brilliant'],
            'strong': ['powerful', 'sturdy', 'robust', 'mighty', 'tough'],
        }
        results = synonym_map.get(word.lower())
        if not results:
            return await ctx.error(f'No synonyms found for `{word}`. Try: {", ".join(synonym_map.keys())}')
        await ctx.send(f'📝 Synonyms for **{word}**: {", ".join(results)}')

    @commands.command(name='antonym', help='Get antonyms for a common word.')
    async def antonym(self, ctx, word: str):
        antonym_map = {
            'happy': 'sad', 'sad': 'happy', 'fast': 'slow', 'slow': 'fast',
            'big': 'small', 'small': 'big', 'hot': 'cold', 'cold': 'hot',
            'light': 'dark', 'dark': 'light', 'strong': 'weak', 'weak': 'strong',
        }
        result = antonym_map.get(word.lower())
        if not result:
            return await ctx.error(f'No antonym found for `{word}`. Try: {", ".join(antonym_map.keys())}')
        await ctx.send(f'📝 Antonym for **{word}**: **{result}**')

    @commands.command(name='acronymgen', help='Generate a fun acronym meaning from a word.')
    async def acronymgen(self, ctx, word: str):
        if len(word) > 8:
            return await ctx.error('Word must be 8 characters or fewer.')
        word_bank = ['Amazing', 'Brilliant', 'Creative', 'Dynamic', 'Epic', 'Fantastic',
                     'Great', 'Heroic', 'Incredible', 'Joyful', 'Kind', 'Legendary',
                     'Mighty', 'Noble', 'Outstanding', 'Powerful', 'Quick', 'Radiant',
                     'Strong', 'Talented', 'Unique', 'Valiant', 'Wise', 'Xtraordinary',
                     'Youthful', 'Zealous']
        result = ' '.join([random.choice([w for w in word_bank if w[0].upper() == c.upper()] or ['???']) for c in word])
        await ctx.send(f'🔤 **{word.upper()}** = {result}')

    @commands.command(name='vaporwave', aliases=['aesthetic'], help='Convert text to vaporwave aesthetic full-width text.')
    async def vaporwave(self, ctx, *, text: str):
        result = ''.join([chr(ord(c) + 0xFEE0) if 0x21 <= ord(c) <= 0x7E else c for c in text])
        await ctx.send(result)

    @commands.command(name='mockcase', help='Convert text to sPoNgEbOb MoCkInG case.')
    async def mock(self, ctx, *, text: str):
        result = ''.join([c.upper() if i % 2 == 0 else c.lower() for i, c in enumerate(text)])
        await ctx.send(result)

    @commands.command(name='clapback', help='Add 👏 claps between words.')
    async def clap(self, ctx, *, text: str):
        await ctx.send(' 👏 '.join(text.split()))

    @commands.command(name='owoify', help='Convert text to owo speak.')
    async def owoify(self, ctx, *, text: str):
        result = text.replace('r', 'w').replace('l', 'w').replace('R', 'W').replace('L', 'W')
        result += random.choice([' owo', ' uwu', ' >w<', ' nya~'])
        await ctx.send(result)

    @commands.command(name='emojiwords', help='Replace common words with emojis.')
    async def emojify(self, ctx, *, text: str):
        emoji_map = {
            'love': '❤️', 'happy': '😊', 'sad': '😢', 'fire': '🔥',
            'star': '⭐', 'heart': '💖', 'cool': '😎', 'laugh': '😂',
            'yes': '✅', 'no': '❌', 'money': '💰', 'party': '🎉',
        }
        words = text.split()
        result = [emoji_map.get(w.lower(), w) for w in words]
        await ctx.send(' '.join(result))

    @commands.command(name='asciiart', help='Generate simple ASCII art text banner.')
    async def asciiart(self, ctx, *, text: str):
        if len(text) > 10:
            return await ctx.error('Text must be 10 characters or fewer.')
        border = '*' * (len(text) + 4)
        await ctx.send(f'```\n{border}\n* {text.upper()} *\n{border}\n```')

async def setup(bot):
    await bot.add_cog(TextGen(bot))
