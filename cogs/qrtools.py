import discord
from discord.ext import commands
import aiohttp
import io
import urllib.parse

class QRTools(commands.Cog):
    category = 'utility'

    def __init__(self, bot):
        self.bot = bot
        self._session = None

    async def cog_load(self):
        self._session = aiohttp.ClientSession()

    def cog_unload(self):
        if self._session:
            self.bot.loop.create_task(self._session.close())

    @commands.command(name='qrcode', aliases=['qr2'], help='Generate a QR code from text or a URL.')
    async def qrcode(self, ctx, *, content: str):
        if len(content) > 500:
            return await ctx.error('Content must be under 500 characters.')
        encoded = urllib.parse.quote(content)
        url = f'https://api.qrserver.com/v1/create-qr-code/?size=400x400&data={encoded}'
        try:
            async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status != 200:
                    return await ctx.error('Failed to generate QR code.')
                data = await r.read()
        except Exception:
            return await ctx.error('QR generation service unavailable.')
        buf = io.BytesIO(data)
        buf.seek(0)
        embed = self.bot.embed_manager.generic(description=f'Encoded: `{content[:100]}`', title='📱 QR Code')
        embed.set_image(url='attachment://qrcode.png')
        await ctx.send(embed=embed, file=discord.File(buf, filename='qrcode.png'))

    @commands.command(name='qrwifi', help='Generate a QR code for WiFi credentials. Usage: qrwifi <ssid> <password>')
    async def qrwifi(self, ctx, ssid: str, password: str):
        wifi_str = f'WIFI:T:WPA;S:{ssid};P:{password};;'
        encoded = urllib.parse.quote(wifi_str)
        url = f'https://api.qrserver.com/v1/create-qr-code/?size=400x400&data={encoded}'
        try:
            async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                data = await r.read()
        except Exception:
            return await ctx.error('QR generation service unavailable.')
        buf = io.BytesIO(data)
        buf.seek(0)
        await ctx.author.send(
            f'📶 WiFi QR for **{ssid}** (sent privately for security):',
            file=discord.File(buf, filename='wifi_qr.png')
        )
        try:
            await ctx.message.delete()
        except Exception:
            pass
        await ctx.success(f'{self.bot.e.success} WiFi QR code sent to your DMs.')

    @commands.command(name='qrvcard', help='Generate a QR code vCard for contact sharing.')
    async def qrvcard(self, ctx, name: str, phone: str, email: str = None):
        vcard = f'BEGIN:VCARD\nVERSION:3.0\nFN:{name}\nTEL:{phone}\n'
        if email:
            vcard += f'EMAIL:{email}\n'
        vcard += 'END:VCARD'
        encoded = urllib.parse.quote(vcard)
        url = f'https://api.qrserver.com/v1/create-qr-code/?size=400x400&data={encoded}'
        try:
            async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                data = await r.read()
        except Exception:
            return await ctx.error('QR generation service unavailable.')
        buf = io.BytesIO(data)
        buf.seek(0)
        embed = self.bot.embed_manager.generic(description=f'Contact card for **{name}**', title='📇 vCard QR Code')
        embed.set_image(url='attachment://vcard.png')
        await ctx.send(embed=embed, file=discord.File(buf, filename='vcard.png'))

    @commands.command(name='barcode', help='Generate a barcode from a number.')
    async def barcode(self, ctx, code: str):
        if not code.isdigit():
            return await ctx.error('Barcode content must be numeric.')
        url = f'https://barcode.tec-it.com/barcode.ashx?data={code}&code=Code128&dpi=96'
        try:
            async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status != 200:
                    return await ctx.error('Failed to generate barcode.')
                data = await r.read()
        except Exception:
            return await ctx.error('Barcode generation service unavailable.')
        buf = io.BytesIO(data)
        buf.seek(0)
        embed = self.bot.embed_manager.generic(description=f'Encoded: `{code}`', title='📊 Barcode')
        embed.set_image(url='attachment://barcode.png')
        await ctx.send(embed=embed, file=discord.File(buf, filename='barcode.png'))

async def setup(bot):
    await bot.add_cog(QRTools(bot))
