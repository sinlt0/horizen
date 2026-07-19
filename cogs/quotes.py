import discord
from discord.ext import commands
import random
import datetime

QUOTE_CATEGORIES = {
    'motivation': [
        ("The only way to do great work is to love what you do.", "Steve Jobs"),
        ("Success is not final, failure is not fatal: it is the courage to continue that counts.", "Winston Churchill"),
        ("It does not matter how slowly you go as long as you do not stop.", "Confucius"),
        ("Believe you can and you're halfway there.", "Theodore Roosevelt"),
        ("The future belongs to those who believe in the beauty of their dreams.", "Eleanor Roosevelt"),
        ("Hardships often prepare ordinary people for an extraordinary destiny.", "C.S. Lewis"),
        ("What lies behind us and what lies before us are tiny matters compared to what lies within us.", "Ralph Waldo Emerson"),
        ("Do not wait to strike till the iron is hot, but make it hot by striking.", "William Butler Yeats"),
    ],
    'wisdom': [
        ("The unexamined life is not worth living.", "Socrates"),
        ("Knowing yourself is the beginning of all wisdom.", "Aristotle"),
        ("The only true wisdom is in knowing you know nothing.", "Socrates"),
        ("Patience is bitter, but its fruit is sweet.", "Jean-Jacques Rousseau"),
        ("He who knows others is wise. He who knows himself is enlightened.", "Lao Tzu"),
        ("A journey of a thousand miles begins with a single step.", "Lao Tzu"),
        ("To know what you know and what you do not know, that is true knowledge.", "Confucius"),
    ],
    'love': [
        ("Where there is love there is life.", "Mahatma Gandhi"),
        ("The best thing to hold onto in life is each other.", "Audrey Hepburn"),
        ("Love is composed of a single soul inhabiting two bodies.", "Aristotle"),
        ("We are most alive when we're in love.", "John Updike"),
        ("Love yourself first and everything else falls into line.", "Lucille Ball"),
    ],
    'success': [
        ("Success usually comes to those who are too busy to be looking for it.", "Henry David Thoreau"),
        ("I find that the harder I work, the more luck I seem to have.", "Thomas Jefferson"),
        ("The road to success and the road to failure are almost exactly the same.", "Colin R. Davis"),
        ("Success is walking from failure to failure with no loss of enthusiasm.", "Winston Churchill"),
    ],
    'life': [
        ("Life is what happens when you're busy making other plans.", "John Lennon"),
        ("In the end, it's not the years in your life that count. It's the life in your years.", "Abraham Lincoln"),
        ("Life is really simple, but we insist on making it complicated.", "Confucius"),
        ("The purpose of our lives is to be happy.", "Dalai Lama"),
    ],
    'funny': [
        ("I am not afraid of death; I just don't want to be there when it happens.", "Woody Allen"),
        ("The trouble with having an open mind, of course, is that people will insist on coming along and putting things in it.", "Terry Pratchett"),
        ("I always wanted to be somebody, but I should have been more specific.", "Lily Tomlin"),
        ("Behind every great man is a woman rolling her eyes.", "Jim Carrey"),
    ],
}

ALL_QUOTES = [(text, author, cat) for cat, lst in QUOTE_CATEGORIES.items() for text, author in lst]


class Quotes(commands.Cog):
    category = 'utility'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager

    @commands.command(name='quote', aliases=['qotd2'], help='Get a random inspirational quote.')
    async def quote(self, ctx, category: str = None):
        if category:
            category = category.lower()
            if category not in QUOTE_CATEGORIES:
                return await ctx.error(f'Invalid category. Choose: `{", ".join(QUOTE_CATEGORIES.keys())}`.')
            text, author = random.choice(QUOTE_CATEGORIES[category])
        else:
            text, author, category = random.choice(ALL_QUOTES)
        embed = discord.Embed(description=f'*"{text}"*\n\n— **{author}**', color=discord.Color.blurple())
        embed.set_footer(text=f'Category: {category}')
        await ctx.send(embed=embed)

    @commands.command(name='quotecategories', aliases=['qcats'], help='List all available quote categories.')
    async def quotecategories(self, ctx):
        desc = '\n'.join([f'`{c}` — {len(lst)} quotes' for c, lst in QUOTE_CATEGORIES.items()])
        embed = self.bot.embed_manager.generic(description=desc, title='📚 Quote Categories')
        await ctx.send(embed=embed)

    @commands.group(name='myquote', aliases=['savedquote'], invoke_without_command=True, help='Personal quote collection commands.')
    async def myquote_group(self, ctx):
        await ctx.send_help(ctx.command)

    @myquote_group.command(name='save', help='Save a quote to your personal collection.')
    async def myquote_save(self, ctx, *, text: str):
        if len(text) > 500:
            return await ctx.error('Quote must be under 500 characters.')
        data = await self.db.find_one('saved_quotes', {'_id': ctx.author.id}) or {'_id': ctx.author.id, 'quotes': []}
        if len(data['quotes']) >= 30:
            return await ctx.error('Maximum 30 saved quotes.')
        data['quotes'].append({'text': text, 'saved_at': int(datetime.datetime.utcnow().timestamp())})
        await self.db.update_one('saved_quotes', {'_id': ctx.author.id}, data, upsert=True)
        await ctx.success(f'{self.bot.e.success} Quote saved. You have `{len(data["quotes"])}` saved quotes.')

    @myquote_group.command(name='list', help='View your saved quotes.')
    async def myquote_list(self, ctx):
        data = await self.db.find_one('saved_quotes', {'_id': ctx.author.id})
        if not data or not data.get('quotes'):
            return await ctx.info('You have no saved quotes.')
        desc = '\n'.join([f'`{i+1}.` "{q["text"][:80]}"' for i, q in enumerate(data['quotes'])])
        embed = self.bot.embed_manager.generic(description=desc, title=f'{ctx.author.name}\'s Saved Quotes')
        await ctx.send(embed=embed)

    @myquote_group.command(name='remove', help='Remove a saved quote by its number.')
    async def myquote_remove(self, ctx, index: int):
        data = await self.db.find_one('saved_quotes', {'_id': ctx.author.id})
        if not data or not data.get('quotes'):
            return await ctx.error('You have no saved quotes.')
        if index < 1 or index > len(data['quotes']):
            return await ctx.error(f'Index must be between 1 and `{len(data["quotes"])}`.')
        removed = data['quotes'].pop(index - 1)
        await self.db.update_one('saved_quotes', {'_id': ctx.author.id}, data, upsert=True)
        await ctx.success(f'{self.bot.e.success} Removed: "{removed["text"][:60]}"')

    @myquote_group.command(name='random', help='Get a random quote from your saved collection.')
    async def myquote_random(self, ctx):
        data = await self.db.find_one('saved_quotes', {'_id': ctx.author.id})
        if not data or not data.get('quotes'):
            return await ctx.error('You have no saved quotes.')
        q = random.choice(data['quotes'])
        embed = discord.Embed(description=f'*"{q["text"]}"*', color=discord.Color.gold())
        await ctx.send(embed=embed)

    @commands.command(name='affirmation', help='Get a positive daily affirmation.')
    async def affirmation(self, ctx):
        affirmations = [
            "You are capable of amazing things.",
            "Today is full of opportunities waiting for you.",
            "You are stronger than you think.",
            "Your hard work will pay off.",
            "You deserve good things in life.",
            "You are exactly where you need to be right now.",
            "Every challenge is an opportunity to grow.",
            "You bring value to everyone around you.",
            "You have the power to create change.",
            "Your potential is limitless.",
        ]
        embed = discord.Embed(description=f'✨ {random.choice(affirmations)}', color=discord.Color.teal())
        await ctx.send(embed=embed)

    @commands.command(name='proverb', help='Get a random proverb from world cultures.')
    async def proverb(self, ctx):
        proverbs = [
            ("Fall seven times, stand up eight.", "Japanese Proverb"),
            ("A bird does not sing because it has an answer, it sings because it has a song.", "Chinese Proverb"),
            ("If you want to go fast, go alone. If you want to go far, go together.", "African Proverb"),
            ("The nail that sticks out gets hammered down.", "Japanese Proverb"),
            ("When the roots are deep, there is no reason to fear the wind.", "African Proverb"),
            ("A smooth sea never made a skilled sailor.", "English Proverb"),
        ]
        text, origin = random.choice(proverbs)
        embed = discord.Embed(description=f'*"{text}"*\n\n— **{origin}**', color=discord.Color.dark_gold())
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Quotes(bot))
