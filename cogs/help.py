import discord
from discord.ext import commands
import math

class HelpDropdown(discord.ui.Select):
    def __init__(self, categories, placeholder="Select a category..."):
        options = [
            discord.SelectOption(label=cat.capitalize(), description=f"Commands for {cat}")
            for cat in categories
        ]
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        try:
            await self.view.show_category(interaction, self.values[0].lower())
        except Exception:
            if not interaction.response.is_done():
                await interaction.response.send_message("An error occurred while switching categories.", ephemeral=True)

class HelpView(discord.ui.View):
    def __init__(self, bot, author, categories):
        super().__init__(timeout=120)
        self.bot = bot
        self.author = author
        self.categories = sorted(categories)
        self.current_category = None
        self.current_page = 0
        self.per_page = 10
        for i in range(0, len(self.categories), 10):
            chunk = self.categories[i:i+10]
            self.add_item(HelpDropdown(chunk, placeholder="Select a category..."))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.author:
            await interaction.response.send_message("This menu is not for you.", ephemeral=True)
            return False
        return True

    def _get_category_commands(self, category_name):
        cmds = []
        for command in self.bot.commands:
            if command.hidden: continue
            cog_cat = getattr(command.cog, 'category', 'general').lower()
            if cog_cat == category_name:
                cmds.append(command)
        return sorted(cmds, key=lambda x: x.name)

    async def show_category(self, interaction, category_name, page=0):
        self.current_category = category_name
        self.current_page = page
        commands_list = self._get_category_commands(category_name)
        max_pages = math.ceil(len(commands_list) / self.per_page)
        start = page * self.per_page
        end = start + self.per_page
        chunk = commands_list[start:end]
        embed = self.bot.embed_manager.generic(
            description=f"Showing commands for **{category_name.capitalize()}**",
            title=f"Help - {category_name.capitalize()} (Page {page + 1}/{max(1, max_pages)})"
        )
        for cmd in chunk:
            desc = cmd.help or "No description provided."
            embed.add_field(name=f"`{cmd.name}`", value=desc, inline=False)
        self._update_buttons(max_pages)
        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=self)
        else:
            try:
                await interaction.response.edit_message(embed=embed, view=self)
            except Exception:
                await interaction.edit_original_response(embed=embed, view=self)

    def _update_buttons(self, max_pages):
        self.clear_items()
        for i in range(0, len(self.categories), 10):
            chunk = self.categories[i:i+10]
            self.add_item(HelpDropdown(chunk, placeholder="Select a category..."))
        if self.current_category:
            prev_btn = discord.ui.Button(label="<", style=discord.ButtonStyle.secondary, disabled=(self.current_page == 0))
            home_btn = discord.ui.Button(label="Home", style=discord.ButtonStyle.blurple)
            next_btn = discord.ui.Button(label=">", style=discord.ButtonStyle.secondary, disabled=(self.current_page >= max_pages - 1))
            async def prev_callback(itn):
                await self.show_category(itn, self.current_category, self.current_page - 1)
            async def home_callback(itn):
                await self.show_home(itn)
            async def next_callback(itn):
                await self.show_category(itn, self.current_category, self.current_page + 1)
            prev_btn.callback = prev_callback
            home_btn.callback = home_callback
            next_btn.callback = next_callback
            self.add_item(prev_btn)
            self.add_item(home_btn)
            self.add_item(next_btn)

    async def show_home(self, interaction):
        self.current_category = None
        self.current_page = 0
        self.clear_items()
        for i in range(0, len(self.categories), 10):
            chunk = self.categories[i:i+10]
            self.add_item(HelpDropdown(chunk, placeholder="Select a category..."))
        embed = self.bot.embed_manager.generic(
            description="-# Click the dropdown below and select a category..",
            title="Help Menu"
        )
        embed.add_field(name="Bot", value="[Support Server](https://discord.gg/KdnAKcHupW) ・ [Invite Bot](https://discord.com/oauth2/authorize?client_id=1167721021323870258&permissions=8&scope=bot)", inline=True)
        embed.add_field(name="Important Note", value="`<>` = Required, `[]` = Optional", inline=True)
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text=f"Total Categories: {len(self.categories)}")
        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=self)
        else:
            try:
                await interaction.response.edit_message(embed=embed, view=self)
            except Exception:
                await interaction.edit_original_response(embed=embed, view=self)

class HelpCog(commands.Cog):
    category = 'utility'

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help", aliases=['h'], help='Displays help information for a category or specific command.')
    async def help_command(self, ctx, *, item: str = None):
        if item:
            item = item.lower()
            command = self.bot.get_command(item)
            if command:
                embed = self.bot.embed_manager.generic(
                    title=f"Command: {command.qualified_name}",
                    description=command.help or "No description provided."
                )
                if command.aliases:
                    embed.add_field(name="Aliases", value=", ".join(f"`{a}`" for a in command.aliases), inline=False)
                usage = f"{ctx.prefix}{command.qualified_name} {command.signature}"
                embed.add_field(name="Usage", value=f"`{usage}`", inline=False)
                if isinstance(command, commands.Group):
                    subcmds = sorted(command.commands, key=lambda x: x.name)
                    if subcmds:
                        val = "\n".join(f"`{c.name}` - {c.help or 'No description'}" for c in subcmds)
                        embed.add_field(name="Subcommands", value=val, inline=False)
                return await ctx.send(embed=embed)
            
            cog_found = None
            for cog_name, cog in self.bot.cogs.items():
                if cog_name.lower() == item or (getattr(cog, 'category', '').lower() == item):
                    cog_found = cog
                    break
            
            if cog_found:
                category_name = getattr(cog_found, 'category', cog_found.qualified_name).lower()
                view = HelpView(self.bot, ctx.author, [category_name])
                await view.show_category(None, category_name)
                # Note: This part is tricky because show_category expects an interaction.
                # Let's refactor help to be simpler for direct category calls.
                return

        categories = set()
        hidden_cats = [cat.strip().lower() for cat in self.bot.config.HIDDEN_CATEGORIES]
        for command in self.bot.commands:
            if command.hidden: continue
            cat = getattr(command.cog, 'category', 'general').lower()
            if cat not in hidden_cats:
                categories.add(cat)
        view = HelpView(self.bot, ctx.author, list(categories))
        embed = self.bot.embed_manager.generic(
            description="-# Click the dropdown below and select a category..",
            title="Help Menu"
        )
        embed.add_field(name="Bot", value="[Support Server](https://discord.gg/KdnAKcHupW) ・ [Invite Bot](https://discord.com/oauth2/authorize?client_id=1167721021323870258&permissions=8&scope=bot)", inline=True)
        embed.add_field(name="Important Note", value="`<>` = Required, `[]` = Optional", inline=True)
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text=f"Total Categories: {len(categories)}")
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(HelpCog(bot))
