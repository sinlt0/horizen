import discord
from discord.ext import commands
import random
import datetime

ZODIAC_SIGNS = [
    ('Capricorn', (12, 22), (1, 19), '♑'),
    ('Aquarius', (1, 20), (2, 18), '♒'),
    ('Pisces', (2, 19), (3, 20), '♓'),
    ('Aries', (3, 21), (4, 19), '♈'),
    ('Taurus', (4, 20), (5, 20), '♉'),
    ('Gemini', (5, 21), (6, 20), '♊'),
    ('Cancer', (6, 21), (7, 22), '♋'),
    ('Leo', (7, 23), (8, 22), '♌'),
    ('Virgo', (8, 23), (9, 22), '♍'),
    ('Libra', (9, 23), (10, 22), '♎'),
    ('Scorpio', (10, 23), (11, 21), '♏'),
    ('Sagittarius', (11, 22), (12, 21), '♐'),
]

SIGN_TRAITS = {
    'Aries': 'bold, ambitious, and a natural leader',
    'Taurus': 'reliable, patient, and devoted',
    'Gemini': 'curious, adaptable, and quick-witted',
    'Cancer': 'intuitive, emotional, and deeply loyal',
    'Leo': 'confident, generous, and dramatic',
    'Virgo': 'analytical, practical, and detail-oriented',
    'Libra': 'diplomatic, fair-minded, and social',
    'Scorpio': 'passionate, resourceful, and intense',
    'Sagittarius': 'adventurous, optimistic, and free-spirited',
    'Capricorn': 'disciplined, responsible, and ambitious',
    'Aquarius': 'independent, original, and humanitarian',
    'Pisces': 'compassionate, artistic, and intuitive',
}

HOROSCOPES = [
    "The stars align in your favor today. Trust your instincts and take that leap you've been considering.",
    "A surprising opportunity will present itself. Stay alert and don't let it pass you by.",
    "Relationships take center stage today. An honest conversation could change everything.",
    "Your energy is high — channel it into something productive rather than scattering it.",
    "Patience will be your greatest asset today. Good things are coming, just not instantly.",
    "Someone from your past may resurface. Approach with an open mind, not old grudges.",
    "Financial clarity is on the horizon. A decision you've been avoiding needs your attention.",
    "Your creativity peaks today. Use it before the moment passes.",
    "A small risk could lead to a big reward. Trust the process.",
    "Rest is productive too. Don't feel guilty for slowing down today.",
]

CHINESE_ZODIAC = ['Rat', 'Ox', 'Tiger', 'Rabbit', 'Dragon', 'Snake', 'Horse', 'Goat', 'Monkey', 'Rooster', 'Dog', 'Pig']

COMPATIBILITY_PAIRS = {
    frozenset(['Aries', 'Leo']): 95, frozenset(['Aries', 'Sagittarius']): 92,
    frozenset(['Taurus', 'Virgo']): 90, frozenset(['Taurus', 'Capricorn']): 88,
    frozenset(['Gemini', 'Libra']): 91, frozenset(['Gemini', 'Aquarius']): 87,
    frozenset(['Cancer', 'Scorpio']): 93, frozenset(['Cancer', 'Pisces']): 89,
    frozenset(['Leo', 'Sagittarius']): 90,
    frozenset(['Virgo', 'Capricorn']): 86,
    frozenset(['Libra', 'Aquarius']): 88,
    frozenset(['Scorpio', 'Pisces']): 91,
}


def get_zodiac(month, day):
    for sign, start, end, emoji in ZODIAC_SIGNS:
        if (month == start[0] and day >= start[1]) or (month == end[0] and day <= end[1]):
            return sign, emoji
    return 'Capricorn', '♑'


class Astrology(commands.Cog):
    category = 'fun'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager

    @commands.command(name='zodiac', help='Find your zodiac sign. Usage: zodiac MM/DD')
    async def zodiac(self, ctx, date: str = None):
        if date:
            try:
                month, day = map(int, date.split('/'))
            except Exception:
                return await ctx.error('Invalid date. Use `MM/DD` format e.g. `12/25`.')
        else:
            data = await self.db.find_one('birthdays', {'_id': f'{ctx.guild.id}:{ctx.author.id}'})
            if not data:
                return await ctx.error('No birthday set. Use `zodiac MM/DD` or set your birthday with `birthday set`.')
            month, day = data['month'], data['day']

        sign, emoji = get_zodiac(month, day)
        traits = SIGN_TRAITS.get(sign, 'unique and one of a kind')
        embed = discord.Embed(
            title=f'{emoji} {sign}',
            description=f'Born on `{month:02d}/{day:02d}`, you are **{traits}**.',
            color=discord.Color.purple()
        )
        await ctx.send(embed=embed)

    @commands.command(name='horoscope', help='Get your daily horoscope.')
    async def horoscope(self, ctx, sign: str = None):
        if sign:
            sign = sign.capitalize()
            valid_signs = [s[0] for s in ZODIAC_SIGNS]
            if sign not in valid_signs:
                return await ctx.error(f'Invalid sign. Choose: `{", ".join(valid_signs)}`.')
        else:
            data = await self.db.find_one('birthdays', {'_id': f'{ctx.guild.id}:{ctx.author.id}'})
            if not data:
                return await ctx.error('No birthday set. Use `horoscope <sign>` or set your birthday first.')
            sign, _ = get_zodiac(data['month'], data['day'])

        emoji = next((e for s, _, _, e in ZODIAC_SIGNS if s == sign), '⭐')
        today = datetime.datetime.utcnow().strftime('%B %d, %Y')
        random.seed(f'{sign}{datetime.datetime.utcnow().strftime("%Y%m%d")}')
        horoscope_text = random.choice(HOROSCOPES)
        random.seed()

        embed = discord.Embed(
            title=f'{emoji} {sign} Horoscope',
            description=horoscope_text,
            color=discord.Color.purple()
        )
        embed.set_footer(text=today)
        await ctx.send(embed=embed)

    @commands.command(name='chinesezodiac', aliases=['czodiac'], help='Find your Chinese zodiac animal. Usage: chinesezodiac <year>')
    async def chinesezodiac(self, ctx, year: int = None):
        if not year:
            data = await self.db.find_one('birthdays', {'_id': f'{ctx.guild.id}:{ctx.author.id}'})
            year = datetime.datetime.utcnow().year - 20
        animal = CHINESE_ZODIAC[(year - 4) % 12]
        embed = discord.Embed(
            description=f'People born in **{year}** are the **{animal}**.',
            title=f'🐉 Chinese Zodiac: {animal}',
            color=discord.Color.dark_red()
        )
        await ctx.send(embed=embed)

    @commands.command(name='compatibility', aliases=['zodiaclove'], help='Check zodiac compatibility between two signs.')
    async def compatibility(self, ctx, sign1: str, sign2: str):
        sign1, sign2 = sign1.capitalize(), sign2.capitalize()
        valid_signs = [s[0] for s in ZODIAC_SIGNS]
        if sign1 not in valid_signs or sign2 not in valid_signs:
            return await ctx.error(f'Invalid sign(s). Choose from: `{", ".join(valid_signs)}`.')

        pair = frozenset([sign1, sign2])
        if pair in COMPATIBILITY_PAIRS:
            score = COMPATIBILITY_PAIRS[pair]
        else:
            random.seed(f'{sign1}{sign2}')
            score = random.randint(40, 85)
            random.seed()

        e1 = next(e for s, _, _, e in ZODIAC_SIGNS if s == sign1)
        e2 = next(e for s, _, _, e in ZODIAC_SIGNS if s == sign2)
        bar = '💖' * (score // 20) + '🖤' * (5 - score // 20)

        embed = discord.Embed(
            title=f'{e1} {sign1} + {e2} {sign2}',
            description=f'**Compatibility:** `{score}%`\n{bar}',
            color=discord.Color.magenta()
        )
        await ctx.send(embed=embed)

    @commands.command(name='zodiacinfo', help='Get detailed traits about a zodiac sign.')
    async def zodiacinfo(self, ctx, sign: str):
        sign = sign.capitalize()
        valid_signs = [s[0] for s in ZODIAC_SIGNS]
        if sign not in valid_signs:
            return await ctx.error(f'Invalid sign. Choose: `{", ".join(valid_signs)}`.')
        emoji = next(e for s, _, _, e in ZODIAC_SIGNS if s == sign)
        traits = SIGN_TRAITS.get(sign, 'unique')
        sign_data = next((s, st, en) for s, st, en, e in ZODIAC_SIGNS if s == sign)
        embed = discord.Embed(
            title=f'{emoji} {sign}',
            description=(
                f'**Date Range:** {sign_data[1][0]:02d}/{sign_data[1][1]:02d} - {sign_data[2][0]:02d}/{sign_data[2][1]:02d}\n'
                f'**Traits:** {traits}'
            ),
            color=discord.Color.purple()
        )
        await ctx.send(embed=embed)

    @commands.command(name='allzodiac', aliases=['zodiaclist'], help='List all zodiac signs and their date ranges.')
    async def allzodiac(self, ctx):
        desc = '\n'.join([
            f'{e} **{s}** — {st[0]:02d}/{st[1]:02d} to {en[0]:02d}/{en[1]:02d}'
            for s, st, en, e in ZODIAC_SIGNS
        ])
        embed = self.bot.embed_manager.generic(description=desc, title='⭐ Zodiac Signs')
        await ctx.send(embed=embed)

    @commands.command(name='moonphase', help='Get today\'s approximate moon phase.')
    async def moonphase(self, ctx):
        phases = ['🌑 New Moon', '🌒 Waxing Crescent', '🌓 First Quarter', '🌔 Waxing Gibbous',
                  '🌕 Full Moon', '🌖 Waning Gibbous', '🌗 Last Quarter', '🌘 Waning Crescent']
        days_since_new = (datetime.datetime.utcnow() - datetime.datetime(2000, 1, 6)).days % 29.53
        phase_index = int((days_since_new / 29.53) * 8) % 8
        embed = discord.Embed(
            description=f'Today\'s moon phase: **{phases[phase_index]}**',
            color=discord.Color.dark_blue()
        )
        await ctx.send(embed=embed)

    @commands.command(name='luckynumber', help='Get your lucky number for today.')
    async def luckynumber(self, ctx):
        seed = f'{ctx.author.id}{datetime.datetime.utcnow().strftime("%Y%m%d")}'
        random.seed(seed)
        number = random.randint(1, 99)
        random.seed()
        embed = discord.Embed(description=f'🍀 Your lucky number today is **{number}**!', color=discord.Color.green())
        await ctx.send(embed=embed)

    @commands.command(name='luckycolor', help='Get your lucky color for today.')
    async def luckycolor(self, ctx):
        colors = ['Red', 'Blue', 'Green', 'Gold', 'Purple', 'Silver', 'Orange', 'Teal', 'Pink', 'White']
        seed = f'{ctx.author.id}{datetime.datetime.utcnow().strftime("%Y%m%d")}color'
        random.seed(seed)
        color = random.choice(colors)
        random.seed()
        embed = discord.Embed(description=f'🎨 Your lucky color today is **{color}**!', color=discord.Color.gold())
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Astrology(bot))
