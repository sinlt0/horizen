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

    @commands.command(name='stomp2', help='Stomp your feet with a GIF!')
    async def stomp_social_gif(self, ctx):
        await self._send_interaction(ctx, None, 'dance', 'is stomping their feet')

    @commands.command(name='dodge2', help='Advanced dodge interaction.')
    async def advanced_dodge(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'nope', 'dodged an attack from')

    @commands.command(name='handshake2', help='Formal handshake with GIF.')
    async def handshake_social_gif(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'peck', 'shakes hands with') # Placeholder GIF

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

    @commands.command(name='highfive2', help='Mega high five!')
    async def mega_highfive(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'highfive', 'gave a mega high-five to')

    @commands.command(name='bite2', help='A more playful bite.')
    async def soft_bite(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'bite', 'nibbles on')

    @commands.command(name='glare2', help='A more intense glare.')
    async def intense_glare(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'stare', 'is staring deeply into the soul of')

    @commands.command(name='lick2', help='Lick someone playfully.')
    async def playful_lick(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'lick', 'licks')

    @commands.command(name='punch2', help='A serious punch.')
    async def serious_punch(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'punch', 'delivered a massive blow to')

    @commands.command(name='kick2', help='A serious kick.')
    async def serious_kick(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'kick', 'kicked')

    @commands.command(name='yeet2', help='Yeet someone into space!')
    async def mega_yeet(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'yeet', 'yeeted into orbit')

    @commands.command(name='tickle2', help='A more intense tickle!')
    async def intense_tickle(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'tickle', 'tickled the life out of')

    @commands.command(name='pat2', help='A mega gentle pat.')
    async def mega_pat(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'pat', 'is giving a mega gentle pat to')

    @commands.command(name='cuddle2', help='The ultimate cuddle.')
    async def ultimate_cuddle(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'cuddle', 'is having the ultimate cuddle session with')

    @commands.command(name='feed2', help='Feed someone a feast!')
    async def feast_feed(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'feed', 'is feeding a royal feast to')

    @commands.command(name='blush2', help='The reddest blush.')
    async def mega_blush(self, ctx, target: discord.Member = None):
        verb = 'blushes intensely at' if target else 'is blushing like a tomato!'
        await self._send_interaction(ctx, target, 'blush', verb)

    @commands.command(name='wink2', help='A very smooth wink.')
    async def smooth_wink(self, ctx, target: discord.Member = None):
        verb = 'winks smoothly at' if target else 'is acting smooth.'
        await self._send_interaction(ctx, target, 'smile', verb) # Using smile as placeholder

    @commands.command(name='poke2', help='A persistent poke.')
    async def persistent_poke(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'poke', 'is persistently poking')

    @commands.command(name='shrug2', help='The ultimate shrug.')
    async def ultimate_shrug(self, ctx):
        await ctx.embed("¯\\_(ツ)_/¯", title="Social - Shrug V2")

    @commands.command(name='dance2', help='A legendary dance move!')
    async def legendary_dance(self, ctx):
        await self._send_interaction(ctx, None, 'dance', 'is performing a legendary dance move!')

    @commands.command(name='laugh2', help='A hysterical laugh.')
    async def hysterical_laugh(self, ctx, target: discord.Member = None):
        verb = 'is laughing hysterically at' if target else 'is laughing hysterically!'
        await self._send_interaction(ctx, target, 'laugh', verb)

    @commands.command(name='pout2', help='A super cute pout.')
    async def mega_pout(self, ctx, target: discord.Member = None):
        verb = 'pouts cutely at' if target else 'is pouting cutely.'
        await self._send_interaction(ctx, target, 'pout', verb)

    @commands.command(name='angry2', help='An explosive anger!')
    async def explosive_angry(self, ctx, target: discord.Member = None):
        verb = 'is exploding with rage at' if target else 'is about to explode!'
        await self._send_interaction(ctx, target, 'kick', verb)

    @commands.command(name='think2', help='Deep philosophical thinking.')
    async def deep_think(self, ctx):
        await self._send_interaction(ctx, None, 'think', 'is pondering the meaning of existence')

    @commands.command(name='confused2', help='Utterly lost.')
    async def utterly_confused(self, ctx):
        await self._send_interaction(ctx, None, 'think', 'is utterly and completely lost')

    @commands.command(name='disgust2', help='Maximum disgust.')
    async def maximum_disgust(self, ctx, target: discord.Member = None):
        verb = 'is maximumly disgusted by' if target else 'is at maximum disgust level.'
        await self._send_interaction(ctx, target, 'stare', verb)

async def setup(bot):
    await bot.add_cog(Social2(bot))
