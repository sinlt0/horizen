import datetime
import discord
from discord.ext import commands
import random
import string
import io
import time
from PIL import Image, ImageDraw, ImageFont, ImageFilter

class CaptchaModal(discord.ui.Modal, title='Verification Captcha'):
    captcha_input = discord.ui.TextInput(label='Enter the code shown in the image', placeholder='Code here...', min_length=5, max_length=5)

    def __init__(self, correct_code, member, role):
        super().__init__()
        self.correct_code = correct_code
        self.member = member
        self.role = role
        self.unverified_role = None
        self.main_role = None

    async def on_submit(self, interaction: discord.Interaction):
        if self.captcha_input.value.upper() == self.correct_code:
            try:
                if self.main_role:
                    await self.member.add_roles(self.main_role, reason='Verification successful (Main Role)')
                    if self.role and self.role in self.member.roles:
                        await self.member.remove_roles(self.role, reason='Verification successful (Replacing Verified with Main)')
                elif self.role:
                    await self.member.add_roles(self.role, reason='Verification successful')
                if self.unverified_role and self.unverified_role in self.member.roles:
                    await self.member.remove_roles(self.unverified_role, reason='Verification successful')
                await self.member.bot.signal_verification_success(self.member)
                await interaction.response.send_message('Verification successful!', ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message("I don't have permission to manage your roles. Please contact an admin.", ephemeral=True)
        else:
            await interaction.response.send_message('Incorrect captcha code. Please try again.', ephemeral=True)

class VerificationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Verify', style=discord.ButtonStyle.green, custom_id='persistent:verify_button')
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = await interaction.client.get_config('verification_config', interaction.guild.id)
        if not config or (not config.get('role_id') and not config.get('main_role_id')):
            return await interaction.response.send_message('Verification is not properly configured.', ephemeral=True)
        
        delay = config.get('joingate_delay', 0)
        if delay > 0 and interaction.user.joined_at:
            wait_until = interaction.user.joined_at + datetime.timedelta(seconds=delay)
            now = discord.utils.utcnow()
            if now < wait_until:
                diff = int((wait_until - now).total_seconds())
                return await interaction.response.send_message(f'Join-Gate Active: You must wait another **{diff} seconds** before you can verify.', ephemeral=True)

        role = interaction.guild.get_role(config.get('role_id'))
        main_role = interaction.guild.get_role(config.get('main_role_id'))
        unverified_role = interaction.guild.get_role(config.get('unverified_role_id'))
        target_role = main_role or role
        if not target_role:
            return await interaction.response.send_message('The target role no longer exists.', ephemeral=True)
        if target_role in interaction.user.roles:
            return await interaction.response.send_message('You are already verified!', ephemeral=True)
        mode = config.get('mode', 'button')

        async def grant_access(member):
            try:
                if main_role:
                    await member.add_roles(main_role, reason='Verification successful (Main Role)')
                    if role and role in member.roles:
                        await member.remove_roles(role, reason='Verification successful (Replacing Verified with Main)')
                elif role:
                    await member.add_roles(role, reason='Verification successful')
                if unverified_role and unverified_role in member.roles:
                    await member.remove_roles(unverified_role, reason='Verification successful')
                await member.bot.signal_verification_success(member)
                return True
            except discord.Forbidden:
                return False

        if mode == 'button':
            if await grant_access(interaction.user):
                await interaction.response.send_message('Verification successful!', ephemeral=True)
            else:
                await interaction.response.send_message("I don't have permission to manage your roles.", ephemeral=True)
        else:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            width, height = (200, 80)
            image = Image.new('RGB', (width, height), color=(255, 255, 255))
            draw = ImageDraw.Draw(image)
            font = ImageFont.load_default()
            for i, char in enumerate(code):
                draw.text((20 + i * 30, 20), char, fill=(0, 0, 0), font=font)
            for _ in range(5):
                draw.line([(random.randint(0, width), random.randint(0, height)), (random.randint(0, width), random.randint(0, height))], fill=(128, 128, 128), width=2)
            image = image.filter(ImageFilter.GaussianBlur(radius=0.5))
            buffer = io.BytesIO()
            image.save(buffer, format='PNG')
            buffer.seek(0)
            file = discord.File(buffer, filename='captcha.png')

            class CaptchaTriggerView(discord.ui.View):
                def __init__(self, correct_code, member, role, unverified_role, main_role):
                    super().__init__(timeout=120)
                    self.correct_code = correct_code
                    self.member = member
                    self.role = role
                    self.unverified_role = unverified_role
                    self.main_role = main_role

                @discord.ui.button(label='Enter Code', style=discord.ButtonStyle.blurple)
                async def enter_code(self, itn: discord.Interaction, btn: discord.ui.Button):
                    modal = CaptchaModal(self.correct_code, self.member, self.role)
                    modal.unverified_role = self.unverified_role
                    modal.main_role = self.main_role
                    await itn.response.send_modal(modal)
            await interaction.response.send_message(content='Please enter the code shown in the image below to verify.', file=file, view=CaptchaTriggerView(code, interaction.user, role, unverified_role, main_role), ephemeral=True)

class Verification(commands.Cog):
    category = 'config'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager

    async def get_config(self, guild_id):
        return await self.bot.get_config('verification_config', guild_id)

    async def update_config(self, guild_id, data):
        await self.bot.update_config('verification_config', guild_id, data)

    @commands.group(name='verify', invoke_without_command=True, help='Manage verification settings.')
    @commands.has_permissions(administrator=True)
    async def verify_group(self, ctx):
        config = await self.get_config(ctx.guild.id)
        if not config:
            return await ctx.info('Verification is not configured.')
        role = ctx.guild.get_role(config.get('role_id'))
        main_role = ctx.guild.get_role(config.get('main_role_id'))
        unverified_role = ctx.guild.get_role(config.get('unverified_role_id'))
        mode = config.get('mode', 'button')
        channel = ctx.guild.get_channel(config.get('channel_id'))
        delay = config.get('joingate_delay', 0)
        description = f"**Mode:** {mode.capitalize()}\n**Join-Gate:** {delay}s\n**Main Role:** {(main_role.mention if main_role else 'None')}\n**Verified Role:** {(role.mention if role else 'Not set')}\n**Unverified Role:** {(unverified_role.mention if unverified_role else 'None')}\n**Channel:** {(channel.mention if channel else 'Not set')}"
        await ctx.embed(description, title='Verification Settings')

    @verify_group.command(name='setup', help='Setup the verification system.')
    @commands.has_permissions(administrator=True, manage_channels=True, manage_roles=True)
    async def verify_setup(self, ctx, mode: str, verified_role: discord.Role, unverified_role: discord.Role=None, main_role: discord.Role=None, channel: discord.TextChannel=None):
        mode = mode.lower()
        if mode not in ['button', 'captcha']:
            return await ctx.error('Invalid mode. Use `button` or `captcha`.')
        channel = channel or ctx.channel
        config = {'mode': mode, 'role_id': verified_role.id, 'unverified_role_id': unverified_role.id if unverified_role else None, 'main_role_id': main_role.id if main_role else None, 'channel_id': channel.id, 'enabled': True}
        await self.update_config(ctx.guild.id, config)
        if unverified_role:
            await ctx.info(f'Locking down channels for {unverified_role.mention}...')
            for ch in ctx.guild.channels:
                try:
                    if ch.id == channel.id:
                        await ch.set_permissions(unverified_role, view_channel=True, send_messages=False, read_message_history=True)
                    else:
                        await ch.set_permissions(unverified_role, view_channel=False)
                except:
                    continue
        view = VerificationView()
        embed = self.bot.embed_manager.generic(description='Click the button below to verify and gain access to the server.', title='Server Verification')
        await channel.send(embed=embed, view=view)
        await ctx.success(f'Verification system set up in {channel.mention} with **{mode}** mode.')

    @verify_group.command(name='joingate', help='Set the delay (seconds) before a user can verify.')
    @commands.has_permissions(administrator=True)
    async def verify_joingate(self, ctx, seconds: int):
        await self.update_config(ctx.guild.id, {'joingate_delay': seconds})
        await ctx.success(f'Join-Gate delay set to **{seconds} seconds**.')

    @verify_group.command(name='mainrole', help='Set the main role for all members.')
    @commands.has_permissions(administrator=True)
    async def verify_mainrole(self, ctx, role: discord.Role):
        await self.update_config(ctx.guild.id, {'main_role_id': role.id})
        await ctx.success(f'Main role set to {role.mention}.')

    @verify_group.command(name='disable', help='Disable the verification system.')
    @commands.has_permissions(administrator=True)
    async def verify_disable(self, ctx):
        await self.bot.db_manager.delete_one('verification_config', {'_id': ctx.guild.id})
        self.bot.invalidate_config('verification_config', ctx.guild.id)
        await ctx.success('Verification system has been disabled.')

async def setup(bot):
    await bot.add_cog(Verification(bot))
