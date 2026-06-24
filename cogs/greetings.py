import discord
from discord.ext import commands
import json
import re
import asyncio
import datetime
import io
import aiohttp
from PIL import Image, ImageDraw, ImageFont, ImageOps

class EmbedEditorModal(discord.ui.Modal):
    def __init__(self, bot, embed_name, key, label, current_val=""):
        super().__init__(title=f"Editing {label}")
        self.bot = bot
        self.embed_name = embed_name
        self.key = key
        self.input = discord.ui.TextInput(
            label=label,
            default=current_val,
            style=discord.TextStyle.paragraph if key == 'description' else discord.TextStyle.short,
            required=False
        )
        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction):
        config = await self.bot.db_manager.find_one('greetings_config', {'_id': interaction.guild.id})
        if not config or self.embed_name not in config.get('custom_embeds', {}):
            return await interaction.response.send_message("Embed not found.", ephemeral=True)
        config['custom_embeds'][self.embed_name][self.key] = self.input.value
        await self.bot.db_manager.update_one('greetings_config', {'_id': interaction.guild.id}, {'custom_embeds': config['custom_embeds']})
        await interaction.response.send_message(f"Updated **{self.key}** successfully.", ephemeral=True)
        if hasattr(self, 'view_ref'):
            await self.view_ref.update_editor_msg(interaction)

class EmbedEditorView(discord.ui.View):
    def __init__(self, bot, author, embed_name):
        super().__init__(timeout=300)
        self.bot = bot
        self.author = author
        self.name = embed_name

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.author:
            await interaction.response.send_message("This editor is not for you.", ephemeral=True)
            return False
        return True

    async def update_editor_msg(self, interaction):
        config = await self.bot.db_manager.find_one('greetings_config', {'_id': interaction.guild.id})
        data = config['custom_embeds'][self.name]
        preview = discord.Embed(title=f"Editor: {self.name}", description="Use the buttons below to customize your template.", color=discord.Color.blue())
        preview.add_field(name="Current Configuration", value=f"```json\n{json.dumps(data, indent=2)}\n```")
        try: await interaction.edit_original_response(embed=preview, view=self)
        except: pass

    @discord.ui.button(label='Title', style=discord.ButtonStyle.secondary)
    async def edit_title(self, interaction, button):
        config = await self.bot.db_manager.find_one('greetings_config', {'_id': interaction.guild.id})
        current = config['custom_embeds'][self.name].get('title', '')
        modal = EmbedEditorModal(self.bot, self.name, 'title', 'Embed Title', current)
        modal.view_ref = self
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='Description', style=discord.ButtonStyle.secondary)
    async def edit_desc(self, interaction, button):
        config = await self.bot.db_manager.find_one('greetings_config', {'_id': interaction.guild.id})
        current = config['custom_embeds'][self.name].get('description', '')
        modal = EmbedEditorModal(self.bot, self.name, 'description', 'Embed Description', current)
        modal.view_ref = self
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='Color', style=discord.ButtonStyle.secondary)
    async def edit_color(self, interaction, button):
        config = await self.bot.db_manager.find_one('greetings_config', {'_id': interaction.guild.id})
        current = config['custom_embeds'][self.name].get('color', '')
        modal = EmbedEditorModal(self.bot, self.name, 'color', 'Hex Color (e.g. #ff0000)', current)
        modal.view_ref = self
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='Media', style=discord.ButtonStyle.secondary)
    async def edit_media(self, interaction, button):
        class MediaModal(discord.ui.Modal, title="Media & URLs"):
            img = discord.ui.TextInput(label="Large Image URL", required=False)
            thumb = discord.ui.TextInput(label="Small Thumbnail URL", required=False)
            async def on_submit(self, itn):
                config = await self.view_ref.bot.db_manager.find_one('greetings_config', {'_id': itn.guild.id})
                config['custom_embeds'][self.view_ref.name]['image'] = self.img.value
                config['custom_embeds'][self.view_ref.name]['thumbnail'] = self.thumb.value
                await self.view_ref.bot.db_manager.update_one('greetings_config', {'_id': itn.guild.id}, {'custom_embeds': config['custom_embeds']})
                await itn.response.send_message("Media updated.", ephemeral=True)
                await self.view_ref.update_editor_msg(itn)
        modal = MediaModal()
        modal.view_ref = self
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='Author', style=discord.ButtonStyle.secondary)
    async def edit_author(self, interaction, button):
        class AuthorModal(discord.ui.Modal, title="Author Info"):
            name = discord.ui.TextInput(label="Author Name", required=False)
            icon = discord.ui.TextInput(label="Author Icon URL", required=False)
            async def on_submit(self, itn):
                config = await self.view_ref.bot.db_manager.find_one('greetings_config', {'_id': itn.guild.id})
                config['custom_embeds'][self.view_ref.name]['author_name'] = self.name.value
                config['custom_embeds'][self.view_ref.name]['author_icon'] = self.icon.value
                await self.view_ref.bot.db_manager.update_one('greetings_config', {'_id': itn.guild.id}, {'custom_embeds': config['custom_embeds']})
                await itn.response.send_message("Author updated.", ephemeral=True)
                await self.view_ref.update_editor_msg(itn)
        modal = AuthorModal()
        modal.view_ref = self
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='Footer', style=discord.ButtonStyle.secondary)
    async def edit_footer(self, interaction, button):
        config = await self.bot.db_manager.find_one('greetings_config', {'_id': interaction.guild.id})
        current = config['custom_embeds'][self.name].get('footer', '')
        modal = EmbedEditorModal(self.bot, self.name, 'footer', 'Embed Footer', current)
        modal.view_ref = self
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='Preview', style=discord.ButtonStyle.success)
    async def preview(self, interaction, button):
        config = await self.bot.db_manager.find_one('greetings_config', {'_id': interaction.guild.id})
        data = config['custom_embeds'][self.name]
        cog = self.bot.get_cog('Greetings')
        embed = discord.Embed(
            title=cog._parse_variables(data.get('title', ''), interaction.user),
            description=cog._parse_variables(data.get('description', ''), interaction.user),
            color=int(str(data.get('color', '0x4A3F5F')).replace('0x', '').replace('#', ''), 16)
        )
        if data.get('image'): embed.set_image(url=cog._parse_variables(data['image'], interaction.user))
        if data.get('thumbnail'): embed.set_thumbnail(url=cog._parse_variables(data['thumbnail'], interaction.user))
        if data.get('footer'): embed.set_footer(text=cog._parse_variables(data['footer'], interaction.user))
        if data.get('author_name'): embed.set_author(name=cog._parse_variables(data['author_name'], interaction.user), icon_url=cog._parse_variables(data.get('author_icon', ''), interaction.user))
        await interaction.response.send_message(embed=embed, ephemeral=True)

class Greetings(commands.Cog):
    category = 'config'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager
        self.session = aiohttp.ClientSession()

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    async def _generate_welcome_card(self, member, config):
        settings = config.get('image_settings', {})
        if not settings.get('enabled'): return None

        w, h = 700, 250
        bg_url = settings.get('background_url')
        
        try:
            if bg_url:
                async with self.session.get(bg_url) as r:
                    bg = Image.open(io.BytesIO(await r.read())).convert("RGBA").resize((w, h), Image.Resampling.LANCZOS)
            else:
                bg = Image.new('RGBA', (w, h), (25, 25, 30))
        except:
            bg = Image.new('RGBA', (w, h), (25, 25, 30))

        # Avatar
        try:
            async with self.session.get(str(member.display_avatar.with_format('png').url)) as r:
                av = Image.open(io.BytesIO(await r.read())).convert("RGBA").resize((150, 150), Image.Resampling.LANCZOS)
        except:
            av = Image.new('RGBA', (150, 150), (50, 50, 50))

        mask = Image.new('L', (150, 150), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 150, 150), fill=255)
        
        bg.paste(av, (20, 50), mask)

        draw = ImageDraw.Draw(bg)
        f_p = "/data/data/com.termux/files/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"
        def get_f(s):
            try: return ImageFont.truetype(f_p, s)
            except: return ImageFont.load_default()

        color = settings.get('text_color', '#FFFFFF')
        
        draw.text((190, 70), f"Welcome to {member.guild.name}", font=get_f(30), fill=color)
        draw.text((190, 110), member.name, font=get_f(45), fill=color)
        draw.text((190, 170), f"Member #{member.guild.member_count}", font=get_f(25), fill=color)

        buf = io.BytesIO()
        bg.save(buf, 'PNG')
        buf.seek(0)
        return discord.File(buf, filename="welcome.png")

    def _parse_variables(self, text, member: discord.Member):
        if not text: return ""
        guild = member.guild
        ordinal = lambda n: "%d%s" % (n, "tsnrhtdd"[(n//10%10!=1)*(n%10<4)*n%10::4])
        now = discord.utils.utcnow()
        age = (now - member.created_at).days
        variables = {
            '{user}': member.mention,
            '{user_mention}': member.mention,
            '{user_name}': member.name,
            '{user_display}': member.display_name,
            '{user_displayname}': member.display_name,
            '{user_nick}': member.nick if member.nick else member.name,
            '{user_id}': str(member.id),
            '{user_avatar}': member.display_avatar.url,
            '{user_tag}': str(member),
            '{account_age}': str(age),
            '{account_age_full}': f"{age} days ago",
            '{server_name}': guild.name,
            '{server_id}': str(guild.id),
            '{server_icon}': guild.icon.url if guild.icon else "",
            '{server_owner}': f"<@{guild.owner_id}>",
            '{server_owner_id}': str(guild.owner_id),
            '{member_count}': str(guild.member_count),
            '{member_count_ordinal}': ordinal(guild.member_count),
            '{join_date}': f"<t:{int(member.joined_at.timestamp())}:R>" if member.joined_at else "Unknown",
            '{create_date}': f"<t:{int(member.created_at.timestamp())}:R>",
            '{boost_count}': str(guild.premium_subscription_count),
            '{server_boostcount}': str(guild.premium_subscription_count),
            '{boost_level}': str(guild.premium_tier),
            '{server_boostlevel}': str(guild.premium_tier),
            '{newline}': "\n",
            '{current_time}': f"<t:{int(now.timestamp())}:T>",
            '{current_date}': f"<t:{int(now.timestamp())}:D>"
        }
        for key, value in variables.items():
            text = text.replace(key, str(value))
        return text

    async def _send_greeting(self, member, event_type):
        config = await self.db.find_one('greetings_config', {'_id': member.guild.id})
        if not config: return
        
        # Handle Image Card if it's a join event
        if event_type == 'join':
            image_file = await self._generate_welcome_card(member, config)
            if image_file:
                # Find the first join action channel
                actions = config.get('join_actions', [])
                if actions:
                    channel = member.guild.get_channel(actions[0].get('channel_id'))
                    if channel: await channel.send(file=image_file)

        actions = config.get(f'{event_type}_actions', [])
        for action in actions:
            delay = action.get('delay', 0)
            if delay > 0: await asyncio.sleep(delay)
            channel = member.guild.get_channel(action.get('channel_id'))
            is_dm = action.get('dm', False)
            if not is_dm and not channel: continue
            raw_content = action.get('message', '')
            embed = None
            embed_match = re.search(r'\{embed:([a-zA-Z0-9_-]+)\}', raw_content)
            if embed_match:
                embed_name = embed_match.group(1)
                raw_content = raw_content.replace(embed_match.group(0), "").strip()
                if config.get('custom_embeds'):
                    data = config['custom_embeds'].get(embed_name)
                    if data:
                        embed = discord.Embed(
                            title=self._parse_variables(data.get('title', ''), member),
                            description=self._parse_variables(data.get('description', ''), member),
                            color=int(str(data.get('color', '0x4A3F5F')).replace('0x', '').replace('#', ''), 16)
                        )
                        if data.get('image'): embed.set_image(url=self._parse_variables(data['image'], member))
                        if data.get('thumbnail'): embed.set_thumbnail(url=self._parse_variables(data['thumbnail'], member))
                        if data.get('footer'): embed.set_footer(text=self._parse_variables(data['footer'], member))
                        if data.get('author_name'): embed.set_author(name=self._parse_variables(data['author_name'], member), icon_url=self._parse_variables(data.get('author_icon', ''), member))
            content = self._parse_variables(raw_content, member)
            try:
                msg = None
                if is_dm: msg = await member.send(content=content if content else None, embed=embed)
                else: msg = await channel.send(content=content if content else None, embed=embed)
                delete_after = action.get('delete_after', 0)
                if delete_after > 0 and msg: await msg.delete(delay=delete_after)
            except: pass

    @commands.group(name='greet', aliases=['welcome'], invoke_without_command=True, help='Configure welcome messages (Mimu-style).')
    @commands.has_permissions(administrator=True)
    async def greet_group(self, ctx):
        config = await self.db.find_one('greetings_config', {'_id': ctx.guild.id})
        actions = config.get('join_actions', []) if config else []
        img_s = config.get('image_settings', {}) if config else {}
        desc = (
            f"**Welcome Actions:** `{len(actions)}`抽\n"
            f"**Image Greeting:** `{'Enabled' if img_s.get('enabled') else 'Disabled'}`"
        )
        await ctx.embed(desc, title="Greet Configuration")

    @greet_group.group(name='image', invoke_without_command=True, help='Manage image-based welcomes.')
    @commands.has_permissions(administrator=True)
    async def greet_image(self, ctx):
        await ctx.send_help(ctx.command)

    @greet_image.command(name='toggle', help='Enable or disable visual welcomes.')
    @commands.has_permissions(administrator=True)
    async def greet_image_toggle(self, ctx, status: bool):
        config = await self.db.find_one('greetings_config', {'_id': ctx.guild.id}) or {}
        settings = config.get('image_settings', {})
        settings['enabled'] = status
        await self.db.update_one('greetings_config', {'_id': ctx.guild.id}, {'image_settings': settings}, upsert=True)
        await ctx.success(f"Image greetings are now **{'enabled' if status else 'disabled'}**.")

    @greet_image.command(name='background', aliases=['bg'], help='Set a custom background image URL.')
    @commands.has_permissions(administrator=True)
    async def greet_image_bg(self, ctx, url: str):
        config = await self.db.find_one('greetings_config', {'_id': ctx.guild.id}) or {}
        settings = config.get('image_settings', {})
        settings['background_url'] = url
        await self.db.update_one('greetings_config', {'_id': ctx.guild.id}, {'image_settings': settings}, upsert=True)
        await ctx.success("Welcome background updated.")

    @greet_image.command(name='color', help='Set the text color (Hex).')
    @commands.has_permissions(administrator=True)
    async def greet_image_color(self, ctx, hex_code: str):
        config = await self.db.find_one('greetings_config', {'_id': ctx.guild.id}) or {}
        settings = config.get('image_settings', {})
        settings['text_color'] = hex_code
        await self.db.update_one('greetings_config', {'_id': ctx.guild.id}, {'image_settings': settings}, upsert=True)
        await ctx.success(f"Welcome text color set to `{hex_code}`.")

    @greet_group.command(name='message', help='Set the welcome message.')
    @commands.has_permissions(administrator=True)
    async def greet_message(self, ctx, *, text: str):
        config = await self.db.find_one('greetings_config', {'_id': ctx.guild.id}) or {}
        actions = config.get('join_actions', [])
        if not actions: actions.append({'channel_id': ctx.channel.id, 'dm': False})
        actions[0]['message'] = text
        await self.db.update_one('greetings_config', {'_id': ctx.guild.id}, {'join_actions': actions}, upsert=True)
        await ctx.success("Welcome message updated.")

    @greet_group.command(name='channel', help='Set the welcome channel.')
    @commands.has_permissions(administrator=True)
    async def greet_channel(self, ctx, channel: discord.TextChannel):
        config = await self.db.find_one('greetings_config', {'_id': ctx.guild.id}) or {}
        actions = config.get('join_actions', [])
        if not actions: actions.append({'message': '', 'dm': False})
        actions[0]['channel_id'] = channel.id
        await self.db.update_one('greetings_config', {'_id': ctx.guild.id}, {'join_actions': actions}, upsert=True)
        await ctx.success(f"Welcome channel set to {channel.mention}.")

    @greet_group.command(name='test', help='Test the welcome system.')
    @commands.has_permissions(administrator=True)
    async def greet_test(self, ctx):
        await self._send_greeting(ctx.author, 'join')
        await ctx.success("Test welcome message sent.")

    @commands.group(name='leave', invoke_without_command=True, help='Configure leave messages.')
    @commands.has_permissions(administrator=True)
    async def leave_group(self, ctx):
        config = await self.db.find_one('greetings_config', {'_id': ctx.guild.id})
        actions = config.get('leave_actions', []) if config else []
        await ctx.embed(f"**Leave Actions:** `{len(actions)}`抽", title="Leave Configuration")

    @leave_group.command(name='message', help='Set the leave message.')
    @commands.has_permissions(administrator=True)
    async def leave_message(self, ctx, *, text: str):
        config = await self.db.find_one('greetings_config', {'_id': ctx.guild.id}) or {}
        actions = config.get('leave_actions', [])
        if not actions: actions.append({'channel_id': ctx.channel.id})
        actions[0]['message'] = text
        await self.db.update_one('greetings_config', {'_id': ctx.guild.id}, {'leave_actions': actions}, upsert=True)
        await ctx.success("Leave message updated.")

    @leave_group.command(name='channel', help='Set the leave channel.')
    @commands.has_permissions(administrator=True)
    async def leave_channel(self, ctx, channel: discord.TextChannel):
        config = await self.db.find_one('greetings_config', {'_id': ctx.guild.id}) or {}
        actions = config.get('leave_actions', [])
        if not actions: actions.append({'message': ''})
        actions[0]['channel_id'] = channel.id
        await self.db.update_one('greetings_config', {'_id': ctx.guild.id}, {'leave_actions': actions}, upsert=True)
        await ctx.success(f"Leave channel set to {channel.mention}.")

    @leave_group.command(name='test', help='Test the leave system.')
    @commands.has_permissions(administrator=True)
    async def leave_test(self, ctx):
        await self._send_greeting(ctx.author, 'leave')
        await ctx.success("Test leave message sent.")

    @commands.group(name='boost', invoke_without_command=True, help='Configure boost messages.')
    @commands.has_permissions(administrator=True)
    async def boost_group(self, ctx):
        config = await self.db.find_one('greetings_config', {'_id': ctx.guild.id})
        actions = config.get('boost_actions', []) if config else []
        await ctx.embed(f"**Boost Actions:** `{len(actions)}`抽", title="Boost Configuration")

    @boost_group.command(name='message', help='Set the boost message.')
    @commands.has_permissions(administrator=True)
    async def boost_message(self, ctx, *, text: str):
        config = await self.db.find_one('greetings_config', {'_id': ctx.guild.id}) or {}
        actions = config.get('boost_actions', [])
        if not actions: actions.append({'channel_id': ctx.channel.id})
        actions[0]['message'] = text
        await self.db.update_one('greetings_config', {'_id': ctx.guild.id}, {'boost_actions': actions}, upsert=True)
        await ctx.success("Boost message updated.")

    @boost_group.command(name='channel', help='Set the boost channel.')
    @commands.has_permissions(administrator=True)
    async def boost_channel(self, ctx, channel: discord.TextChannel):
        config = await self.db.find_one('greetings_config', {'_id': ctx.guild.id}) or {}
        actions = config.get('boost_actions', [])
        if not actions: actions.append({'message': ''})
        actions[0]['channel_id'] = channel.id
        await self.db.update_one('greetings_config', {'_id': ctx.guild.id}, {'boost_actions': actions}, upsert=True)
        await ctx.success(f"Boost channel set to {channel.mention}.")

    @boost_group.command(name='test', help='Test the boost system.')
    @commands.has_permissions(administrator=True)
    async def boost_test(self, ctx):
        await self._send_greeting(ctx.author, 'boost')
        await ctx.success("Test boost message sent.")

    @commands.command(name='variables', help='List all message placeholders.')
    async def list_variables(self, ctx):
        desc = (
            "**Member Variables:**\n"
            "`{user}`, `{user_mention}` - User mention\n"
            "`{user_name}`, `{user_displayname}` - Display name\n"
            "`{user_nick}` - Nickname (or name)\n"
            "`{user_id}`, `{user_tag}`, `{user_avatar}`\n"
            "`{account_age}`, `{account_age_full}`, `{join_date}`, `{create_date}`\n\n"
            "**Server Variables:**\n"
            "`{server_name}`, `{server_id}`, `{server_icon}`\n"
            "`{server_owner}`, `{server_owner_id}`\n"
            "`{member_count}`, `{member_count_ordinal}`\n"
            "`{server_boostcount}`, `{server_boostlevel}`\n\n"
            "**General:**\n"
            "`{current_time}`, `{current_date}`, `{newline}`, `{embed:name}`"
        )
        await ctx.embed(desc, title="Message Placeholders")

    @commands.group(name='embed', invoke_without_command=True, help='Interactive embed editor.')
    @commands.has_permissions(administrator=True)
    async def embed_group(self, ctx):
        config = await self.db.find_one('greetings_config', {'_id': ctx.guild.id})
        embeds = config.get('custom_embeds', {}) if config else {}
        desc = "Current Templates:\n" + ("\n".join([f"• `{e}`" for e in embeds]) if embeds else "None")
        await ctx.embed(desc, title="Embed Templates")

    @embed_group.command(name='create', help='Create a new template.')
    @commands.has_permissions(administrator=True)
    async def embed_create(self, ctx, name: str):
        config = await self.bot.db_manager.find_one('greetings_config', {'_id': ctx.guild.id}) or {}
        embeds = config.get('custom_embeds', {})
        if name in embeds: return await ctx.warning(f"Embed `{name}` already exists.")
        embeds[name] = {'title': 'New Template', 'description': 'Customize me!'}
        await self.bot.db_manager.update_one('greetings_config', {'_id': ctx.guild.id}, {'custom_embeds': embeds}, upsert=True)
        await ctx.success(f"Embed template `{name}` created. Use `!embed editor {name}` to customize.")

    @embed_group.command(name='editor', help='Open the interactive live editor.')
    @commands.has_permissions(administrator=True)
    async def embed_editor(self, ctx, name: str):
        config = await self.db.find_one('greetings_config', {'_id': ctx.guild.id})
        if not config or name not in config.get('custom_embeds', {}): return await ctx.error(f"Embed `{name}` not found.")
        preview = discord.Embed(title=f"Editor: {name}", description="Use the buttons below to customize your template.", color=discord.Color.blue())
        preview.add_field(name="Current State", value=f"```json\n{json.dumps(config['custom_embeds'][name], indent=2)}\n```")
        await ctx.send(embed=preview, view=EmbedEditorView(self.bot, ctx.author, name))

    @commands.Cog.listener()
    async def on_member_join(self, member):
        await self._send_greeting(member, 'join')

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        await self._send_greeting(member, 'leave')

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if not before.premium_since and after.premium_since:
            await self._send_greeting(after, 'boost')

async def setup(bot):
    await bot.add_cog(Greetings(bot))
