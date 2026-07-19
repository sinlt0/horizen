import discord
from discord.ext import commands
import aiohttp
import random

class Anime(commands.Cog):
    category = 'utility'

    def __init__(self, bot):
        self.bot = bot
        self._session = None

    async def cog_load(self):
        self._session = aiohttp.ClientSession()

    def cog_unload(self):
        if self._session:
            self.bot.loop.create_task(self._session.close())

    async def _jikan_get(self, endpoint):
        try:
            async with self._session.get(
                f'https://api.jikan.moe/v4/{endpoint}',
                timeout=aiohttp.ClientTimeout(total=10)
            ) as r:
                if r.status == 200:
                    return await r.json()
        except Exception:
            pass
        return None

    @commands.command(name='animesearch', help='Search for an anime by name.')
    async def anime_search(self, ctx, *, query: str):
        data = await self._jikan_get(f'anime?q={query}&limit=1')
        if not data or not data.get('data'):
            return await ctx.error(f'No results found for `{query}`.')
        a = data['data'][0]
        embed = discord.Embed(
            title=a.get('title', 'Unknown'),
            url=a.get('url', ''),
            color=discord.Color.purple()
        )
        embed.set_thumbnail(url=a.get('images', {}).get('jpg', {}).get('image_url', ''))
        embed.add_field(name='Type', value=f'`{a.get("type", "N/A")}`', inline=True)
        embed.add_field(name='Episodes', value=f'`{a.get("episodes", "?")}`', inline=True)
        embed.add_field(name='Status', value=f'`{a.get("status", "N/A")}`', inline=True)
        embed.add_field(name='Score', value=f'`{a.get("score", "N/A")} ⭐`', inline=True)
        embed.add_field(name='Rating', value=f'`{a.get("rating", "N/A")}`', inline=True)
        embed.add_field(name='Season', value=f'`{a.get("season", "N/A")} {a.get("year", "")}`', inline=True)
        synopsis = a.get('synopsis', 'No synopsis available.')
        embed.add_field(name='Synopsis', value=synopsis[:500] + '...' if len(synopsis) > 500 else synopsis, inline=False)
        embed.set_footer(text=f'MAL ID: {a.get("mal_id", "N/A")} • Source: MyAnimeList')
        await ctx.send(embed=embed)

    @commands.command(name='mangasearch', help='Search for a manga by name.')
    async def manga_search(self, ctx, *, query: str):
        data = await self._jikan_get(f'manga?q={query}&limit=1')
        if not data or not data.get('data'):
            return await ctx.error(f'No results found for `{query}`.')
        m = data['data'][0]
        embed = discord.Embed(
            title=m.get('title', 'Unknown'),
            url=m.get('url', ''),
            color=discord.Color.dark_orange()
        )
        embed.set_thumbnail(url=m.get('images', {}).get('jpg', {}).get('image_url', ''))
        embed.add_field(name='Type', value=f'`{m.get("type", "N/A")}`', inline=True)
        embed.add_field(name='Chapters', value=f'`{m.get("chapters", "?")}`', inline=True)
        embed.add_field(name='Status', value=f'`{m.get("status", "N/A")}`', inline=True)
        embed.add_field(name='Score', value=f'`{m.get("score", "N/A")} ⭐`', inline=True)
        embed.add_field(name='Volumes', value=f'`{m.get("volumes", "?")}`', inline=True)
        synopsis = m.get('synopsis', 'No synopsis available.')
        embed.add_field(name='Synopsis', value=synopsis[:500] + '...' if len(synopsis) > 500 else synopsis, inline=False)
        embed.set_footer(text=f'MAL ID: {m.get("mal_id", "N/A")} • Source: MyAnimeList')
        await ctx.send(embed=embed)

    @commands.command(name='character', aliases=['animechar'], help='Search for an anime/manga character.')
    async def character_search(self, ctx, *, query: str):
        data = await self._jikan_get(f'characters?q={query}&limit=1')
        if not data or not data.get('data'):
            return await ctx.error(f'No character found for `{query}`.')
        c = data['data'][0]
        embed = discord.Embed(
            title=c.get('name', 'Unknown'),
            url=c.get('url', ''),
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=c.get('images', {}).get('jpg', {}).get('image_url', ''))
        embed.add_field(name='Nicknames', value=', '.join(c.get('nicknames', [])) or 'None', inline=False)
        embed.add_field(name='Favorites', value=f'`{c.get("favorites", 0):,}`', inline=True)
        about = c.get('about', 'No information available.')
        embed.add_field(name='About', value=about[:400] + '...' if len(about) > 400 else about, inline=False)
        embed.set_footer(text='Source: MyAnimeList')
        await ctx.send(embed=embed)

    @commands.command(name='animetop', aliases=['topanim'], help='Show the top rated anime of all time.')
    async def animetop(self, ctx, count: int = 10):
        count = max(1, min(20, count))
        data = await self._jikan_get(f'top/anime?limit={count}')
        if not data or not data.get('data'):
            return await ctx.error('Failed to fetch top anime.')
        lines = [
            f'`{i+1}.` **[{a["title"]}]({a["url"]})** — ⭐ `{a.get("score", "N/A")}`'
            for i, a in enumerate(data['data'])
        ]
        embed = self.bot.embed_manager.generic(description='\n'.join(lines), title=f'🏆 Top {count} Anime')
        await ctx.send(embed=embed)

    @commands.command(name='mangatop', aliases=['topmanga'], help='Show the top rated manga of all time.')
    async def mangatop(self, ctx, count: int = 10):
        count = max(1, min(20, count))
        data = await self._jikan_get(f'top/manga?limit={count}')
        if not data or not data.get('data'):
            return await ctx.error('Failed to fetch top manga.')
        lines = [
            f'`{i+1}.` **[{m["title"]}]({m["url"]})** — ⭐ `{m.get("score", "N/A")}`'
            for i, m in enumerate(data['data'])
        ]
        embed = self.bot.embed_manager.generic(description='\n'.join(lines), title=f'📚 Top {count} Manga')
        await ctx.send(embed=embed)

    @commands.command(name='animerandom', aliases=['randomanime'], help='Get a random anime recommendation.')
    async def animerandom(self, ctx):
        data = await self._jikan_get('random/anime')
        if not data or not data.get('data'):
            return await ctx.error('Failed to fetch a random anime.')
        a = data['data']
        embed = discord.Embed(title=a.get('title', 'Unknown'), url=a.get('url', ''), color=discord.Color.random())
        embed.set_thumbnail(url=a.get('images', {}).get('jpg', {}).get('image_url', ''))
        embed.add_field(name='Score', value=f'`{a.get("score", "N/A")} ⭐`', inline=True)
        embed.add_field(name='Episodes', value=f'`{a.get("episodes", "?")}`', inline=True)
        embed.add_field(name='Status', value=f'`{a.get("status", "N/A")}`', inline=True)
        synopsis = a.get('synopsis', 'No synopsis.')
        embed.add_field(name='Synopsis', value=synopsis[:400] + '...' if len(synopsis) > 400 else synopsis, inline=False)
        embed.set_footer(text='🎲 Random Pick • Source: MyAnimeList')
        await ctx.send(embed=embed)

    @commands.command(name='animeseason', aliases=['seasonalanime'], help='Show currently airing anime this season.')
    async def animeseason(self, ctx, count: int = 10):
        count = max(1, min(20, count))
        data = await self._jikan_get(f'seasons/now?limit={count}')
        if not data or not data.get('data'):
            return await ctx.error('Failed to fetch seasonal anime.')
        lines = [
            f'`{i+1}.` **[{a["title"]}]({a["url"]})** — ⭐ `{a.get("score", "N/A")}`'
            for i, a in enumerate(data['data'][:count])
        ]
        embed = self.bot.embed_manager.generic(description='\n'.join(lines), title='📺 Currently Airing Anime')
        await ctx.send(embed=embed)

    @commands.command(name='animegenre', help='Show top anime for a genre ID.')
    async def animegenre(self, ctx, genre_id: int, count: int = 5):
        count = max(1, min(10, count))
        data = await self._jikan_get(f'anime?genres={genre_id}&order_by=score&sort=desc&limit={count}')
        if not data or not data.get('data'):
            return await ctx.error('No anime found for that genre ID.')
        lines = [
            f'`{i+1}.` **[{a["title"]}]({a["url"]})** — ⭐ `{a.get("score", "N/A")}`'
            for i, a in enumerate(data['data'])
        ]
        embed = self.bot.embed_manager.generic(description='\n'.join(lines), title=f'🎭 Top Anime — Genre #{genre_id}')
        await ctx.send(embed=embed)

    @commands.command(name='animequote', help='Get a random anime quote.')
    async def animequote(self, ctx):
        quotes = [
            ("People's lives don't end when they die. It ends when they lose faith.", "Itachi Uchiha", "Naruto"),
            ("If you don't take risks, you can't create a future.", "Monkey D. Luffy", "One Piece"),
            ("The world isn't perfect. But it's there for us, doing the best it can.", "Roy Mustang", "Fullmetal Alchemist"),
            ("Hard work is worthless for those that don't believe in themselves.", "Naruto Uzumaki", "Naruto"),
            ("We are all like fireworks: we climb, we shine and always go our separate ways and become further apart.", "Tsubasa Hanekawa", "Monogatari"),
            ("You should enjoy the little detours to the fullest. Because that's where you'll find the things more important than what you want.", "Ging Freecss", "Hunter x Hunter"),
            ("No matter how hard or impossible it is, never lose sight of your goal.", "Monkey D. Luffy", "One Piece"),
            ("In this world, wherever there is light, there are also shadows.", "Madara Uchiha", "Naruto"),
        ]
        text, character, series = random.choice(quotes)
        embed = discord.Embed(
            description=f'*"{text}"*\n\n— **{character}**, *{series}*',
            color=discord.Color.purple()
        )
        await ctx.send(embed=embed)

    @commands.command(name='waifu3', help='Get a random waifu image from waifu.im.')
    async def waifu2(self, ctx):
        if not ctx.channel.is_nsfw():
            try:
                async with self._session.get(
                    'https://api.waifu.im/search/?included_tags=waifu&is_nsfw=false',
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as r:
                    if r.status == 200:
                        data = await r.json()
                        img_url = data['images'][0]['url']
                        embed = discord.Embed(color=discord.Color.pink())
                        embed.set_image(url=img_url)
                        return await ctx.send(embed=embed)
            except Exception:
                pass
            return await ctx.error('Could not fetch image.')
        else:
            return await ctx.error('This command is not available here.')

async def setup(bot):
    await bot.add_cog(Anime(bot))
