import discord
from discord.ext import commands
import aiohttp
import io
import base64
import asyncio

class Customization(commands.Cog):
    category = 'config'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager
        self.session = aiohttp.ClientSession()

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    async def _is_premium(self, ctx):
        is_p, _ = await self.bot.premium_manager.get_premium_status(ctx.guild.id)
        if not is_p:
            await ctx.error("This is a **Premium Only** feature. Upgrade to customize the bot's identity!")
            return False
        return True

    async def _to_data_uri(self, data, content_type="image/png"):
        b64 = base64.b64encode(data).decode('utf-8')
        return f"data:{content_type};base64,{b64}"

    async def _patch_member(self, guild_id, payload):
        url = f"https://discord.com/api/v10/guilds/{guild_id}/members/@me"
        headers = {
            "Authorization": f"Bot {self.bot.http.token}",
            "Content-Type": "application/json"
        }
        async with self.session.patch(url, json=payload, headers=headers) as resp:
            if resp.status == 200:
                return True
            else:
                text = await resp.text()
                print(f"API Error ({resp.status}): {text}")
                return False

    @commands.group(name='bot', invoke_without_command=True, help='Manage the bot\'s native server identity (Premium Only).')
    async def branding_group(self, ctx):
        if not await self._is_premium(ctx): return
        
        config = await self.db.find_one('customization_config', {'_id': ctx.guild.id}) or {}
        
        embed = self.bot.embed_manager.generic(
            description=(
                f"**Nickname:** `{ctx.guild.me.display_name}`\n"
                f"**Custom Bio:** {config.get('bio', 'Not Set')}\n"
                f"**Guild Avatar:** {'Set ✅' if ctx.guild.me.guild_avatar else 'Default ❌'}\n"
                f"**Guild Banner:** {'Set ✅' if config.get('banner_url') else 'Default ❌'}"
            ),
            title="Bot Identity Configuration"
        )
        await ctx.send(embed=embed)

    @branding_group.command(name='name', help='Change the bot\'s nickname in this server.')
    async def name_cmd(self, ctx, *, name: str):
        if not await self._is_premium(ctx): return
        if len(name) > 32: return await ctx.error("Name must be under 32 characters.")
        
        if await self._patch_member(ctx.guild.id, {'nick': name}):
            await self.db.update_one('customization_config', {'_id': ctx.guild.id}, {'nickname': name}, upsert=True)
            await ctx.success(f"My nickname has been updated to **{name}**.")
        else:
            await ctx.error("Failed to update nickname. Ensure I have `Change Nickname` permission.")

    @branding_group.command(name='bio', help='Change the bot\'s "About Me" in this server.')
    async def bio_cmd(self, ctx, *, bio: str):
        if not await self._is_premium(ctx): return
        if len(bio) > 190: return await ctx.error("Bio must be under 190 characters.")
        
        if await self._patch_member(ctx.guild.id, {'bio': bio}):
            await self.db.update_one('customization_config', {'_id': ctx.guild.id}, {'bio': bio}, upsert=True)
            await ctx.success("My server-specific **About Me** has been updated!")
        else:
            await ctx.error("Failed to update bio.")

    @branding_group.command(name='avatar', help='Change the bot\'s profile picture in this server.')
    async def avatar_cmd(self, ctx, url: str = None):
        if not await self._is_premium(ctx): return
        
        image_data = None
        if ctx.message.attachments:
            image_data = await ctx.message.attachments[0].read()
            url = ctx.message.attachments[0].url
        elif url:
            async with self.session.get(url) as r:
                if r.status == 200: image_data = await r.read()
            
        if not image_data:
            return await ctx.error("Please provide an image URL or attach an image.")

        data_uri = await self._to_data_uri(image_data)
        if await self._patch_member(ctx.guild.id, {'avatar': data_uri}):
            await self.db.update_one('customization_config', {'_id': ctx.guild.id}, {'avatar_url': url}, upsert=True)
            await ctx.success("My server-specific **Avatar** has been updated!")
        else:
            await ctx.error("Failed to update avatar.")

    @branding_group.command(name='banner', help='Change the bot\'s profile banner in this server.')
    async def banner_cmd(self, ctx, url: str = None):
        if not await self._is_premium(ctx): return
        
        image_data = None
        if ctx.message.attachments:
            image_data = await ctx.message.attachments[0].read()
            url = ctx.message.attachments[0].url
        elif url:
            async with self.session.get(url) as r:
                if r.status == 200: image_data = await r.read()
            
        if not image_data:
            return await ctx.error("Please provide an image URL or attach an image.")

        data_uri = await self._to_data_uri(image_data)
        if await self._patch_member(ctx.guild.id, {'banner': data_uri}):
            await self.db.update_one('customization_config', {'_id': ctx.guild.id}, {'banner_url': url}, upsert=True)
            await ctx.success("My server-specific **Banner** has been updated!")
        else:
            await ctx.error("Failed to update banner.")

    @branding_group.command(name='reset', help='Revert all identity customizations.')
    async def reset_cmd(self, ctx):
        if not await self._is_premium(ctx): return
        
        if await self._patch_member(ctx.guild.id, {'nick': None, 'avatar': None, 'banner': None, 'bio': None}):
            await self.db.delete_one('customization_config', {'_id': ctx.guild.id})
            await ctx.success("I have reset my server identity to default.")
        else:
            await ctx.error("Failed to reset identity.")

async def setup(bot):
    await bot.add_cog(Customization(bot))
