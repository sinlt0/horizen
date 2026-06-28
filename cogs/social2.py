import discord
from discord.ext import commands
import aiohttp
import random

class Social2(commands.Cog):
    category = 'social'

    def __init__(self, bot):
        self.bot = bot
        self.apis = {
            'nekos_best': 'https://nekos.best/api/v2/',
            'nekos_life': 'https://nekos.life/api/v2/img/',
            'waifu_pics': 'https://api.waifu.pics/sfw/'
        }

    async def _fetch_gif(self, action):
        # Specific mappings for different APIs
        mappings = {
            'boop': ('nekos_life', 'boop'),
            'bonk': ('waifu_pics', 'bonk'),
            'nuzzle': ('nekos_life', 'cuddle'),
            'peek': ('nekos_best', 'lurk'),
            'tailwag': ('nekos_best', 'fluff'),
            'baka': ('nekos_best', 'baka'),
            'chase': ('nekos_best', 'chase'),
            'cheer': ('nekos_best', 'cheer'),
            'peck': ('nekos_best', 'peck'),
            'nod': ('nekos_best', 'nod'),
            'nope': ('nekos_best', 'nope')
        }
        
        provider, api_action = mappings.get(action, ('nekos_best', action))
        url = f"{self.apis[provider]}{api_action}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if provider == 'nekos_best': return data['results'][0]['url']
                    if provider == 'nekos_life': return data['url']
                    if provider == 'waifu_pics': return data['url']
        return None

    async def _send_interaction(self, ctx, target: discord.Member, action: str, verb: str):
        url = await self._fetch_gif(action)
        if not url: return await ctx.error(f"Failed to fetch {action} GIF.")
        
        emoji = getattr(ctx.e, action, getattr(ctx.e, 'happy', ''))
        if target:
            if target == ctx.author: return await ctx.warning(f"You can't {action} yourself!")
            desc = f"{emoji} **{ctx.author.display_name}** {verb} **{target.display_name}**!"
        else:
            desc = f"{emoji} **{ctx.author.display_name}** {verb}!"
            
        embed = self.bot.embed_manager.generic(description=desc, title=f"Social - {action.capitalize()}")
        embed.set_image(url=url)
        await ctx.send(embed=embed)

    @commands.command(name='boop', help='Boop someone!')
    async def boop_social(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'boop', 'boops')

    @commands.command(name='bonk', help='Bonk someone!')
    async def bonk_social(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'bonk', 'bonks')

    @commands.command(name='peek', help='Peek at someone.')
    async def peek_social(self, ctx, target: discord.Member = None):
        await self._send_interaction(ctx, target, 'peek', 'peeks at' if target else 'peeks')

    @commands.command(name='tailwag', help='Wag your tail!')
    async def tailwag_social(self, ctx):
        await self._send_interaction(ctx, None, 'tailwag', 'wags their tail')

    @commands.command(name='nuzzle', help='Nuzzle someone.')
    async def nuzzle_social(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'nuzzle', 'nuzzles')

    @commands.command(name='baka', help='Call someone a baka!')
    async def baka_social(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'baka', 'calls BAKA to')

    @commands.command(name='chase', help='Chase someone!')
    async def chase_social(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'chase', 'is chasing')

    @commands.command(name='cheer', help='Cheer for someone!')
    async def cheer_social(self, ctx, target: discord.Member = None):
        await self._send_interaction(ctx, target, 'cheer', 'cheers for' if target else 'cheers')

    @commands.command(name='peck', help='Give someone a quick peck.')
    async def peck_social(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'peck', 'pecks')

    @commands.command(name='nod', help='Nod your head.')
    async def nod_social(self, ctx):
        await self._send_interaction(ctx, None, 'nod', 'nods')

    @commands.command(name='nope', help='Just say NOPE.')
    async def nope_social(self, ctx):
        await self._send_interaction(ctx, None, 'nope', 'says NOPE')

    @commands.command(name='thumbsup', help='Give someone a thumbs up!')
    async def thumbsup_social(self, ctx, target: discord.Member = None):
        await self._send_interaction(ctx, target, 'thumbsup', 'gives a thumbs up to' if target else 'gives a thumbs up')

    @commands.command(name='greet2', help='Greet the channel.')
    async def greet_social_cmd(self, ctx):
        await self._send_interaction(ctx, None, 'wave', 'says hello to everyone!')

    @commands.command(name='goodnight', help='Say goodnight to someone.')
    async def goodnight_social(self, ctx, target: discord.Member = None):
        verb = f'wishes a good night to **{target.display_name}**' if target else 'is going to sleep. Goodnight!'
        await self._send_interaction(ctx, target, 'sleep', verb)

    @commands.command(name='goodmorning', help='Say goodmorning to someone.')
    async def goodmorning_social(self, ctx, target: discord.Member = None):
        verb = f'wishes a productive morning to **{target.display_name}**' if target else 'is waking up. Good morning!'
        await self._send_interaction(ctx, target, 'smile', verb)

    @commands.command(name='comfort', help='Comfort someone in need.')
    async def comfort_social(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'hug', 'comforts')

async def setup(bot):
    await bot.add_cog(Social2(bot))
