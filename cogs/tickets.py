import discord
from discord.ext import commands
import uuid
import time
import datetime
import io
import json
import aiohttp
import re

class TicketModal(discord.ui.Modal):
    def __init__(self, panel_data, bot):
        super().__init__(title=f"{panel_data['name']} - Questionnaire")
        self.panel_data = panel_data
        self.bot = bot
        
        self.reason = discord.ui.TextInput(
            label="Reason for opening this ticket",
            placeholder="Please describe your issue in detail...",
            style=discord.TextStyle.paragraph,
            required=True,
            min_length=10,
            max_length=1000
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        
        config = await self.bot.db_manager.find_one('ticket_config', {'_id': guild.id})
        active_tickets = await self.bot.db_manager.find_one('active_tickets_count', {'_id': f"{guild.id}:{user.id}"}) or {'count': 0}
        
        is_premium, _ = await self.bot.premium_manager.get_premium_status(guild.id)
        limit = 5 if is_premium else 1
        
        if active_tickets['count'] >= limit:
            return await interaction.response.send_message(f"You have reached the maximum limit of {limit} active tickets in this server.", ephemeral=True)

        category = guild.get_channel(self.panel_data['category_id'])
        if not category:
            return await interaction.response.send_message("The ticket category no longer exists. Please contact an administrator.", ephemeral=True)

        ticket_id = str(uuid.uuid4())[:8]
        channel_name = f"ticket-{user.name}-{ticket_id}"
        channel_name = re.sub(r'[^a-zA-Z0-9-]', '', channel_name)[:100]
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True, embed_links=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, manage_channels=True, manage_permissions=True)
        }
        
        for role_id in self.panel_data.get('roles', []):
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        config = await self.bot.db_manager.find_one('ticket_config', {'_id': guild.id})
        if config and 'staff_roles' in config:
            for role_id in config['staff_roles']:
                role = guild.get_role(role_id)
                if role:
                    overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        try:
            channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                reason=f"Ticket opened by {user} (Panel: {self.panel_data['name']})"
            )
        except Exception as e:
            return await interaction.response.send_message(f"Failed to create ticket channel: {e}", ephemeral=True)

        await self.bot.db_manager.update_one('active_tickets', {'_id': channel.id}, {
            'guild_id': guild.id,
            'user_id': user.id,
            'panel_id': self.panel_data['id'],
            'opened_at': time.time(),
            'status': 'open',
            'reason': self.reason.value,
            'welcome_msg_id': None # Will be updated after sending
        }, upsert=True)
        
        await self.bot.db_manager.update_one('active_tickets_count', {'_id': f"{guild.id}:{user.id}"}, {'$inc': {'count': 1}}, upsert=True)

        embed = self.bot.embed_manager.generic(
            title=f"Ticket: {self.panel_data['name']}",
            description=f"Welcome {user.mention}, support will be with you shortly.\n\n**Reason provided:**\n{self.reason.value}"
        )
        embed.set_footer(text=f"Ticket ID: {ticket_id} | User ID: {user.id}")
        
        view = TicketControlView(self.bot)
        welcome_msg = await channel.send(content=f"{user.mention} | <@&{self.panel_data['roles'][0]}>" if self.panel_data.get('roles') else user.mention, embed=embed, view=view)
        
        await self.bot.db_manager.update_one('active_tickets', {'_id': channel.id}, {'welcome_msg_id': welcome_msg.id})
        
        await interaction.response.send_message(f"Your ticket has been created: {channel.mention}", ephemeral=True)

class TicketTypeSelect(discord.ui.Select):
    def __init__(self, panel, bot):
        self.panel = panel
        self.bot = bot
        options = []
        for cat in panel.get('categories', []):
            options.append(discord.SelectOption(
                label=cat['name'],
                value=cat['id'],
                emoji=cat.get('emoji'),
                description=cat.get('description', f"Open a {cat['name']} ticket")
            ))
        super().__init__(
            placeholder="Select a ticket category...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="ticket_select_global"
        )

    async def callback(self, interaction: discord.Interaction):
        cog = self.bot.get_cog('Tickets')
        config = await cog.get_guild_config(interaction.guild.id)
        if not config:
            return await interaction.response.send_message("Ticket system not configured.", ephemeral=True)
            
        panel = next((p for p in config.get('panels', []) if p['message_id'] == interaction.message.id), None)
        if not panel:
            return await interaction.response.send_message("Panel not found.", ephemeral=True)

        selected_cat = next((c for c in panel.get('categories', []) if c['id'] == self.values[0]), None)
        if not selected_cat:
            return await interaction.response.send_message("Category not found.", ephemeral=True)

        if interaction.user.id in config.get('blacklist', []):
            return await interaction.response.send_message("You are blacklisted.", ephemeral=True)

        active_tickets = await self.bot.db_manager.find_one('active_tickets_count', {'_id': f"{interaction.guild.id}:{interaction.user.id}"}) or {'count': 0}
        is_premium, _ = await self.bot.premium_manager.get_premium_status(interaction.guild.id)
        limit = 5 if is_premium else 1
        
        if active_tickets['count'] >= limit:
            return await interaction.response.send_message(f"Active ticket limit reached ({limit}).", ephemeral=True)

        modal_data = panel.copy()
        modal_data.update(selected_cat)
        modal_data['name'] = f"{panel['name']} - {selected_cat['name']}"
        
        await interaction.response.send_modal(TicketModal(modal_data, self.bot))

class TicketPanelView(discord.ui.View):
    def __init__(self, bot, panel_data=None):
        super().__init__(timeout=None)
        self.bot = bot
        if panel_data and panel_data.get('categories'):
            self.add_item(TicketTypeSelect(panel_data, bot))
        else:
            button = discord.ui.Button(
                label="Create Ticket",
                style=discord.ButtonStyle.primary,
                emoji="🎫",
                custom_id="ticket_panel_create_global"
            )
            button.callback = self.create_ticket_callback
            self.add_item(button)

    async def create_ticket_callback(self, interaction: discord.Interaction):
        cog = self.bot.get_cog('Tickets')
        config = await cog.get_guild_config(interaction.guild.id)
        if not config:
            return await interaction.response.send_message("Ticket system is not configured for this server.", ephemeral=True)
        
        panel = next((p for p in config.get('panels', []) if p['message_id'] == interaction.message.id), None)
        if not panel:
            return await interaction.response.send_message("This panel configuration was not found.", ephemeral=True)

        if interaction.user.id in config.get('blacklist', []):
            return await interaction.response.send_message("You are blacklisted from using the ticket system.", ephemeral=True)

        active_tickets = await self.bot.db_manager.find_one('active_tickets_count', {'_id': f"{interaction.guild.id}:{interaction.user.id}"}) or {'count': 0}
        is_premium, _ = await self.bot.premium_manager.get_premium_status(interaction.guild.id)
        limit = 5 if is_premium else 1
        
        if active_tickets['count'] >= limit:
            return await interaction.response.send_message(f"You already have {active_tickets['count']} active ticket(s). Max allowed: {limit}", ephemeral=True)

        await interaction.response.send_modal(TicketModal(panel, self.bot))

class TicketCloseConfirmView(discord.ui.View):
    def __init__(self, bot, opener_id):
        super().__init__(timeout=60)
        self.bot = bot
        self.opener_id = opener_id

    @discord.ui.button(label="Confirm Close", style=discord.ButtonStyle.danger, emoji="🔒")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await perform_ticket_close(self.bot, interaction)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Ticket closure cancelled.", view=None, delete_after=5)

class TicketControlView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.success, emoji="👋", custom_id="ticket_claim_global")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket = await self.bot.db_manager.find_one('active_tickets', {'_id': interaction.channel.id})
        if not ticket:
            return await interaction.response.send_message("This channel is not an active ticket.", ephemeral=True)

        panel_roles = []
        config = await self.bot.db_manager.find_one('ticket_config', {'_id': interaction.guild.id})
        if config:
            panel = next((p for p in config.get('panels', []) if p['id'] == ticket.get('panel_id')), None)
            if panel: panel_roles = panel.get('roles', [])

        cog = self.bot.get_cog('Tickets')
        if not cog or not await cog.is_staff(interaction.user, panel_roles):
            return await interaction.response.send_message("Only staff can claim tickets.", ephemeral=True)

        if ticket.get('claimed_by'):
            return await interaction.response.send_message(f"This ticket is already claimed by <@{ticket['claimed_by']}>.", ephemeral=True)

        await self.bot.db_manager.update_one('active_tickets', {'_id': interaction.channel.id}, {'claimed_by': interaction.user.id})
        
        try:
            new_name = f"claimed-{interaction.user.name}"
            new_name = re.sub(r'[^a-zA-Z0-9-]', '', new_name)[:100]
            await interaction.channel.edit(name=new_name)
        except: pass

        try:
            if ticket.get('welcome_msg_id'):
                msg = await interaction.channel.fetch_message(ticket['welcome_msg_id'])
                if msg:
                    view = TicketControlView(self.bot)
                    for item in view.children:
                        if isinstance(item, discord.ui.Button) and item.custom_id == "ticket_claim_global":
                            item.label = f"Claimed by {interaction.user.display_name}"
                            item.disabled = True
                    await msg.edit(view=view)
        except: pass

        await interaction.response.send_message(f"Ticket has been claimed by {interaction.user.mention}.")

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="ticket_close_global")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket = await self.bot.db_manager.find_one('active_tickets', {'_id': interaction.channel.id})
        if not ticket:
            return await interaction.response.send_message("This channel is not an active ticket.", ephemeral=True)

        panel_roles = []
        config = await self.bot.db_manager.find_one('ticket_config', {'_id': interaction.guild.id})
        if config:
            panel = next((p for p in config.get('panels', []) if p['id'] == ticket.get('panel_id')), None)
            if panel: panel_roles = panel.get('roles', [])

        cog = self.bot.get_cog('Tickets')
        is_staff = cog and await cog.is_staff(interaction.user, panel_roles)
        is_opener = interaction.user.id == ticket.get('user_id')

        if not is_staff and not is_opener:
            return await interaction.response.send_message("You do not have permission to close this ticket.", ephemeral=True)

        view = TicketCloseConfirmView(self.bot, ticket.get('user_id'))
        await interaction.response.send_message("Are you sure you want to close this ticket?", view=view)

async def perform_ticket_close(bot, interaction: discord.Interaction):
    await interaction.response.edit_message(content="Closing ticket and generating transcript...", view=None)
    
    transcript = []
    transcript.append("=" * 50)
    transcript.append(f"HORIZEN SYSTEMS - TICKET TRANSCRIPT")
    transcript.append(f"Ticket: {interaction.channel.name}")
    transcript.append(f"Server: {interaction.guild.name} ({interaction.guild.id})")
    transcript.append(f"Generated at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    transcript.append("=" * 50)
    transcript.append("")

    async for message in interaction.channel.history(limit=None, oldest_first=True):
        timestamp = message.created_at.strftime('%Y-%m-%d %H:%M:%S')
        author = str(message.author)
        content = message.content or "[No text content]"
        
        line = f"[{timestamp}] {author}: {content}"
        if message.attachments:
            line += f" | [ATTACHMENTS: {', '.join(a.url for a in message.attachments)}]"
        transcript.append(line)

    transcript_text = "\n".join(transcript)
    file_bytes = transcript_text.encode('utf-8')

    ticket = await bot.db_manager.find_one('active_tickets', {'_id': interaction.channel.id})
    if ticket:
        user_id = ticket.get('user_id')
        user = interaction.guild.get_member(user_id)
        if user:
            try:
                await user.send(
                    f"Your ticket in **{interaction.guild.name}** has been closed.",
                    file=discord.File(io.BytesIO(file_bytes), filename=f"transcript-{interaction.channel.name}.txt")
                )
            except: pass
        
        await bot.db_manager.update_one('active_tickets_count', {'_id': f"{interaction.guild.id}:{user_id}"}, {'$inc': {'count': -1}})
        await bot.db_manager.delete_one('active_tickets', {'_id': interaction.channel.id})

    log_cog = bot.get_cog('Logging')
    if log_cog:
        embed = discord.Embed(
            title="Ticket Closed",
            description=f"**Ticket:** {interaction.channel.name}\n**Closed by:** {interaction.user.mention} ({interaction.user.id})",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        await log_cog.log_tickets(
            interaction.guild, 
            embed, 
            file=discord.File(io.BytesIO(file_bytes), filename=f"transcript-{interaction.channel.name}.txt")
        )

    await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")

class Tickets(commands.Cog):
    category = 'config'

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    async def get_guild_config(self, guild_id):
        return await self.bot.get_config('ticket_config', guild_id)

    async def update_config(self, guild_id, data):
        await self.bot.update_config('ticket_config', guild_id, data)

    async def is_staff(self, member: discord.Member, panel_roles: list = None):
        if member.guild_permissions.administrator:
            return True

        config = await self.get_guild_config(member.guild.id)
        if not config:
            return False

        staff_roles = config.get('staff_roles', [])
        if any(role.id in staff_roles for role in member.roles):
            return True

        if panel_roles and any(role.id in panel_roles for role in member.roles):
            return True

        return False

    @commands.group(name='ticket', invoke_without_command=True, help='Manage the ticket system.')
    @commands.has_permissions(administrator=True)
    async def ticket_group(self, ctx):
        config = await self.get_guild_config(ctx.guild.id)
        if not config or not config.get('panels'):
            return await ctx.info("No ticket panels configured. Use `ticket setup` to create one.")

        desc = "**Active Panels:**\n"
        for panel in config['panels']:
            roles = ", ".join(f"<@&{r}>" for r in panel.get('roles', []))
            desc += f"• **{panel['name']}** (ID: `{panel['id']}`)\n  - Default Category: <#{panel['category_id']}>\n  - Roles: {roles}\n"

            if panel.get('categories'):
                desc += "  - **Sub-Categories:**\n"
                for cat in panel['categories']:
                    emoji_str = f"{cat['emoji']} " if cat.get('emoji') else ""
                    desc += f"    └ {emoji_str}{cat['name']} (ID: `{cat['id']}`) -> <#{cat['category_id']}>\n"

        staff_roles = config.get('staff_roles', [])
        if staff_roles:
            desc += f"\n**Global Staff Roles:** {', '.join(f'<@&{r}>' for r in staff_roles)}"

        await ctx.embed(desc, title="Ticket System Configuration")

    @ticket_group.group(name='staff', invoke_without_command=True, help='Manage global ticket staff roles.')
    @commands.has_permissions(administrator=True)
    async def staff_group(self, ctx):
        await ctx.send_help(ctx.command)

    @staff_group.command(name='add', help='Add a global staff role for tickets.')
    @commands.has_permissions(administrator=True)
    async def staff_add(self, ctx, role: discord.Role):
        await self.bot.db_manager.update_one('ticket_config', {'_id': ctx.guild.id}, {'$addToSet': {'staff_roles': role.id}}, upsert=True)
        self.bot.invalidate_config('ticket_config', ctx.guild.id)
        await ctx.success(f"{role.mention} has been added as a global ticket staff role.")

    @staff_group.command(name='remove', help='Remove a global staff role.')
    @commands.has_permissions(administrator=True)
    async def staff_remove(self, ctx, role: discord.Role):
        await self.bot.db_manager.update_one('ticket_config', {'_id': ctx.guild.id}, {'$pull': {'staff_roles': role.id}})
        self.bot.invalidate_config('ticket_config', ctx.guild.id)
        await ctx.success(f"{role.mention} has been removed from global ticket staff roles.")

    @ticket_group.command(name='category', help='Update the category for a ticket panel.')
    @commands.has_permissions(administrator=True)
    async def ticket_category(self, ctx, panel_id: str, category: discord.CategoryChannel):
        config = await self.get_guild_config(ctx.guild.id)
        if not config: return await ctx.error("No ticket system configured.")

        panels = config.get('panels', [])
        found = False
        for p in panels:
            if p['id'] == panel_id:
                p['category_id'] = category.id
                found = True
                break

        if not found: return await ctx.error("Panel ID not found.")

        await self.bot.db_manager.update_one('ticket_config', {'_id': ctx.guild.id}, {'panels': panels})
        await ctx.success(f"Category for panel `{panel_id}` has been updated to **{category.name}**.")

    @ticket_group.group(name='type', invoke_without_command=True, help='Manage ticket types/categories within a panel.')
    @commands.has_permissions(administrator=True)
    async def type_group(self, ctx):
        await ctx.send_help(ctx.command)

    @type_group.command(name='add', help='Add a ticket type/category to a panel.')
    @commands.has_permissions(administrator=True)
    async def type_add(self, ctx, panel_id: str, name: str, category: discord.CategoryChannel, emoji: str = None):
        is_premium, _ = await self.bot.premium_manager.get_premium_status(ctx.guild.id)
        config = await self.get_guild_config(ctx.guild.id)
        if not config: return await ctx.error("No ticket system configured.")
        
        panels = config.get('panels', [])
        panel = next((p for p in panels if p['id'] == panel_id), None)
        if not panel: return await ctx.error("Panel ID not found.")
        
        if 'categories' not in panel: panel['categories'] = []
        
        cat_limit = 20 if is_premium else 10
        if len(panel['categories']) >= cat_limit:
            return await ctx.error(f"This panel has reached the limit of {cat_limit} categories.")

        new_cat = {
            'id': str(uuid.uuid4())[:8],
            'name': name,
            'category_id': category.id,
            'emoji': emoji
        }
        
        panel['categories'].append(new_cat)
        await self.bot.db_manager.update_one('ticket_config', {'_id': ctx.guild.id}, {'panels': panels})
        
        target_channel = ctx.guild.get_channel(panel['channel_id'])
        if target_channel:
            try:
                msg = await target_channel.fetch_message(panel['message_id'])
                if msg: await msg.edit(view=TicketPanelView(self.bot, panel))
            except: pass
            
        await ctx.success(f"Ticket type **{name}** added to panel `{panel_id}`.")

    @type_group.command(name='remove', help='Remove a ticket type from a panel.')
    @commands.has_permissions(administrator=True)
    async def type_remove(self, ctx, panel_id: str, type_id: str):
        config = await self.get_guild_config(ctx.guild.id)
        if not config: return await ctx.error("No ticket system configured.")
        
        panels = config.get('panels', [])
        panel = next((p for p in panels if p['id'] == panel_id), None)
        if not panel: return await ctx.error("Panel ID not found.")
        
        if 'categories' not in panel: return await ctx.error("This panel has no categories.")
        
        panel['categories'] = [c for c in panel['categories'] if c['id'] != type_id]
        
        await self.bot.db_manager.update_one('ticket_config', {'_id': ctx.guild.id}, {'panels': panels})
        
        target_channel = ctx.guild.get_channel(panel['channel_id'])
        if target_channel:
            try:
                msg = await target_channel.fetch_message(panel['message_id'])
                if msg: await msg.edit(view=TicketPanelView(self.bot, panel))
            except: pass
            
        await ctx.success(f"Ticket type removed from panel `{panel_id}`.")

    @ticket_group.command(name='setup', help='Launch the ticket panel setup wizard.')
    @commands.has_permissions(administrator=True)
    async def ticket_setup(self, ctx):
        is_premium, _ = await self.bot.premium_manager.get_premium_status(ctx.guild.id)
        config = await self.get_guild_config(ctx.guild.id) or {'panels': []}
        
        panel_limit = 15 if is_premium else 1
        if len(config.get('panels', [])) >= panel_limit:
            return await ctx.error(f"You have reached the maximum limit of {panel_limit} panel(s). {'Upgrade to Premium for more!' if not is_premium else ''}")

        await ctx.send("Starting Ticket Setup Wizard. Please answer the following questions.")
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            await ctx.send("1. What should be the **name** of this panel? (e.g., General Support)")
            name_msg = await self.bot.wait_for('message', check=check, timeout=60)
            name = name_msg.content

            await ctx.send("2. Which **channel** should the panel be sent to? (Mention the channel)")
            chan_msg = await self.bot.wait_for('message', check=check, timeout=60)
            try:
                chan_id = int(chan_msg.content.replace('<#', '').replace('>', ''))
                target_channel = ctx.guild.get_channel(chan_id)
            except: target_channel = None
            if not target_channel: return await ctx.error("Invalid channel.")

            await ctx.send("3. Do you want this panel to have **multiple categories**? (yes/no)\n*Multiple categories use a dropdown menu instead of a button.*")
            multi_msg = await self.bot.wait_for('message', check=check, timeout=60)
            use_multi = multi_msg.content.lower() in ['yes', 'y']

            await ctx.send("4. Which **category** should the *default* tickets be created in? (Provide ID)")
            cat_msg = await self.bot.wait_for('message', check=check, timeout=60)
            try:
                category = ctx.guild.get_channel(int(cat_msg.content))
            except: category = None
            if not category or not isinstance(category, discord.CategoryChannel):
                return await ctx.error("Invalid category ID.")

            await ctx.send("5. Which **role** should handle these tickets? (Mention the role)")
            role_msg = await self.bot.wait_for('message', check=check, timeout=60)
            try:
                role_id = int(role_msg.content.replace('<@&', '').replace('>', ''))
                role = ctx.guild.get_role(role_id)
            except: role = None
            if not role: return await ctx.error("Invalid role.")

        except Exception as e:
            return await ctx.error(f"Setup failed or timed out: {e}")

        panel_id = str(uuid.uuid4())[:8]
        
        panel_data = {
            'id': panel_id,
            'name': name,
            'channel_id': target_channel.id,
            'category_id': category.id,
            'roles': [role.id],
            'categories': []
        }

        if use_multi:
            panel_data['categories'].append({
                'id': str(uuid.uuid4())[:8],
                'name': 'General Support',
                'category_id': category.id,
                'emoji': '🎫'
            })

        embed = self.bot.embed_manager.generic(
            title=name,
            description="To create a support ticket, click the button below and fill out the form." if not use_multi else "To create a support ticket, select a category from the dropdown menu below."
        )
        
        view = TicketPanelView(self.bot, panel_data)
        panel_msg = await target_channel.send(embed=embed, view=view)
        panel_data['message_id'] = panel_msg.id

        await self.bot.db_manager.update_one('ticket_config', {'_id': ctx.guild.id}, {'$push': {'panels': panel_data}}, upsert=True)
        await ctx.success(f"Ticket panel **{name}** has been setup in {target_channel.mention}!")

    @ticket_group.command(name='delete', help='Delete a ticket panel.')
    @commands.has_permissions(administrator=True)
    async def ticket_delete(self, ctx, panel_id: str):
        config = await self.get_guild_config(ctx.guild.id)
        if not config: return await ctx.error("No ticket system configured.")
        
        panels = config.get('panels', [])
        new_panels = [p for p in panels if p['id'] != panel_id]
        
        if len(panels) == len(new_panels):
            return await ctx.error("Panel ID not found.")

        await self.bot.db_manager.update_one('ticket_config', {'_id': ctx.guild.id}, {'panels': new_panels})
        await ctx.success(f"Panel `{panel_id}` has been deleted.")

    @ticket_group.command(name='blacklist', help='Blacklist a user from opening tickets.')
    @commands.has_permissions(administrator=True)
    async def ticket_blacklist(self, ctx, user: discord.Member):
        await self.bot.db_manager.update_one('ticket_config', {'_id': ctx.guild.id}, {'$addToSet': {'blacklist': user.id}}, upsert=True)
        await ctx.success(f"{user.mention} has been blacklisted from tickets.")

    @ticket_group.command(name='unblacklist', help='Remove a user from the ticket blacklist.')
    @commands.has_permissions(administrator=True)
    async def ticket_unblacklist(self, ctx, user: discord.Member):
        await self.bot.db_manager.update_one('ticket_config', {'_id': ctx.guild.id}, {'$pull': {'blacklist': user.id}})
        await ctx.success(f"{user.mention} has been removed from the ticket blacklist.")

    @ticket_group.command(name='add', help='Add a user to the current ticket.')
    @commands.has_permissions(manage_messages=True)
    async def ticket_add(self, ctx, user: discord.Member):
        ticket = await self.bot.db_manager.find_one('active_tickets', {'_id': ctx.channel.id})
        if not ticket: return await ctx.error("This is not an active ticket channel.")
        
        await ctx.channel.set_permissions(user, view_channel=True, send_messages=True, read_message_history=True)
        await ctx.success(f"{user.mention} has been added to the ticket.")

    @ticket_group.command(name='remove', help='Remove a user from the current ticket.')
    @commands.has_permissions(manage_messages=True)
    async def ticket_remove(self, ctx, user: discord.Member):
        ticket = await self.bot.db_manager.find_one('active_tickets', {'_id': ctx.channel.id})
        if not ticket: return await ctx.error("This is not an active ticket channel.")
        
        if user.id == ticket.get('user_id'):
            return await ctx.error("You cannot remove the ticket opener.")

        await ctx.channel.set_permissions(user, overwrite=None)
        await ctx.success(f"{user.mention} has been removed from the ticket.")

    @ticket_group.command(name='rename', help='Rename the current ticket channel.')
    @commands.has_permissions(manage_messages=True)
    async def ticket_rename(self, ctx, *, name: str):
        ticket = await self.bot.db_manager.find_one('active_tickets', {'_id': ctx.channel.id})
        if not ticket: return await ctx.error("This is not an active ticket channel.")
        
        clean_name = re.sub(r'[^a-zA-Z0-9-]', '', name.replace(' ', '-')).lower()[:100]
        await ctx.channel.edit(name=clean_name)
        await ctx.success(f"Channel renamed to `{clean_name}`.")

    @ticket_group.command(name='close', help='Close the current ticket.')
    @commands.has_permissions(manage_messages=True)
    async def ticket_close_cmd(self, ctx):
        ticket = await self.bot.db_manager.find_one('active_tickets', {'_id': ctx.channel.id})
        if not ticket: return await ctx.error("This is not an active ticket channel.")
        
        view = TicketCloseConfirmView(self.bot, ticket.get('user_id'))
        await ctx.send("Are you sure you want to close this ticket?", view=view)

async def setup(bot):
    await bot.add_cog(Tickets(bot))
