import discord
from discord.ext import commands
import aiohttp
import io
import asyncio
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw, ImageFont, ImageOps

class ImageTools(commands.Cog):
    category = 'utility'

    def __init__(self, bot):
        self.bot = bot

    async def _get_avatar_bytes(self, member):
        url = member.display_avatar.replace(format='png', size=512).url
        async with aiohttp.ClientSession() as s:
            async with s.get(url) as r:
                return await r.read()

    def _to_file(self, img, name='image.png'):
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return discord.File(buf, filename=name)

    @commands.command(name='greyscale', aliases=['grayscale', 'grey'], help='Convert a member\'s avatar to greyscale.')
    async def greyscale(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        data = await self._get_avatar_bytes(member)
        img = Image.open(io.BytesIO(data)).convert('L').convert('RGB')
        await ctx.send(file=self._to_file(img, 'greyscale.png'))

    @commands.command(name='invert', aliases=['negative'], help='Invert the colors of a member\'s avatar.')
    async def invert(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        data = await self._get_avatar_bytes(member)
        img = ImageOps.invert(Image.open(io.BytesIO(data)).convert('RGB'))
        await ctx.send(file=self._to_file(img, 'inverted.png'))

    @commands.command(name='blur', help='Apply a blur effect to a member\'s avatar.')
    async def blur(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        data = await self._get_avatar_bytes(member)
        img = Image.open(io.BytesIO(data)).convert('RGB').filter(ImageFilter.GaussianBlur(radius=5))
        await ctx.send(file=self._to_file(img, 'blurred.png'))

    @commands.command(name='pixelate', aliases=['pixel'], help='Pixelate a member\'s avatar.')
    async def pixelate(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        data = await self._get_avatar_bytes(member)
        img = Image.open(io.BytesIO(data)).convert('RGB')
        small = img.resize((32, 32), Image.NEAREST)
        pixelated = small.resize(img.size, Image.NEAREST)
        await ctx.send(file=self._to_file(pixelated, 'pixelated.png'))

    @commands.command(name='sharpen', help='Sharpen a member\'s avatar.')
    async def sharpen(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        data = await self._get_avatar_bytes(member)
        img = Image.open(io.BytesIO(data)).convert('RGB').filter(ImageFilter.SHARPEN)
        await ctx.send(file=self._to_file(img, 'sharpened.png'))

    @commands.command(name='emboss', help='Apply an emboss effect to a member\'s avatar.')
    async def emboss(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        data = await self._get_avatar_bytes(member)
        img = Image.open(io.BytesIO(data)).convert('RGB').filter(ImageFilter.EMBOSS)
        await ctx.send(file=self._to_file(img, 'embossed.png'))

    @commands.command(name='sepia', help='Apply a sepia filter to a member\'s avatar.')
    async def sepia(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        data = await self._get_avatar_bytes(member)
        img = Image.open(io.BytesIO(data)).convert('RGB')
        r, g, b = img.split()
        r = r.point(lambda i: min(255, int(i * 0.393 + 0.769 * i + 0.189 * i)))
        g = g.point(lambda i: min(255, int(i * 0.349 + 0.686 * i + 0.168 * i)))
        b = b.point(lambda i: min(255, int(i * 0.272 + 0.534 * i + 0.131 * i)))
        img = Image.merge('RGB', (r, g, b))
        await ctx.send(file=self._to_file(img, 'sepia.png'))

    @commands.command(name='flip2', aliases=['flipv', 'vflip'], help='Flip a member\'s avatar vertically.')
    async def flip2(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        data = await self._get_avatar_bytes(member)
        img = ImageOps.flip(Image.open(io.BytesIO(data)).convert('RGB'))
        await ctx.send(file=self._to_file(img, 'flipped.png'))

    @commands.command(name='mirror', aliases=['hflip'], help='Mirror a member\'s avatar horizontally.')
    async def mirror(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        data = await self._get_avatar_bytes(member)
        img = ImageOps.mirror(Image.open(io.BytesIO(data)).convert('RGB'))
        await ctx.send(file=self._to_file(img, 'mirrored.png'))

    @commands.command(name='rotate', help='Rotate a member\'s avatar. Usage: rotate [degrees] [@member]')
    async def rotate(self, ctx, degrees: int = 90, member: discord.Member = None):
        member = member or ctx.author
        data = await self._get_avatar_bytes(member)
        img = Image.open(io.BytesIO(data)).convert('RGB').rotate(degrees, expand=True)
        await ctx.send(file=self._to_file(img, 'rotated.png'))

    @commands.command(name='brightness', aliases=['bright'], help='Adjust avatar brightness. Usage: brightness [0.1-3.0] [@member]')
    async def brightness(self, ctx, factor: float = 1.5, member: discord.Member = None):
        factor = max(0.1, min(3.0, factor))
        member = member or ctx.author
        data = await self._get_avatar_bytes(member)
        img = ImageEnhance.Brightness(Image.open(io.BytesIO(data)).convert('RGB')).enhance(factor)
        await ctx.send(file=self._to_file(img, 'brightness.png'))

    @commands.command(name='contrast', help='Adjust avatar contrast. Usage: contrast [0.1-3.0] [@member]')
    async def contrast(self, ctx, factor: float = 1.5, member: discord.Member = None):
        factor = max(0.1, min(3.0, factor))
        member = member or ctx.author
        data = await self._get_avatar_bytes(member)
        img = ImageEnhance.Contrast(Image.open(io.BytesIO(data)).convert('RGB')).enhance(factor)
        await ctx.send(file=self._to_file(img, 'contrast.png'))

    @commands.command(name='saturate', aliases=['saturation'], help='Adjust avatar saturation. Usage: saturate [0.0-3.0] [@member]')
    async def saturate(self, ctx, factor: float = 2.0, member: discord.Member = None):
        factor = max(0.0, min(3.0, factor))
        member = member or ctx.author
        data = await self._get_avatar_bytes(member)
        img = ImageEnhance.Color(Image.open(io.BytesIO(data)).convert('RGB')).enhance(factor)
        await ctx.send(file=self._to_file(img, 'saturated.png'))

    @commands.command(name='edge', aliases=['edges', 'edgedetect'], help='Apply edge detection to a member\'s avatar.')
    async def edge(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        data = await self._get_avatar_bytes(member)
        img = Image.open(io.BytesIO(data)).convert('RGB').filter(ImageFilter.FIND_EDGES)
        await ctx.send(file=self._to_file(img, 'edges.png'))

    @commands.command(name='circle', aliases=['circleav', 'roundav'], help='Crop a member\'s avatar into a circle.')
    async def circle(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        data = await self._get_avatar_bytes(member)
        img = Image.open(io.BytesIO(data)).convert('RGBA').resize((512, 512))
        mask = Image.new('L', img.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, 512, 512), fill=255)
        img.putalpha(mask)
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        await ctx.send(file=discord.File(buf, filename='circle.png'))

    @commands.command(name='colorize', help='Tint a member\'s avatar with a hex color.')
    async def colorize(self, ctx, color: str, member: discord.Member = None):
        member = member or ctx.author
        try:
            color = color.lstrip('#')
            r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
        except Exception:
            return await ctx.error('Invalid hex color. Example: `#FF5733`')
        data = await self._get_avatar_bytes(member)
        img = Image.open(io.BytesIO(data)).convert('RGBA')
        overlay = Image.new('RGBA', img.size, (r, g, b, 100))
        result = Image.alpha_composite(img, overlay).convert('RGB')
        await ctx.send(file=self._to_file(result, 'colorized.png'))

    @commands.command(name='caption', help='Add a caption to a member\'s avatar.')
    async def caption(self, ctx, member: discord.Member, *, text: str):
        if len(text) > 80:
            return await ctx.error('Caption must be under 80 characters.')
        data = await self._get_avatar_bytes(member)
        img = Image.open(io.BytesIO(data)).convert('RGB').resize((512, 512))
        bar_height = 60
        canvas = Image.new('RGB', (512, 512 + bar_height), (0, 0, 0))
        canvas.paste(img, (0, 0))
        draw = ImageDraw.Draw(canvas)
        try:
            font = ImageFont.truetype('/system/fonts/DroidSans.ttf', 28)
        except Exception:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        tx = (512 - tw) // 2
        draw.text((tx, 512 + 15), text, fill=(255, 255, 255), font=font)
        await ctx.send(file=self._to_file(canvas, 'captioned.png'))

    @commands.command(name='avatar2', aliases=['av2', 'pfp2'], help='Show a member\'s avatar in full size with download links.')
    async def avatar2(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        av = member.display_avatar
        formats = []
        for fmt in ['png', 'jpg', 'webp']:
            formats.append(f'[{fmt.upper()}]({av.replace(format=fmt, size=4096).url})')
        if av.is_animated():
            formats.append(f'[GIF]({av.replace(format="gif", size=4096).url})')
        embed = self.bot.embed_manager.generic(
            description=f'**Download:** {" | ".join(formats)}',
            title=f'{member}\'s Avatar'
        )
        embed.set_image(url=av.replace(format='png', size=4096).url)
        await ctx.send(embed=embed)

    @commands.command(name='servericonbig', aliases=['sib', 'bigicon'], help='Show the server icon in maximum resolution.')
    async def servericonbig(self, ctx):
        if not ctx.guild.icon:
            return await ctx.info('This server has no icon.')
        icon = ctx.guild.icon
        formats = [f'[PNG]({icon.replace(format="png", size=4096).url})']
        if icon.is_animated():
            formats.append(f'[GIF]({icon.replace(format="gif", size=4096).url})')
        embed = self.bot.embed_manager.generic(
            description=f'**Download:** {" | ".join(formats)}',
            title=f'{ctx.guild.name} Icon'
        )
        embed.set_image(url=icon.replace(format='png', size=4096).url)
        await ctx.send(embed=embed)

    @commands.command(name='serverbanner', aliases=['sbanner', 'guildban'], help='Show the server banner in full size.')
    async def serverbanner(self, ctx):
        if not ctx.guild.banner:
            return await ctx.info('This server has no banner.')
        embed = self.bot.embed_manager.generic(
            description=f'[Download]({ctx.guild.banner.replace(format="png", size=4096).url})',
            title=f'{ctx.guild.name} Banner'
        )
        embed.set_image(url=ctx.guild.banner.replace(format='png', size=4096).url)
        await ctx.send(embed=embed)

    @commands.command(name='serversplashbig', aliases=['splashbig'], help='Show the server splash image in full size.')
    async def serversplashbig(self, ctx):
        if not ctx.guild.splash:
            return await ctx.info('This server has no splash image.')
        embed = self.bot.embed_manager.generic(
            description=f'[Download]({ctx.guild.splash.replace(format="png", size=4096).url})',
            title=f'{ctx.guild.name} Splash'
        )
        embed.set_image(url=ctx.guild.splash.replace(format='png', size=4096).url)
        await ctx.send(embed=embed)

    @commands.command(name='thumbnail', aliases=['thumb'], help='Show a member\'s avatar as a small thumbnail embed.')
    async def thumbnail(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        embed = self.bot.embed_manager.generic(
            description=f'Thumbnail for {member.mention}',
            title=str(member)
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name='compareav', aliases=['avcompare'], help='Compare two members\' avatars side by side.')
    async def compareav(self, ctx, member1: discord.Member, member2: discord.Member):
        data1 = await self._get_avatar_bytes(member1)
        data2 = await self._get_avatar_bytes(member2)
        img1 = Image.open(io.BytesIO(data1)).convert('RGB').resize((256, 256))
        img2 = Image.open(io.BytesIO(data2)).convert('RGB').resize((256, 256))
        canvas = Image.new('RGB', (532, 256), (30, 30, 30))
        canvas.paste(img1, (0, 0))
        canvas.paste(img2, (276, 0))
        draw = ImageDraw.Draw(canvas)
        draw.text((252, 110), 'VS', fill=(255, 255, 255))
        await ctx.send(file=self._to_file(canvas, 'compare.png'))

    @commands.command(name='dominantcolor', aliases=['domcolor', 'imgcolor'], help='Find the dominant color in a member\'s avatar.')
    async def dominantcolor(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        data = await self._get_avatar_bytes(member)
        img = Image.open(io.BytesIO(data)).convert('RGB').resize((50, 50))
        pixels = list(img.getdata())
        avg_r = sum(p[0] for p in pixels) // len(pixels)
        avg_g = sum(p[1] for p in pixels) // len(pixels)
        avg_b = sum(p[2] for p in pixels) // len(pixels)
        hex_color = f'#{avg_r:02X}{avg_g:02X}{avg_b:02X}'
        color_img = Image.new('RGB', (200, 200), (avg_r, avg_g, avg_b))
        embed = self.bot.embed_manager.generic(
            description=f'**Dominant Color:** `{hex_color}`\n**RGB:** `({avg_r}, {avg_g}, {avg_b})`',
            title=f'{member.name}\'s Dominant Color'
        )
        embed.color = discord.Color(int(hex_color[1:], 16))
        embed.set_thumbnail(url=f'https://singlecolorimage.com/get/{hex_color[1:]}/100x100')
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ImageTools(bot))
