import discord
from discord.ext import commands
import asyncio

class SuggestionVoteView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    async def _update_votes(self, interaction, vote_type):
        msg_id = interaction.message.id
        user_id = interaction.user.id
        
        # Fetch suggestion data
        sug = await self.bot.db_manager.find_one('suggestions', {'_id': msg_id})
        if not sug:
            return await interaction.response.send_message("Suggestion data not found.", ephemeral=True)
        
        if sug['status'] != 'pending':
            return await interaction.response.send_message("This suggestion has already been reviewed.", ephemeral=True)

        upvotes = set(sug.get('upvotes', []))
        downvotes = set(sug.get('downvotes', []))

        if vote_type == 'up':
            if user_id in upvotes: upvotes.remove(user_id)
            else:
                upvotes.add(user_id)
                if user_id in downvotes: downvotes.remove(user_id)
        else:
            if user_id in downvotes: downvotes.remove(user_id)
            else:
                downvotes.add(user_id)
                if user_id in upvotes: upvotes.remove(user_id)

        await self.bot.db_manager.update_one('suggestions', {'_id': msg_id}, {
            'upvotes': list(upvotes),
            'downvotes': list(downvotes)
        }, upsert=True)

        # Update embed
        embed = interaction.message.embeds[0]
        # Find the line with votes and update it
        lines = embed.description.split('\n')
        new_desc = []
        for line in lines:
            if 'Votes:' in line or '⬆️' in line: continue # Remove old vote line
            new_desc.append(line)
        
        desc_str = '\n'.join(new_desc).strip()
        desc_str += f"\n\n**Votes:**\n{self.bot.e.upvote} `{len(upvotes)}` | {self.bot.e.downvote} `{len(downvotes)}`"
        embed.description = desc_str
        
        await interaction.message.edit(embed=embed)
        await interaction.response.defer()

    @discord.ui.button(label="Upvote", style=discord.ButtonStyle.success, custom_id="suggestion_upvote")
    async def upvote(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._update_votes(interaction, 'up')

    @discord.ui.button(label="Downvote", style=discord.ButtonStyle.danger, custom_id="suggestion_downvote")
    async def downvote(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._update_votes(interaction, 'down')

class Suggestions(commands.Cog):
    category = 'utility'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager

    async def get_config(self, guild_id):
        return await self.bot.get_config('suggestions_config', guild_id)

    async def update_config(self, guild_id, data):
        await self.bot.update_config('suggestions_config', guild_id, data)

    @commands.group(name='suggest', invoke_without_command=True, help='Submit a suggestion for the server.')
    async def suggest_group(self, ctx, *, text: str):
        config = await self.get_config(ctx.guild.id)
        if not config or not config.get('channel_id'):
            return await ctx.error("Suggestion system is not set up! Use `!suggest channel <#channel>`.")

        channel = ctx.guild.get_channel(config['channel_id'])
        if not channel: return await ctx.error("Suggestion channel not found.")

        embed = self.bot.embed_manager.generic(
            description=f"{text}\n\n**Votes:**\n{self.bot.e.upvote} `0` | {self.bot.e.downvote} `0`",
            title=f"{self.bot.e.suggestion} New Suggestion"
        )
        
        if config.get('anonymous'):
            embed.set_author(name="Anonymous User")
        else:
            embed.set_author(name=f"Suggested by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
            embed.set_footer(text=f"User ID: {ctx.author.id}")

        msg = await channel.send(embed=embed, view=SuggestionVoteView(self.bot))
        
        thread_id = None
        if config.get('auto_thread', True):
            try:
                thread = await msg.create_thread(name=f"Discussion: {text[:50]}...")
                thread_id = thread.id
            except: pass

        sug_data = {
            '_id': msg.id,
            'guild_id': ctx.guild.id,
            'author_id': ctx.author.id,
            'content': text,
            'status': 'pending',
            'upvotes': [],
            'downvotes': [],
            'thread_id': thread_id
        }
        await self.db.update_one('suggestions', {'_id': msg.id}, sug_data, upsert=True)
        
        log_cog = self.bot.get_cog('Logging')
        if log_cog:
            log_embed = discord.Embed(title="New Suggestion Submitted", description=f"**Author:** {ctx.author.mention} ({ctx.author.id})\n**Content:** {text}\n**Jump:** [Message]({msg.jump_url})", color=discord.Color.blue(), timestamp=discord.utils.utcnow())
            await log_cog.log_suggestions(ctx.guild, log_embed)

        await ctx.success(f"Your suggestion has been submitted to {channel.mention}!")

    @suggest_group.command(name='channel', help='Set the channel for suggestions.')
    @commands.has_permissions(manage_guild=True)
    async def suggest_channel(self, ctx, channel: discord.TextChannel):
        await self.update_config(ctx.guild.id, {'channel_id': channel.id})
        await ctx.success(f"Suggestions will now be sent to {channel.mention}.")

    @suggest_group.command(name='anonymous', aliases=['anon'], help='Toggle anonymous suggestions.')
    @commands.has_permissions(manage_guild=True)
    async def suggest_anon(self, ctx, status: bool):
        await self.update_config(ctx.guild.id, {'anonymous': status})
        await ctx.success(f"Anonymous suggestions are now **{'enabled' if status else 'disabled'}**.")

    @suggest_group.command(name='approve', help='Approve a suggestion.')
    @commands.has_permissions(manage_messages=True)
    async def suggest_approve(self, ctx, message_id: int, *, reason: str = "No reason provided."):
        await self._update_status(ctx, message_id, 'approved', discord.Color.green(), reason)

    @suggest_group.command(name='deny', help='Deny a suggestion.')
    @commands.has_permissions(manage_messages=True)
    async def suggest_deny(self, ctx, message_id: int, *, reason: str = "No reason provided."):
        await self._update_status(ctx, message_id, 'denied', discord.Color.red(), reason)

    @suggest_group.command(name='consider', help='Mark a suggestion as considered.')
    @commands.has_permissions(manage_messages=True)
    async def suggest_consider(self, ctx, message_id: int, *, reason: str = "No reason provided."):
        await self._update_status(ctx, message_id, 'considered', discord.Color.gold(), reason)

    @suggest_group.command(name='implement', help='Mark a suggestion as implemented.')
    @commands.has_permissions(manage_messages=True)
    async def suggest_implement(self, ctx, message_id: int, *, reason: str = "No reason provided."):
        await self._update_status(ctx, message_id, 'implemented', discord.Color.blue(), reason)

    async def _update_status(self, ctx, message_id, status, color, reason):
        sug = await self.db.find_one('suggestions', {'_id': message_id})
        if not sug: return await ctx.error("Suggestion not found.")
        
        config = await self.db.find_one('suggestions_config', {'_id': ctx.guild.id})
        channel = ctx.guild.get_channel(config['channel_id'])
        if not channel: return await ctx.error("Suggestion channel not found.")

        try:
            msg = await channel.fetch_message(message_id)
        except: return await ctx.error("Could not find the suggestion message.")

        embed = msg.embeds[0]
        embed.color = color
        embed.title = f"{getattr(self.bot.e, status, '')} Suggestion {status.capitalize()}"
        
        # Check if field already exists, if so update, else add
        field_found = False
        for i, field in enumerate(embed.fields):
            if field.name == "Staff Response":
                embed.set_field_at(i, name="Staff Response", value=f"**Status:** {status.capitalize()}\n**Reason:** {reason}\n**By:** {ctx.author.mention}", inline=False)
                field_found = True
                break
        
        if not field_found:
            embed.add_field(name="Staff Response", value=f"**Status:** {status.capitalize()}\n**Reason:** {reason}\n**By:** {ctx.author.mention}", inline=False)

        await msg.edit(embed=embed, view=None) # Remove buttons after review
        await self.db.update_one('suggestions', {'_id': message_id}, {'status': status}, upsert=True)
        
        # Notify author
        try:
            author = await self.bot.fetch_user(sug['author_id'])
            await author.send(embed=self.bot.embed_manager.generic(
                description=f"Your suggestion in **{ctx.guild.name}** has been **{status}**.\n\n**Content:** {sug['content']}\n**Reason:** {reason}",
                title="Suggestion Update",
                color=color
            ))
        except: pass

        await ctx.success(f"Suggestion `{message_id}` marked as **{status}**.")

async def setup(bot):
    await bot.add_cog(Suggestions(bot))
