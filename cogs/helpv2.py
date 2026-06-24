import discord
from discord.ext import commands
import math
from utils.v2_builder import V2MessageBuilder, V2Container, V2Section, V2Text, V2Separator, send_v2, callback_v2

class HelpV2(commands.Cog):
    category = 'info'

    def __init__(self, bot):
        self.bot = bot
        self.per_page = 8

    def _get_categories(self):
        categories = set()
        hidden_cats = [cat.strip().lower() for cat in self.bot.config.HIDDEN_CATEGORIES]
        for command in self.bot.commands:
            if command.hidden: continue
            cat = getattr(command.cog, 'category', 'general').lower()
            if cat not in hidden_cats:
                categories.add(cat)
        return sorted(list(categories))

    def _get_category_commands(self, category_name):
        cmds = []
        for command in self.bot.commands:
            if command.hidden: continue
            cog_cat = getattr(command.cog, 'category', 'general').lower()
            if cog_cat == category_name:
                cmds.append(command)
        return sorted(cmds, key=lambda x: x.name)

    def _get_select_menu(self, categories, placeholder="Select a protocol sector..."):
        options = []
        for cat in categories:
            options.append({
                "label": cat.capitalize(),
                "value": cat,
                "description": f"View {cat.capitalize()} command protocols."
            })
        return {
            "type": 3,
            "custom_id": "v2h:select",
            "options": options,
            "placeholder": placeholder
        }

    def _build_home_payload(self):
        builder = V2MessageBuilder()
        container = V2Container(accent_color=self.bot.config.EMBED_COLOR)
        
        header = V2Section().set_thumbnail(self.bot.user.display_avatar.url)
        header.add_text(f"## Horizen Intelligence V2\nExperience the next generation of modular server management.")
        container.add_item(header)
        
        container.add_item(V2Separator())
        
        container.add_item(V2Text(
            "-# **Information Overview**\n"
            "Use the dropdown menu below to select a specific protocol sector and deploy modular controls. Each sector contains specialized logic for server optimization."
        ))
        
        container.add_item(V2Separator())

        links = V2Section().add_text("**System Access**\nConnect to support or invite the node.")
        links.set_button("Support Server", "v2h:link:support", style=2)
        container.add_item(links)

        builder.add_container(container)
        
        categories = self._get_categories()
        builder.add_action_row([self._get_select_menu(categories)])
        
        return builder

    def _build_category_payload(self, cat_name, page=0):
        builder = V2MessageBuilder()
        container = V2Container(accent_color=self.bot.config.EMBED_COLOR)
        
        commands_list = self._get_category_commands(cat_name)
        max_pages = math.ceil(len(commands_list) / self.per_page)
        start = page * self.per_page
        end = start + self.per_page
        chunk = commands_list[start:end]

        header = V2Section().add_text(f"### {cat_name.capitalize()} Protocols\nShowing page {page+1} of {max(1, max_pages)}.")
        header.set_button("Home Hub", "v2h:home", style=2)
        container.add_item(header)
        
        container.add_item(V2Separator())

        for cmd in chunk:
            desc = (cmd.help or "No description.").split('\n')[0]
            container.add_item(V2Text(f"**`{cmd.name}`**\n{desc}"))

        container.add_item(V2Separator())

        if max_pages > 1:
            nav = V2Section().add_text("-# **Protocol Navigation**\nCycle through command pages.")
            if page < max_pages - 1:
                nav.set_button("Next Page", f"v2h:cat:{cat_name}:{page+1}", style=1)
            elif page > 0:
                nav.set_button("Prev Page", f"v2h:cat:{cat_name}:{page-1}", style=1)
            container.add_item(nav)

        builder.add_container(container)
        
        categories = self._get_categories()
        builder.add_action_row([self._get_select_menu(categories, placeholder=f"Current: {cat_name.capitalize()}")])
        
        return builder

    @commands.command(name="help2", help="Access the high-end modular V2 help interface with dropdown navigation.")
    async def help2_cmd(self, ctx):
        builder = self._build_home_payload()
        try:
            await send_v2(ctx, builder)
        except Exception as e:
            await ctx.error(f"V2 Rendering Error: {e}")

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.data or 'custom_id' not in interaction.data: return
        custom_id = interaction.data['custom_id']
        
        if not custom_id.startswith("v2h:"): return
        
        builder = None
        # Defer immediately to prevent "Interaction Failed" for V2 payloads
        try:
            if custom_id == "v2h:select":
                cat_name = interaction.data['values'][0]
                builder = self._build_category_payload(cat_name, 0)
            elif custom_id == "v2h:home":
                builder = self._build_home_payload()
            elif custom_id.startswith("v2h:cat:"):
                parts = custom_id.split(":")
                cat_name = parts[2]
                page = int(parts[3])
                builder = self._build_category_payload(cat_name, page)
            elif custom_id == "v2h:link:support":
                return await interaction.response.send_message("Join our support server: https://discord.gg/KdnAKcHupW", ephemeral=True)

            if builder:
                await callback_v2(interaction, builder)
        except Exception as e:
            print(f"[V2 DEBUG] Interaction Error: {e}")

async def setup(bot):
    await bot.add_cog(HelpV2(bot))
