import discord
from discord.ext import commands
import asyncio

class ApplicationModal(discord.ui.Modal):
    def __init__(self, bot, category_name, questions, role_id):
        super().__init__(title=f"Applying for {category_name.title()}")
        self.bot = bot
        self.category_name = category_name
        self.role_id = role_id
        self.questions = questions
        
        self.inputs = []
        for i, q in enumerate(questions):
            text_input = discord.ui.TextInput(
                label=f"Question {i+1}",
                placeholder=q[:100],
                style=discord.TextStyle.paragraph,
                max_length=1000,
                required=True
            )
            self.add_item(text_input)
            self.inputs.append(text_input)

    async def on_submit(self, interaction: discord.Interaction):
        log_cog = self.bot.get_cog('Logging')
        if not log_cog:
            return await interaction.response.send_message("Logging system not found.", ephemeral=True)

        embed = self.bot.embed_manager.generic(
            description=f"**User:** {interaction.user.mention} (`{interaction.user.id}`)\n**Category:** {self.category_name.title()}\n\n",
            title=f"New Application: {self.category_name.title()}"
        )
        embed.set_author(name=f"{interaction.user}", icon_url=interaction.user.display_avatar.url)
        
        answers = {}
        for i, q in enumerate(self.questions):
            ans = self.inputs[i].value
            embed.add_field(name=f"Q: {q}", value=ans, inline=False)
            answers[q] = ans

        view = AppReviewView(self.bot, interaction.user.id, self.role_id, self.category_name)
        
        await log_cog.log_apps(interaction.guild, embed)
        
        config = await self.bot.db_manager.find_one('app_configs', {'_id': interaction.guild.id})
        log_channel = interaction.guild.get_channel(config.get('log_channel'))
        if log_channel:
            msg = await log_channel.send(embed=embed, view=view)
        else:
            return await interaction.response.send_message("Application review channel not found.", ephemeral=True)
        
        app_data = {
            '_id': msg.id,
            'guild_id': interaction.guild.id,
            'user_id': interaction.user.id,
            'category': self.category_name,
            'answers': answers,
            'status': 'pending'
        }
        await self.bot.db_manager.update_one('submitted_apps', {'_id': msg.id}, app_data, upsert=True)
        
        await interaction.response.send_message("Your application has been submitted successfully!", ephemeral=True)

class ApplySelectView(discord.ui.View):
    def __init__(self, bot, categories):
        super().__init__(timeout=60)
        self.bot = bot
        options = []
        for name, data in categories.items():
            if data.get('enabled', True):
                options.append(discord.SelectOption(label=name.title(), value=name, description=f"Apply for {name.title()}"))
        
        if not options:
            self.stop()
            return

        self.select = discord.ui.Select(placeholder="Choose a category to apply for...", options=options)
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction):
        category_name = self.select.values[0]
        config = await self.bot.db_manager.find_one('app_configs', {'_id': interaction.guild.id})
        data = config['categories'][category_name]
        
        if data.get('required_roles'):
            user_role_ids = [r.id for r in interaction.user.roles]
            missing = [rid for rid in data['required_roles'] if rid not in user_role_ids]
            if missing:
                return await interaction.response.send_message("You do not meet the role requirements to apply for this category.", ephemeral=True)

        modal = ApplicationModal(self.bot, category_name, data['questions'], data['role_id'])
        await interaction.response.send_modal(modal)

class AppReviewView(discord.ui.View):
    def __init__(self, bot, user_id=None, role_id=None, category=None):
        super().__init__(timeout=None)
        self.bot = bot
        self.user_id = user_id
        self.role_id = role_id
        self.category = category

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.success, custom_id="app_approve")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._process_app(interaction, 'approved')

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.danger, custom_id="app_deny")
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._process_app(interaction, 'denied')

    async def _process_app(self, interaction, status):
        app = await self.bot.db_manager.find_one('submitted_apps', {'_id': interaction.message.id})
        if not app: return await interaction.response.send_message("Application data not found.", ephemeral=True)
        if app['status'] != 'pending': return await interaction.response.send_message("This application has already been processed.", ephemeral=True)

        user_id = app['user_id']
        category_name = app['category']
        guild = interaction.guild
        member = guild.get_member(user_id)
        
        config = await self.bot.db_manager.find_one('app_configs', {'_id': guild.id})
        role_id = config['categories'][category_name]['role_id']
        
        embed = interaction.message.embeds[0]
        color = discord.Color.green() if status == 'approved' else discord.Color.red()
        embed.color = color
        embed.title = f"Application {status.capitalize()}: {category_name.title()}"
        
        reason_modal = AppReasonModal(self.bot, member, status, role_id, interaction.message, embed)
        await interaction.response.send_modal(reason_modal)

class AppReasonModal(discord.ui.Modal):
    def __init__(self, bot, member, status, role_id, message, embed):
        super().__init__(title="Staff Feedback")
        self.bot = bot
        self.member = member
        self.status = status
        self.role_id = role_id
        self.message = message
        self.embed = embed
        
        self.reason = discord.ui.TextInput(label="Reason/Feedback", style=discord.TextStyle.paragraph, required=False, default="No reason provided.")
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        reason_val = self.reason.value
        self.embed.add_field(name="Staff Decision", value=f"**Status:** {self.status.capitalize()}\n**Reason:** {reason_val}\n**By:** {interaction.user.mention}")
        
        await self.message.edit(embed=self.embed, view=None)
        await self.bot.db_manager.update_one('submitted_apps', {'_id': self.message.id}, {'status': self.status}, upsert=True)

        if self.status == 'approved' and self.member:
            role = interaction.guild.get_role(self.role_id)
            if role:
                try: await self.member.add_roles(role, reason=f"Application Approved by {interaction.user}")
                except: pass

        if self.member:
            try:
                msg = f"Your application for **{interaction.guild.name}** has been **{self.status}**."
                msg += f"\n\n**Reason:** {reason_val}"
                await self.member.send(embed=self.bot.embed_manager.generic(description=msg, title="Application Update", color=self.embed.color))
            except: pass

        await interaction.response.send_message(f"Application processed as **{self.status}**.", ephemeral=True)

class Applications(commands.Cog):
    category = 'config'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager

    @commands.group(name='apply', invoke_without_command=True, help='Submit an application for a server role.')
    async def apply_group(self, ctx):
        config = await self.db.find_one('app_configs', {'_id': ctx.guild.id})
        if not config or not config.get('categories'):
            return await ctx.error("There are no active application categories.")

        view = ApplySelectView(self.bot, config['categories'])
        if not view.children:
            return await ctx.error("All application categories are currently disabled.")
            
        await ctx.info("Select a category below to start your application.", title="Submit Application", view=view)

    @apply_group.command(name='setup', help='Set the channel where applications are sent for review.')
    @commands.has_permissions(manage_guild=True)
    async def apply_setup(self, ctx, channel: discord.TextChannel):
        await self.db.update_one('app_configs', {'_id': ctx.guild.id}, {'log_channel': channel.id}, upsert=True)
        await ctx.success(f"Applications will now be sent to {channel.mention} for review.")

    @apply_group.command(name='create', help='Create a new application category.')
    @commands.has_permissions(manage_guild=True)
    async def apply_create(self, ctx, name: str, role: discord.Role):
        config = await self.db.find_one('app_configs', {'_id': ctx.guild.id}) or {'categories': {}}
        if name.lower() in config.get('categories', {}):
            return await ctx.error(f"Category `{name}` already exists.")
            
        if 'categories' not in config: config['categories'] = {}
        config['categories'][name.lower()] = {
            'role_id': role.id,
            'questions': ["Why do you want this role?"],
            'required_roles': [],
            'enabled': True
        }
        await self.db.update_one('app_configs', {'_id': ctx.guild.id}, {'categories': config['categories']}, upsert=True)
        await ctx.success(f"Category `{name}` created for role {role.mention}. Use `!apply addquestion` to customize it.")

    @apply_group.command(name='addquestion', aliases=['aq'], help='Add a question to an application category (max 5).')
    @commands.has_permissions(manage_guild=True)
    async def apply_add_q(self, ctx, category: str, *, question: str):
        config = await self.db.find_one('app_configs', {'_id': ctx.guild.id})
        if not config or category.lower() not in config.get('categories', {}):
            return await ctx.error(f"Category `{category}` not found.")
            
        cat = config['categories'][category.lower()]
        if len(cat['questions']) >= 5:
            return await ctx.error("You can only have a maximum of 5 questions per application.")
            
        cat['questions'].append(question)
        await self.db.update_one('app_configs', {'_id': ctx.guild.id}, {'categories': config['categories']}, upsert=True)
        await ctx.success(f"Question added to `{category}`.")

    @apply_group.command(name='delete', help='Delete an application category.')
    @commands.has_permissions(manage_guild=True)
    async def apply_delete(self, ctx, name: str):
        config = await self.db.find_one('app_configs', {'_id': ctx.guild.id})
        if not config or name.lower() not in config.get('categories', {}):
            return await ctx.error(f"Category `{name}` not found.")
            
        del config['categories'][name.lower()]
        await self.db.update_one('app_configs', {'_id': ctx.guild.id}, {'categories': config['categories']}, upsert=True)
        await ctx.success(f"Category `{name}` has been deleted.")

    @apply_group.command(name='list', help='List all application categories.')
    @commands.has_permissions(manage_guild=True)
    async def apply_list(self, ctx):
        config = await self.db.find_one('app_configs', {'_id': ctx.guild.id})
        if not config or not config.get('categories'):
            return await ctx.info("No application categories found.")
            
        desc = ""
        for name, data in config['categories'].items():
            role = ctx.guild.get_role(data['role_id'])
            status = "✅ Enabled" if data.get('enabled', True) else "❌ Disabled"
            desc += f"• **{name.title()}**: {role.mention if role else 'Unknown Role'} ({status})\n"
            desc += f"  > Questions: `{len(data['questions'])}` | Requirements: `{len(data.get('required_roles', []))}`\n\n"
            
        await ctx.embed(desc, title="Application Categories")

async def setup(bot):
    await bot.add_cog(Applications(bot))
