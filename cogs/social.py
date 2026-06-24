import discord
from discord.ext import commands
import aiohttp
import random

class SocialCog(commands.Cog):
    category = 'social'

    def __init__(self, bot):
        self.bot = bot
        self.api_url = 'https://nekos.best/api/v2/'
        self.session = aiohttp.ClientSession()

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    async def _send_interaction(self, ctx, target: discord.Member, action_name: str, verb: str, emoji_name: str):
        async with self.session.get(f'{self.api_url}{action_name}') as response:
            if response.status == 200:
                data = await response.json()
                result = data['results'][0]
                emoji = getattr(ctx.e, emoji_name, '')
                received_count = 0
                mutual_count = 0
                if target:
                    if target == ctx.author:
                        return await ctx.warning(f"You can't {action_name} yourself!")
                    received_key = f'rec:{action_name}:{target.id}'
                    ids = sorted([ctx.author.id, target.id])
                    mutual_key = f'mut:{action_name}:{ids[0]}:{ids[1]}'
                    res_rec = await self.bot.db_manager.find_one('social_stats', {'_id': received_key})
                    received_count = (res_rec.get('count', 0) if res_rec else 0) + 1
                    await self.bot.db_manager.update_one('social_stats', {'_id': received_key}, {'count': received_count}, upsert=True)
                    res_mut = await self.bot.db_manager.find_one('social_stats', {'_id': mutual_key})
                    mutual_count = (res_mut.get('count', 0) if res_mut else 0) + 1
                    await self.bot.db_manager.update_one('social_stats', {'_id': mutual_key}, {'count': mutual_count}, upsert=True)
                    footer_text = f'They have {action_name}ed each other {mutual_count} times! | {target.display_name} has been {action_name}ed {received_count} times.'
                    description = f'{emoji} **{ctx.author.display_name}** {verb} **{target.display_name}**!\n\n> -# {footer_text}'
                else:
                    description = f'{emoji} **{ctx.author.display_name}** {verb}!'
                embed = self.bot.embed_manager.generic(description=description, title=f'Social - {action_name.capitalize()}')
                embed.set_image(url=result['url'])
                anime_name = result.get('anime_name')
                if anime_name:
                    embed.set_footer(text=f'Anime: {anime_name}')
                await ctx.send(embed=embed)
            else:
                await ctx.error(f'Failed to fetch {action_name} GIF. Please try again.')

    @commands.command(name='hug', help='Give someone a warm hug.')
    async def hug(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'hug', 'hugs', 'hug')

    @commands.command(name='kiss', help='Give someone a sweet kiss.')
    async def kiss(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'kiss', 'kisses', 'kiss')

    @commands.command(name='slap', help='Slap someone.')
    async def slap(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'slap', 'slapped', 'slap')

    @commands.command(name='pat', help='Give someone a gentle pat.')
    async def pat(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'pat', 'pats', 'pat')

    @commands.command(name='cuddle', help='Cuddle with someone.')
    async def cuddle(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'cuddle', 'cuddles with', 'cuddle')

    @commands.command(name='poke', help='Poke someone.')
    async def poke(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'poke', 'pokes', 'poke')

    @commands.command(name='tickle', help='Tickle someone.')
    async def tickle(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'tickle', 'tickles', 'tickle')

    @commands.command(name='feed', help='Feed someone.')
    async def feed(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'feed', 'feeds', 'feed')

    @commands.command(name='wave', help='Wave hello to someone or just wave.')
    async def wave(self, ctx, target: discord.Member=None):
        await self._send_interaction(ctx, target, 'wave', 'waves', 'wave')

    @commands.command(name='blush', help='Blush at someone or just blush.')
    async def blush(self, ctx, target: discord.Member=None):
        verb = 'blushes at' if target else 'blushes'
        await self._send_interaction(ctx, target, 'blush', verb, 'blush')

    @commands.command(name='smile', help='Smile at someone or just smile.')
    async def smile(self, ctx, target: discord.Member=None):
        verb = 'smiles at' if target else 'smiles'
        await self._send_interaction(ctx, target, 'smile', verb, 'smile')

    @commands.command(name='wink', help='Wink at someone or just wink.')
    async def wink(self, ctx, target: discord.Member=None):
        verb = 'winks at' if target else 'winks'
        await self._send_interaction(ctx, target, 'wink', verb, 'wink')

    @commands.command(name='dance', help='Dance with someone or just dance.')
    async def dance(self, ctx, target: discord.Member=None):
        verb = 'dances with' if target else 'is dancing'
        await self._send_interaction(ctx, target, 'dance', verb, 'dance')

    @commands.command(name='cry', help='Cry on someone\'s shoulder or just cry.')
    async def cry(self, ctx, target: discord.Member=None):
        verb = 'cries on' if target else 'is crying'
        await self._send_interaction(ctx, target, 'cry', verb, 'cry')

    @commands.command(name='handhold', help='Hold someone\'s hand.')
    async def handhold(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'handhold', 'holds the hand of', 'handhold')

    @commands.command(name='punch', help='Punch someone.')
    async def punch(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'punch', 'punches', 'punch')

    @commands.command(name='stare', help='Stare at someone.')
    async def stare(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'stare', 'stares at', 'stare')

    @commands.command(name='highfive', help='Give someone a high five.')
    async def highfive(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'highfive', 'high-fives', 'highfive')

    @commands.command(name='laugh', help='Laugh at someone or just laugh.')
    async def laugh(self, ctx, target: discord.Member=None):
        verb = 'laughs at' if target else 'laughs'
        await self._send_interaction(ctx, target, 'laugh', verb, 'laugh')

    @commands.command(name='pout', help='Pout at someone or just pout.')
    async def pout(self, ctx, target: discord.Member=None):
        verb = 'pouts at' if target else 'pouts'
        await self._send_interaction(ctx, target, 'pout', verb, 'pout')

    @commands.command(name='shrug', help='Shrug at someone or just shrug.')
    async def shrug(self, ctx, target: discord.Member=None):
        verb = 'shrugs at' if target else 'shrugs'
        await self._send_interaction(ctx, target, 'shrug', verb, 'shrug')

    @commands.command(name='sleep', help='Go to sleep.')
    async def sleep(self, ctx):
        await self._send_interaction(ctx, None, 'sleep', 'is sleeping', 'sleep')

    @commands.command(name='yeet', help='Yeet someone.')
    async def yeet(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'yeet', 'yeeted', 'yeet')

    @commands.command(name='bored', help='Show how bored you are.')
    async def bored(self, ctx):
        await self._send_interaction(ctx, None, 'bored', 'is bored', 'bored')

    @commands.command(name='shoot', help='Shoot someone (virtually).')
    async def shoot_social(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'shoot', 'shoots', 'shoot')

    @commands.command(name='dodge', help='Dodge an attack!')
    async def dodge_social(self, ctx, target: discord.Member = None):
        verb = 'dodges an attack from' if target else 'dodges'
        await self._send_interaction(ctx, target, 'dodge', verb, 'dodge')

    @commands.command(name='hide', help='Hide from someone.')
    async def hide_social(self, ctx, target: discord.Member = None):
        verb = 'hides from' if target else 'is hiding'
        await self._send_interaction(ctx, target, 'hide', verb, 'hide')

    @commands.command(name='scared', help='Show how scared you are.')
    async def scared_social(self, ctx, target: discord.Member = None):
        verb = 'is scared of' if target else 'is scared'
        await self._send_interaction(ctx, target, 'scared', verb, 'scared')

    @commands.command(name='skick', help='Socially kick someone.')
    async def skick_social(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'kick', 'kicked', 'kick')

    @commands.command(name='bite', help='Bite someone.')
    async def bite_social(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'bite', 'bites', 'bite')

    @commands.command(name='threaten', help='Threaten someone.')
    async def threaten_social(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'shoot', 'threatens', 'shoot')

    @commands.command(name='lick', help='Lick someone.')
    async def lick_social(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'lick', 'licks', 'lick')

    @commands.command(name='glare', help='Glare at someone.')
    async def glare_social(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'stare', 'glares at', 'stare')

    @commands.command(name='bully', help='Bully someone (playfully).')
    async def bully_social(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'bully', 'bullies', 'bully')

    @commands.command(name='smug', help='Look smug.')
    async def smug_social(self, ctx, target: discord.Member = None):
        verb = 'smugs at' if target else 'is acting smug'
        await self._send_interaction(ctx, target, 'smug', verb, 'smug')

    @commands.command(name='happy', help='Show how happy you are.')
    async def happy_social(self, ctx):
        await self._send_interaction(ctx, None, 'happy', 'is happy', 'happy')

    @commands.command(name='cringe', help='Show your cringe reaction.')
    async def cringe_social(self, ctx, target: discord.Member = None):
        verb = 'cringes at' if target else 'cringes'
        await self._send_interaction(ctx, target, 'cringe', verb, 'cringe')

    @commands.command(name='snuggle', help='Snuggle with someone.')
    async def snuggle_social(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'cuddle', 'snuggles with', 'cuddle')

    @commands.command(name='nom', help='Nom nom nom!')
    async def nom_social(self, ctx, target: discord.Member = None):
        verb = 'noms on' if target else 'noms'
        await self._send_interaction(ctx, target, 'feed', verb, 'feed')

    @commands.command(name='angry', help='Show how angry you are.')
    async def angry_social(self, ctx, target: discord.Member = None):
        verb = 'is angry at' if target else 'is angry'
        await self._send_interaction(ctx, target, 'kick', verb, 'angry')

    @commands.command(name='sad', help='Show how sad you are.')
    async def sad_social(self, ctx):
        await self._send_interaction(ctx, None, 'cry', 'is sad', 'sad')

    @commands.command(name='think', aliases=['thinking'], help='Show that you are thinking.')
    async def think_social(self, ctx):
        await self._send_interaction(ctx, None, 'think', 'is thinking', 'think')

    @commands.command(name='confused', help='Show how confused you are.')
    async def confused_social(self, ctx):
        await self._send_interaction(ctx, None, 'thinking', 'is confused', 'confused')

    @commands.command(name='handshake', help='Shake hands with someone.')
    async def handshake_social(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'handshake', 'shakes hands with', 'handshake')

    @commands.command(name='disgust', help='Show your disgust.')
    async def disgust_social(self, ctx, target: discord.Member = None):
        verb = 'is disgusted by' if target else 'is disgusted'
        await self._send_interaction(ctx, target, 'stare', verb, 'disgust')

    @commands.command(name='scare', help='Scare someone!')
    async def scare_social(self, ctx, target: discord.Member):
        await self._send_interaction(ctx, target, 'shoot', 'scares', 'scare')

async def setup(bot):
    await bot.add_cog(SocialCog(bot))
