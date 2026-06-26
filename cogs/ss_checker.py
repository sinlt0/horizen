import discord
from discord.ext import commands
import aiohttp
import hashlib
import re
import asyncio
import io
from PIL import Image, ImageEnhance, ImageOps

class SSReviewView(discord.ui.View):
    def __init__(self, bot, user_id=None, role_id=None):
        super().__init__(timeout=None)
        self.bot = bot
        self.user_id = user_id
        self.role_id = role_id

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.success, custom_id="ss_approve")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._process(interaction, 'approved')

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.danger, custom_id="ss_deny")
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._process(interaction, 'denied')

    async def _process(self, interaction, status):
        embed = interaction.message.embeds[0]
        user_id_match = re.search(r'\d+', embed.description)
        if not user_id_match: return await interaction.response.send_message("User ID not found in embed.", ephemeral=True)
        user_id = int(user_id_match.group())
        
        config = await self.bot.db_manager.find_one('ss_checker_config', {'_id': interaction.guild.id})
        role_id = config['reward_role']
        
        guild = interaction.guild
        member = guild.get_member(user_id)
        
        embed.color = discord.Color.green() if status == 'approved' else discord.Color.red()
        embed.title = f"Screenshot {status.capitalize()}"
        embed.add_field(name="Moderator", value=interaction.user.mention)
        
        await interaction.message.edit(embed=embed, view=None)
        
        if status == 'approved' and member:
            role = guild.get_role(role_id)
            if role:
                try: await member.add_roles(role, reason=f"SS Verified by {interaction.user}")
                except: pass
            try: await member.send(embed=self.bot.embed_manager.success(f"Your screenshot in **{guild.name}** has been approved!", title="Verification Success"))
            except: pass
        elif status == 'denied' and member:
            try: await member.send(embed=self.bot.embed_manager.error(f"Your screenshot in **{guild.name}** was denied by staff.", title="Verification Failed"))
            except: pass

        await interaction.response.send_message(f"SS {status}.", ephemeral=True)

class SSChecker(commands.Cog):
    category = 'config'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager
        self.session = aiohttp.ClientSession()
        self.sub_indicators = [
            "subscrib", "unsubscribe", "subbed", "bell", "notification", "abonné", "désabonner", 
            "suscrito", "inscrito", "подписаться", "subscribed", "joined", "member", "membership"
        ]

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    async def _preprocess_image(self, image_bytes):
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                img = img.convert("L") # Grayscale
                img = ImageEnhance.Contrast(img).enhance(2.0)
                img = ImageEnhance.Sharpness(img).enhance(2.0)
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                return buf.getvalue()
        except: return image_bytes

    async def _get_perceptual_hash(self, image_bytes):
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                img = img.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
                pixels = list(img.getdata())
                diff = [pixels[r*9+c] > pixels[r*9+c+1] for r in range(8) for c in range(8)]
                return hex(int("".join(['1' if d else '0' for d in diff]), 2))[2:]
        except: return hashlib.md5(image_bytes).hexdigest()

    def _fuzzy_handle_match(self, handle, text):
        """Advanced fuzzy matching using chunk similarity."""
        handle = handle.lower().strip('@').replace('_', '').replace('.', '')
        text = text.lower().replace('_', '').replace('.', '')
        if handle in text: return True
        chunks = [handle[i:i+3] for i in range(len(handle)-2)]
        if not chunks: return handle in text
        matches = sum(1 for c in chunks if c in text)
        return (matches / len(chunks)) >= 0.6

    async def _perform_ocr(self, image_data):
        api_key = 'K81339388788957'
        form = aiohttp.FormData()
        form.add_field('file', image_data, filename='ss.png', content_type='image/png')
        form.add_field('apikey', api_key)
        form.add_field('language', 'eng')
        try:
            async with self.session.post('https://api.ocr.space/parse/image', data=form, timeout=20) as resp:
                if resp.status == 200:
                    d = await resp.json()
                    if d.get('ParsedResults'): return d['ParsedResults'][0].get('ParsedText', '').lower()
        except: pass
        return ""

    def _extract_handle(self, text):
        match = re.search(r"(@[a-zA-Z0-9_.]+)", text)
        return match.group(1) if match else text

    @commands.group(name='ss', invoke_without_command=True, help='Screenshot verification system.')
    @commands.has_permissions(manage_guild=True)
    async def ss_group(self, ctx):
        await ctx.send_help(ctx.command)

    @ss_group.command(name='setup', help='Setup the YT SS checker.')
    @commands.has_permissions(manage_guild=True)
    async def ss_setup(self, ctx, yt_handle_or_link: str, role: discord.Role, channel: discord.TextChannel):
        handle = self._extract_handle(yt_handle_or_link)
        config = {'_id': ctx.guild.id, 'yt_handle': handle.lower(), 'reward_role': role.id, 'submission_channel': channel.id, 'enabled': True, 'staff_channel': ctx.channel.id}
        await self.db.update_one('ss_checker_config', {'_id': ctx.guild.id}, config, upsert=True)
        await ctx.success(f"SS Checker setup complete!\n**Channel:** {channel.mention}\n**Role:** {role.mention}\n**Target:** `{handle}`")

    @ss_group.command(name='staff', help='Set the staff review channel.')
    @commands.has_permissions(manage_guild=True)
    async def ss_staff(self, ctx, channel: discord.TextChannel):
        await self.db.update_one('ss_checker_config', {'_id': ctx.guild.id}, {'staff_channel': channel.id}, upsert=True)
        await ctx.success(f"Staff review channel set to {channel.mention}.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild: return
        config = await self.db.find_one('ss_checker_config', {'_id': message.guild.id})
        if not config or not config.get('enabled') or message.channel.id != config.get('submission_channel'): return
        if not message.attachments: return
        attachment = message.attachments[0]
        if not any(attachment.filename.lower().endswith(ext) for ext in ['png', 'jpg', 'jpeg', 'webp']): return

        raw_bytes = await attachment.read()
        p_hash = await self._get_perceptual_hash(raw_bytes)
        if await self.db.find_one('ss_hashes', {'_id': p_hash}):
            await message.delete()
            try: await message.author.send(embed=self.bot.embed_manager.error("Duplicate screenshot detected.", title="Anti-Cheat"))
            except: pass
            return

        async with message.channel.typing():
            processed_bytes = await self._preprocess_image(raw_bytes)
            ocr_text = await self._perform_ocr(processed_bytes)
            handle = config['yt_handle']
            is_subbed = any(kw in ocr_text for kw in self.sub_indicators)
            has_handle = self._fuzzy_handle_match(handle, ocr_text)

            if is_subbed and has_handle:
                role = message.guild.get_role(config['reward_role'])
                if role:
                    try: await message.author.add_roles(role, reason="Verified SS")
                    except: pass
                await self.db.update_one('ss_hashes', {'_id': p_hash}, {'user_id': message.author.id}, upsert=True)
                await message.add_reaction("✅")
                try: await message.author.send(embed=self.bot.embed_manager.success(f"Verified subscription to **{handle}**!", title="Success"))
                except: pass
            else:
                staff_channel = message.guild.get_channel(config.get('staff_channel'))
                if staff_channel:
                    embed = self.bot.embed_manager.generic(description=f"**User:** {message.author.mention} (`{message.author.id}`)\n**Target:** `{handle}`\n\n**OCR:**\n```\n{ocr_text[:1800]}\n```", title="SS Staff Review")
                    embed.set_image(url=attachment.url)
                    await staff_channel.send(embed=embed, view=SSReviewView(self.bot, message.author.id, config['reward_role']))
                    await message.add_reaction("⏳")
                else: await message.add_reaction("❌")

async def setup(bot):
    await bot.add_cog(SSChecker(bot))
