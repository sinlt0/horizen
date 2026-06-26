import discord
from discord.ext import commands
import aiohttp
import asyncio
import random
import datetime
import urllib.parse

class NSFWSearhModal(discord.ui.Modal, title="NSFW Advanced Search"):
    query_input = discord.ui.TextInput(
        label="Tags / Search Query",
        placeholder="e.g. yae_miko, high_res, solo...",
        required=True,
        max_length=100
    )

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        url, tags = await self.cog._fetch_gelbooru(self.query_input.value)
        if not url:
            return await interaction.followup.send("No results found for those tags.", ephemeral=True)
        
        embed = self.cog._build_nsfw_embed(url, f"Search: {self.query_input.value}", tags=tags)
        await interaction.followup.send(embed=embed)

class NSFWMasterView(discord.ui.View):
    def __init__(self, bot, cog, ctx):
        super().__init__(timeout=120)
        self.bot = bot
        self.cog = cog
        self.ctx = ctx
        self.current_cat = "hentai"
        self.current_provider = "auto"

    @discord.ui.select(placeholder="🔥 Select Content Category...", options=[
        discord.SelectOption(label="Hentai (Anime)", value="hentai", emoji="🎨", description="Classic high-quality anime art"),
        discord.SelectOption(label="Real Life (irl)", value="ass", emoji="📸", description="Real world NSFW photography"),
        discord.SelectOption(label="Animated (GIFs)", value="pgif", emoji="🎞️", description="Action-packed NSFW animations"),
        discord.SelectOption(label="Neko / Kemonomimi", value="neko", emoji="🐱", description="Catgirls and animal-eared girls"),
        discord.SelectOption(label="Solo / Masturbation", value="solo", emoji="🧘", description="Solo performance content"),
        discord.SelectOption(label="Hardcore / Action", value="fuck", emoji="💥", description="Explicit sexual interactions"),
        discord.SelectOption(label="Specific Fetish", value="bondage", emoji="⛓️", description="Specialized categories & fetishes")
    ])
    async def cat_select(self, interaction, select):
        self.current_cat = select.values[0]
        await interaction.response.defer()
        await self._update(interaction)

    @discord.ui.select(placeholder="⚙️ Select Provider...", options=[
        discord.SelectOption(label="Auto-Select (Recommended)", value="auto", emoji="🧠"),
        discord.SelectOption(label="Nekos.best", value="nekos_best", emoji="⭐"),
        discord.SelectOption(label="Nekobot.xyz", value="nekobot", emoji="🤖"),
        discord.SelectOption(label="Purrbot.site", value="purrbot", emoji="🐾"),
        discord.SelectOption(label="Waifu.pics", value="waifu_pics", emoji="🖼️")
    ])
    async def prov_select(self, interaction, select):
        self.current_provider = select.values[0]
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Next Image", style=discord.ButtonStyle.success, emoji="⏭️")
    async def next_btn(self, interaction, button):
        await interaction.response.defer()
        await self._update(interaction)

    @discord.ui.button(label="Search Tags", style=discord.ButtonStyle.primary, emoji="🔍")
    async def search_btn(self, interaction, button):
        await interaction.response.send_modal(NSFWSearhModal(self.cog))

    @discord.ui.button(label="Randomize", style=discord.ButtonStyle.secondary, emoji="🎲")
    async def rand_btn(self, interaction, button):
        self.current_cat = random.choice(["hentai", "neko", "paizuri", "ass", "pussy", "blowjob", "fuck", "solo"])
        await interaction.response.defer()
        await self._update(interaction)

    async def _update(self, interaction):
        url, anime = await self.cog._fetch_image(self.current_cat, provider=self.current_provider)
        if not url: return await interaction.followup.send("Failed to fetch image from this provider.", ephemeral=True)
        embed = self.cog._build_nsfw_embed(url, self.current_cat, anime)
        await interaction.edit_original_response(embed=embed, view=self)

class NSFW(commands.Cog):
    category = 'nsfw'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager
        self.session = None
        self.providers = {
            'waifu_pics': {
                'base_url': 'https://api.waifu.pics/nsfw/{category}',
                'categories': ['hentai', 'neko', 'trap', 'blowjob', 'waifu'],
                'parse': lambda d: d.get('url')
            },
            'nekos_best': {
                'base_url': 'https://nekos.best/api/v2/{category}',
                'categories': ['hentai', 'neko', 'waifu', 'bj', 'cum', 'anal', 'lesbian', 'pussy', 'paizuri'],
                'parse': lambda d: d.get('results', [{}])[0].get('url') if d.get('results') else None,
                'parse_anime': lambda d: d.get('results', [{}])[0].get('anime_name') if d.get('results') else None
            },
            'nekobot': {
                'base_url': 'https://nekobot.xyz/api/image?type={category}',
                'categories': ['hass', 'hboobs', 'hentai', 'pussy', '4k', 'gonewild', 'ass', 'pgif', 'boobs', 'tentacle', 'yaoi', 'cosplay', 'futanari', 'midriff', 'holo', 'kemonomimi', 'kitsune'],
                'parse': lambda d: d.get('message')
            },
            'purrbot': {
                'base_url': 'https://purrbot.site/api/img/nsfw/{category}/gif',
                'categories': ['anal', 'blowjob', 'cum', 'fuck', 'neko', 'pussy', 'solo', 'threesome', 'yuri', 'creampie'],
                'parse': lambda d: d.get('link')
            }
        }

    async def cog_load(self):
        self.session = aiohttp.ClientSession(headers={'User-Agent': 'HorizenBot/2.0'})

    async def cog_unload(self):
        if self.session: await self.session.close()

    async def _fetch_image(self, category, provider="auto"):
        mapping = {"bj": "blowjob", "sex": "fuck", "pgif": "pgif", "hboobs": "hboobs"}
        target_list = [provider] if provider != "auto" else list(self.providers.keys())
        if provider == "auto": random.shuffle(target_list)
        
        for p_key in target_list:
            if p_key not in self.providers: continue
            p = self.providers[p_key]
            cat = category
            if p_key == "nekos_best":
                if cat == "blowjob": cat = "bj"
            
            if cat in p['categories']:
                try:
                    async with self.session.get(p['base_url'].format(category=cat), timeout=5) as resp:
                        if resp.status == 200:
                            data = await resp.json(content_type=None)
                            url = p['parse'](data)
                            anime = p.get('parse_anime', lambda d: None)(data)
                            if url: return url, anime
                except: continue
        return None, None

    async def _fetch_gelbooru(self, query):
        tags = urllib.parse.quote(f"{query} rating:explicit")
        url = f"https://gelbooru.com/index.php?page=dapi&s=post&q=index&json=1&tags={tags}&limit=50"
        try:
            async with self.session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if not data.get('post'): return None, None
                    post = random.choice(data['post'])
                    return post['file_url'], post.get('tags', '')
        except: pass
        return None, None

    def _build_nsfw_embed(self, url, category, anime=None, tags=None):
        embed = discord.Embed(color=0xFF69B4, timestamp=discord.utils.utcnow())
        embed.set_author(name=f"NSFW Intelligence • {category.capitalize()}", icon_url="https://i.imgur.com/vHqBInS.png")
        embed.set_image(url=url)
        footer = "Horizen Systems Pro"
        if anime: footer += f" • Anime: {anime}"
        embed.set_footer(text=footer)
        if tags:
            tag_list = tags.split(' ')[:10]
            embed.description = f"**Tags:** " + ", ".join([f"`{t}`" for t in tag_list])
        return embed

    async def _handle_nsfw(self, ctx, category, member=None, verb=None):
        if not ctx.channel.is_nsfw(): return await ctx.warning("This command is restricted to NSFW channels.")
        url, anime = await self._fetch_image(category)
        if not url: return await ctx.error(f"Failed to fetch {category} image.")
        
        if member and member != ctx.author:
            await self.db.update_one('social_stats', {'_id': f"{ctx.guild.id}-{ctx.author.id}"}, {'$inc': {'sent_nsfw': 1}}, upsert=True)
            await self.db.update_one('social_stats', {'_id': f"{ctx.guild.id}-{member.id}"}, {'$inc': {'received_nsfw': 1}}, upsert=True)

        desc = f"**{ctx.author.display_name}** {verb} **{member.display_name}**!" if member else None
        embed = self._build_nsfw_embed(url, category, anime)
        if desc: embed.description = desc
        await ctx.send(embed=embed)

    @commands.command(name="nsfw", help="Open the Master NSFW GUI Dashboard.")
    async def nsfw_master(self, ctx):
        if not ctx.channel.is_nsfw(): return await ctx.warning("NSFW Dashboard can only be opened in NSFW channels.")
        url, anime = await self._fetch_image("hentai")
        embed = self._build_nsfw_embed(url, "hentai", anime)
        view = NSFWMasterView(self.bot, self, ctx)
        await ctx.send(embed=embed, view=view)

    @commands.command(name="nsfwsearch", aliases=["nsearch"], help="Search for NSFW content by tags.")
    async def nsfw_search(self, ctx, *, query: str):
        if not ctx.channel.is_nsfw(): return await ctx.warning("NSFW Search is restricted to NSFW channels.")
        await ctx.typing()
        url, tags = await self._fetch_gelbooru(query)
        if not url: return await ctx.error("No results found.")
        embed = self._build_nsfw_embed(url, f"Search: {query}", tags=tags)
        await ctx.send(embed=embed)

    @commands.command(name='boobs', help="Fetch NSFW boobs content.")
    async def boobs(self, ctx, target: discord.Member=None):
        await self._handle_nsfw(ctx, 'boobs' if not target else 'hboobs', target, 'plays with the boobs of')

    @commands.command(name='ass', help="Fetch NSFW ass content.")
    async def ass(self, ctx, target: discord.Member=None):
        await self._handle_nsfw(ctx, 'ass' if not target else 'hass', target, 'smacks the ass of')

    @commands.command(name='pussy', help="Fetch NSFW pussy content.")
    async def pussy(self, ctx, target: discord.Member=None):
        await self._handle_nsfw(ctx, 'pussy', target, 'eats out')

    @commands.command(name='hentai', help="Fetch NSFW hentai content.")
    async def hentai(self, ctx, target: discord.Member=None):
        await self._handle_nsfw(ctx, 'hentai', target, 'watches hentai with')

    @commands.command(name='cum', help="Fetch NSFW cum content.")
    async def cum(self, ctx, target: discord.Member=None):
        await self._handle_nsfw(ctx, 'cum', target, 'cums on')

    @commands.command(name='blowjob', aliases=['bj'], help="Fetch NSFW blowjob content.")
    async def blowjob(self, ctx, target: discord.Member):
        await self._handle_nsfw(ctx, 'bj', target, 'gives a blowjob to')

    @commands.command(name='fuck', help="Fetch NSFW fuck content.")
    async def fuck(self, ctx, target: discord.Member):
        await self._handle_nsfw(ctx, 'fuck', target, 'fucks')

    @commands.command(name='ero', help="Fetch NSFW ero content.")
    async def ero(self, ctx): await self._handle_nsfw(ctx, 'ero')

    @commands.command(name='yaoi', help="Fetch NSFW yaoi content.")
    async def yaoi(self, ctx): await self._handle_nsfw(ctx, 'yaoi')

    @commands.command(name='yuri', help="Fetch NSFW yuri content.")
    async def yuri(self, ctx): await self._handle_nsfw(ctx, 'lesbian')

    @commands.command(name='bdsm', help="Fetch NSFW bdsm content.")
    async def bdsm(self, ctx): await self._handle_nsfw(ctx, 'bondage')

    @commands.command(name='tentacle', help="Fetch NSFW tentacle content.")
    async def tentacle(self, ctx): await self._handle_nsfw(ctx, 'tentacle')

    @commands.command(name='waifunsfw', help="Fetch NSFW waifunsfw content.")
    async def waifu(self, ctx): await self._handle_nsfw(ctx, 'waifu')

    @commands.command(name='nekonsfw', help="Fetch NSFW nekonsfw content.")
    async def neko(self, ctx): await self._handle_nsfw(ctx, 'neko')

    @commands.command(name='trap', help="Fetch NSFW trap content.")
    async def trap(self, ctx): await self._handle_nsfw(ctx, 'trap')

    @commands.command(name='anal', help="Fetch NSFW anal content.")
    async def anal(self, ctx, target: discord.Member):
        await self._handle_nsfw(ctx, 'anal', target, 'does anal with')

    @commands.command(name='lesbian', help="Fetch NSFW lesbian content.")
    async def lesbian(self, ctx, target: discord.Member):
        await self._handle_nsfw(ctx, 'lesbian', target, 'does lesbian things with')

    @commands.command(name='solo', help="Fetch NSFW solo content.")
    async def solo(self, ctx): await self._handle_nsfw(ctx, 'solo')

    @commands.command(name='spank', help="Fetch NSFW spank content.")
    async def spank(self, ctx, target: discord.Member):
        await self._handle_nsfw(ctx, 'spank', target, 'spanks')

    @commands.command(name='tits', help="Fetch NSFW tits content.")
    async def tits(self, ctx, target: discord.Member=None):
        await self._handle_nsfw(ctx, 'tits', target, 'plays with the tits of')

    @commands.command(name='threesome', help="Fetch NSFW threesome content.")
    async def threesome(self, ctx): await self._handle_nsfw(ctx, 'threesome')

    @commands.command(name='thighs', help="Fetch NSFW thighs content.")
    async def thighs(self, ctx): await self._handle_nsfw(ctx, 'hentai')

    @commands.command(name='panties', help="Fetch NSFW panties content.")
    async def panties(self, ctx): await self._handle_nsfw(ctx, 'hentai')

    @commands.command(name='feet', help="Fetch NSFW feet content.")
    async def feet(self, ctx): await self._handle_nsfw(ctx, 'feet')

    @commands.command(name='4k', help="Fetch NSFW 4k content.")
    async def four_k(self, ctx): await self._handle_nsfw(ctx, '4k')

    @commands.command(name='gonewild', aliases=['gwild'], help="Fetch NSFW gonewild content.")
    async def gonewild(self, ctx): await self._handle_nsfw(ctx, 'gonewild')

    @commands.command(name='ass_irl', help="Fetch NSFW ass_irl content.")
    async def ass_irl(self, ctx): await self._handle_nsfw(ctx, 'ass')

    @commands.command(name='pussy_irl', help="Fetch NSFW pussy_irl content.")
    async def pussy_irl(self, ctx): await self._handle_nsfw(ctx, 'pussy')

    @commands.command(name='bondage', help="Fetch NSFW bondage content.")
    async def bondage_cmd(self, ctx): await self._handle_nsfw(ctx, 'bondage')

    @commands.command(name='femdom', help="Fetch NSFW femdom content.")
    async def femdom(self, ctx): await self._handle_nsfw(ctx, 'hentai')

    @commands.command(name='masturbation', help="Fetch NSFW masturbation content.")
    async def masturbation(self, ctx): await self._handle_nsfw(ctx, 'solo')

    @commands.command(name='foot', help="Fetch NSFW foot content.")
    async def foot_nsfw(self, ctx): await self._handle_nsfw(ctx, 'feet')

    @commands.command(name='nsfwavatar', help="Fetch NSFW nsfwavatar content.")
    async def nsfw_avatar(self, ctx): await self._handle_nsfw(ctx, 'hentai')

    @commands.command(name='lewdneko', help="Fetch NSFW lewdneko content.")
    async def lewd_neko(self, ctx): await self._handle_nsfw(ctx, 'neko')

    @commands.command(name='eroyuri', help="Fetch NSFW eroyuri content.")
    async def ero_yuri(self, ctx): await self._handle_nsfw(ctx, 'lesbian')

    @commands.command(name='kuni', help="Fetch NSFW kuni content.")
    async def kuni_cmd(self, ctx, target: discord.Member):
        await self._handle_nsfw(ctx, 'pussy', target, 'performs cunnilingus on')

    @commands.command(name='tits_gif', help="Fetch NSFW tits_gif content.")
    async def tits_gif(self, ctx): await self._handle_nsfw(ctx, 'pgif')

    @commands.command(name='anal_gif', help="Fetch NSFW anal_gif content.")
    async def anal_gif(self, ctx, target: discord.Member):
        await self._handle_nsfw(ctx, 'anal', target, 'does animated anal with')

    @commands.command(name='vagina', help="Fetch NSFW vagina content.")
    async def vagina_cmd(self, ctx): await self._handle_nsfw(ctx, 'pussy')

    @commands.command(name='boobs_gif', help="Fetch NSFW boobs_gif content.")
    async def boobs_gif(self, ctx): await self._handle_nsfw(ctx, 'hboobs')

    @commands.command(name='pussy_gif', help="Fetch NSFW pussy_gif content.")
    async def pussy_gif(self, ctx): await self._handle_nsfw(ctx, 'pgif')

    @commands.command(name='titssuck', help="Fetch NSFW titssuck content.")
    async def tits_suck(self, ctx, target: discord.Member):
        await self._handle_nsfw(ctx, 'bj', target, 'sucks the tits of')

    @commands.command(name='cumonface', help="Fetch NSFW cumonface content.")
    async def cum_on_face(self, ctx, target: discord.Member):
        await self._handle_nsfw(ctx, 'cum', target, 'cums on the face of')

    @commands.command(name='eroneko', help="Fetch NSFW eroneko content.")
    async def ero_neko(self, ctx): await self._handle_nsfw(ctx, 'neko')

    @commands.command(name='yuri_gif', help="Fetch NSFW yuri_gif content.")
    async def yuri_gif(self, ctx): await self._handle_nsfw(ctx, 'lesbian')

    @commands.command(name='cum_gif', help="Fetch NSFW cum_gif content.")
    async def cum_gif(self, ctx, target: discord.Member):
        await self._handle_nsfw(ctx, 'cum', target, 'cums on')

    @commands.command(name='feet_gif', help="Fetch NSFW feet_gif content.")
    async def feet_gif(self, ctx): await self._handle_nsfw(ctx, 'feet')

    @commands.command(name='fuck_gif', help="Fetch NSFW fuck_gif content.")
    async def fuck_gif(self, ctx, target: discord.Member):
        await self._handle_nsfw(ctx, 'fuck', target, 'fucks')

    @commands.command(name='blowjob_gif', help="Fetch NSFW blowjob_gif content.")
    async def blowjob_gif(self, ctx, target: discord.Member):
        await self._handle_nsfw(ctx, 'bj', target, 'gives an animated blowjob to')

    @commands.command(name='gasm', help="Fetch NSFW gasm content.")
    async def gasm_cmd(self, ctx): await self._handle_nsfw(ctx, 'hentai')

    @commands.command(name='oral', help="Fetch NSFW oral content.")
    async def oral_gif(self, ctx, target: discord.Member):
        await self._handle_nsfw(ctx, 'bj', target, 'performs oral on')

    @commands.command(name='solo_gif', help="Fetch NSFW solo_gif content.")
    async def solo_gif(self, ctx): await self._handle_nsfw(ctx, 'solo')

    @commands.command(name='lesbian_gif', help="Fetch NSFW lesbian_gif content.")
    async def lesbian_gif(self, ctx, target: discord.Member):
        await self._handle_nsfw(ctx, 'lesbian', target, 'does animated lesbian things with')

    @commands.command(name='handcuffs', help="Fetch NSFW handcuffs content.")
    async def handcuffs_cmd(self, ctx): await self._handle_nsfw(ctx, 'bondage')

    @commands.command(name='uniform', help="Fetch NSFW uniform content.")
    async def uniform_cmd(self, ctx): await self._handle_nsfw(ctx, 'hentai')

    @commands.command(name='spank_gif', help="Fetch NSFW spank_gif content.")
    async def spank_gif_cmd(self, ctx, target: discord.Member):
        await self._handle_nsfw(ctx, 'spank', target, 'spanks')

    @commands.command(name='masturbate_gif', help="Fetch NSFW masturbate_gif content.")
    async def masturbate_gif_cmd(self, ctx): await self._handle_nsfw(ctx, 'solo')

    @commands.command(name='lewd', help="Fetch NSFW lewd content.")
    async def lewd_cmd(self, ctx): await self._handle_nsfw(ctx, 'hentai')

    @commands.command(name='hentai_gif', help="Fetch NSFW hentai_gif content.")
    async def hentai_gif_cmd(self, ctx): await self._handle_nsfw(ctx, 'hentai')

    @commands.command(name='futanari_gif', help="Fetch NSFW futanari_gif content.")
    async def futanari_gif_cmd(self, ctx): await self._handle_nsfw(ctx, 'futanari')

    @commands.command(name='cosplay_gif', help="Fetch NSFW cosplay_gif content.")
    async def cosplay_gif_cmd(self, ctx): await self._handle_nsfw(ctx, 'cosplay')

    @commands.command(name='paizuri', help="Fetch NSFW paizuri content.")
    async def paizuri_cmd(self, ctx, target: discord.Member = None):
        await self._handle_nsfw(ctx, 'paizuri', target, 'gives a paizuri to')

    @commands.command(name='creampie', help="Fetch NSFW creampie content.")
    async def creampie_cmd(self, ctx, target: discord.Member = None):
        await self._handle_nsfw(ctx, 'creampie', target, 'creampies')

    @commands.command(name='vagina_gif', help="Fetch NSFW vagina_gif content.")
    async def vagina_gif(self, ctx): await self._handle_nsfw(ctx, 'pgif')

    @commands.command(name='paizuri_gif', help="Fetch NSFW paizuri_gif content.")
    async def paizuri_gif(self, ctx): await self._handle_nsfw(ctx, 'pgif')

    @commands.command(name='creampie_gif', help="Fetch NSFW creampie_gif content.")
    async def creampie_gif(self, ctx): await self._handle_nsfw(ctx, 'pgif')

    @commands.command(name='tentacle_gif', help="Fetch NSFW tentacle_gif content.")
    async def tentacle_gif(self, ctx): await self._handle_nsfw(ctx, 'hentai')

    @commands.command(name='bdsm_gif', help="Fetch NSFW bdsm_gif content.")
    async def bdsm_gif(self, ctx): await self._handle_nsfw(ctx, 'bondage')

    @commands.command(name='bondage_gif', help="Fetch NSFW bondage_gif content.")
    async def bondage_gif(self, ctx): await self._handle_nsfw(ctx, 'bondage')

    @commands.command(name='ero_gif', help="Fetch NSFW ero_gif content.")
    async def ero_gif(self, ctx): await self._handle_nsfw(ctx, 'hentai')

    @commands.command(name='femdom_gif', help="Fetch NSFW femdom_gif content.")
    async def femdom_gif(self, ctx): await self._handle_nsfw(ctx, 'hentai')

    @commands.command(name='hentai_neko', help="Fetch NSFW hentai_neko content.")
    async def hentai_neko(self, ctx): await self._handle_nsfw(ctx, 'neko')

    @commands.command(name='hentai_trap', help="Fetch NSFW hentai_trap content.")
    async def hentai_trap(self, ctx): await self._handle_nsfw(ctx, 'trap')

    @commands.command(name='hentai_waifu', help="Fetch NSFW hentai_waifu content.")
    async def hentai_waifu(self, ctx): await self._handle_nsfw(ctx, 'waifu')

    @commands.command(name='real_lesbian', help="Fetch NSFW real_lesbian content.")
    async def real_lesbian(self, ctx): await self._handle_nsfw(ctx, 'lesbian')

    @commands.command(name='real_blowjob', help="Fetch NSFW real_blowjob content.")
    async def real_blowjob(self, ctx): await self._handle_nsfw(ctx, 'ass')

    @commands.command(name='real_cum', help="Fetch NSFW real_cum content.")
    async def real_cum(self, ctx): await self._handle_nsfw(ctx, 'cum')

    @commands.command(name='real_anal', help="Fetch NSFW real_anal content.")
    async def real_anal(self, ctx): await self._handle_nsfw(ctx, 'anal')

    @commands.command(name='real_solo', help="Fetch NSFW real_solo content.")
    async def real_solo(self, ctx): await self._handle_nsfw(ctx, 'solo')

    @commands.command(name='real_spank', help="Fetch NSFW real_spank content.")
    async def real_spank(self, ctx): await self._handle_nsfw(ctx, 'spank')

    @commands.command(name='real_threesome', help="Fetch NSFW real_threesome content.")
    async def real_threesome(self, ctx): await self._handle_nsfw(ctx, 'threesome')

    @commands.command(name='ecchi', help="Fetch NSFW ecchi content.")
    async def ecchi(self, ctx): await self._handle_nsfw(ctx, 'hentai')

    @commands.command(name='lewd_kitsune', help="Fetch NSFW lewd_kitsune content.")
    async def lewd_kitsune(self, ctx): await self._handle_nsfw(ctx, 'kitsune')

    @commands.command(name='lewd_kemonomimi', help="Fetch NSFW lewd_kemonomimi content.")
    async def lewd_kemonomimi(self, ctx): await self._handle_nsfw(ctx, 'kemonomimi')

    @commands.command(name='lewd_holo', help="Fetch NSFW lewd_holo content.")
    async def lewd_holo(self, ctx): await self._handle_nsfw(ctx, 'holo')

    @commands.command(name='midriff_gif', help="Fetch NSFW midriff_gif content.")
    async def midriff_gif(self, ctx): await self._handle_nsfw(ctx, 'hentai')

    @commands.command(name='hentai_master', help="Fetch NSFW hentai_master content.")
    async def h_master(self, ctx): await self._handle_nsfw(ctx, 'hentai')

    @commands.command(name='nsfw_kitsune', help="Fetch NSFW nsfw_kitsune content.")
    async def n_kitsune(self, ctx): await self._handle_nsfw(ctx, 'kitsune')

    @commands.command(name='nsfw_holo', help="Fetch NSFW nsfw_holo content.")
    async def n_holo(self, ctx): await self._handle_nsfw(ctx, 'holo')

    @commands.command(name='lewd_hentai', help="Fetch NSFW lewd_hentai content.")
    async def l_hentai(self, ctx): await self._handle_nsfw(ctx, 'hentai')

    @commands.command(name='hentai_4k', help="Fetch NSFW hentai_4k content.")
    async def h_4k(self, ctx): await self._handle_nsfw(ctx, '4k')

    @commands.command(name='hentai_solo', help="Fetch NSFW hentai_solo content.")
    async def h_solo(self, ctx): await self._handle_nsfw(ctx, 'solo')

    @commands.command(name='hentai_anal', help="Fetch NSFW hentai_anal content.")
    async def h_anal(self, ctx): await self._handle_nsfw(ctx, 'anal')

    @commands.command(name='hentai_bj', help="Fetch NSFW hentai_bj content.")
    async def h_bj(self, ctx): await self._handle_nsfw(ctx, 'bj')

    @commands.command(name='hentai_fuck', help="Fetch NSFW hentai_fuck content.")
    async def h_fuck(self, ctx): await self._handle_nsfw(ctx, 'fuck')

    @commands.command(name='hentai_pussy', help="Fetch NSFW hentai_pussy content.")
    async def h_pussy(self, ctx): await self._handle_nsfw(ctx, 'pussy')

    @commands.command(name='hentai_ass', help="Fetch NSFW hentai_ass content.")
    async def h_ass(self, ctx): await self._handle_nsfw(ctx, 'ass')

    @commands.command(name='hentai_boobs', help="Fetch NSFW hentai_boobs content.")
    async def h_boobs(self, ctx): await self._handle_nsfw(ctx, 'boobs')

    @commands.command(name='hentai_cum', help="Fetch NSFW hentai_cum content.")
    async def h_cum(self, ctx): await self._handle_nsfw(ctx, 'cum')

    @commands.command(name='hentai_lesbian', help="Fetch NSFW hentai_lesbian content.")
    async def h_lesbian(self, ctx): await self._handle_nsfw(ctx, 'lesbian')

    @commands.command(name='hentai_spank', help="Fetch NSFW hentai_spank content.")
    async def h_spank(self, ctx): await self._handle_nsfw(ctx, 'spank')

    @commands.command(name='hentai_random', help="Fetch NSFW hentai_random content.")
    async def n_random(self, ctx):
        cats = ['hentai', 'neko', 'paizuri', 'ass', 'pussy', 'bj', 'fuck', 'solo', 'anal', 'lesbian']
        await self._handle_nsfw(ctx, random.choice(cats))

    @commands.command(name='hentai2', help="Fetch NSFW hentai2 content.")
    async def hentai_two(self, ctx): await self._handle_nsfw(ctx, 'hentai')

    @commands.command(name='pussy2', help="Fetch NSFW pussy2 content.")
    async def pussy_two(self, ctx): await self._handle_nsfw(ctx, 'pussy')

    @commands.command(name='ass2', help="Fetch NSFW ass2 content.")
    async def ass_two(self, ctx): await self._handle_nsfw(ctx, 'ass')

    @commands.command(name='tentacle2', help="Fetch NSFW tentacle2 content.")
    async def tentacle_two(self, ctx): await self._handle_nsfw(ctx, 'tentacle')

    @commands.command(name='yaoi2', help="Fetch NSFW yaoi2 content.")
    async def yaoi_two(self, ctx): await self._handle_nsfw(ctx, 'yaoi')

    @commands.command(name='yuri2', help="Fetch NSFW yuri2 content.")
    async def yuri_two(self, ctx): await self._handle_nsfw(ctx, 'lesbian')

    @commands.command(name='holo', help="Fetch NSFW holo content.")
    async def holo_nsfw(self, ctx): await self._handle_nsfw(ctx, 'holo')

    @commands.command(name='kemonomimi', help="Fetch NSFW kemonomimi content.")
    async def kemonomimi_nsfw(self, ctx): await self._handle_nsfw(ctx, 'kemonomimi')

    @commands.command(name='gonewild2', help="Fetch NSFW gonewild2 content.")
    async def gonewild_two(self, ctx): await self._handle_nsfw(ctx, 'gonewild')

    @commands.command(name='futanari2', help="Fetch NSFW futanari2 content.")
    async def futanari_two(self, ctx): await self._handle_nsfw(ctx, 'futanari')

    @commands.command(name='cosplay2', help="Fetch NSFW cosplay2 content.")
    async def cosplay_two(self, ctx): await self._handle_nsfw(ctx, 'cosplay')

    @commands.command(name='paizuri2', help="Fetch NSFW paizuri2 content.")
    async def paizuri_two(self, ctx): await self._handle_nsfw(ctx, 'paizuri')

    @commands.command(name='creampie2', help="Fetch NSFW creampie2 content.")
    async def creampie_two(self, ctx): await self._handle_nsfw(ctx, 'creampie')

    @commands.command(name='hthighs', help="Fetch NSFW hthighs content.")
    async def hthighs_two(self, ctx): await self._handle_nsfw(ctx, 'hentai')

    @commands.command(name='feet2', help="Fetch NSFW feet2 content.")
    async def feet_two(self, ctx): await self._handle_nsfw(ctx, 'feet')

    @commands.command(name='waifu_nsfw_v2', help="Fetch NSFW waifu_nsfw_v2 content.")
    async def waifu_nsfw_v2(self, ctx): await self._handle_nsfw(ctx, 'waifu')

    @commands.command(name='neko_nsfw_v2', help="Fetch NSFW neko_nsfw_v2 content.")
    async def neko_nsfw_v2(self, ctx): await self._handle_nsfw(ctx, 'neko')

    @commands.command(name='bj_v2', help="Fetch NSFW bj_v2 content.")
    async def bj_v2(self, ctx): await self._handle_nsfw(ctx, 'bj')

    @commands.command(name='cum_v2', help="Fetch NSFW cum_v2 content.")
    async def cum_v2(self, ctx): await self._handle_nsfw(ctx, 'cum')

    @commands.command(name='anal_v2', help="Fetch NSFW anal_v2 content.")
    async def anal_v2(self, ctx): await self._handle_nsfw(ctx, 'anal')

    @commands.command(name='pussy_gif_v2', help="Fetch NSFW pussy_gif_v2 content.")
    async def pussy_gif_v2(self, ctx): await self._handle_nsfw(ctx, 'pussy')

    @commands.command(name='fuck_gif_v2', help="Fetch NSFW fuck_gif_v2 content.")
    async def fuck_gif_v2(self, ctx): await self._handle_nsfw(ctx, 'fuck')

    @commands.command(name='threesome_gif_v2', help="Fetch NSFW threesome_gif_v2 content.")
    async def threesome_gif_v2(self, ctx): await self._handle_nsfw(ctx, 'threesome')

async def setup(bot):
    await bot.add_cog(NSFW(bot))
