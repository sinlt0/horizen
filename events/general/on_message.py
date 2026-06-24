import discord
from discord.ext import commands
import logging

class MentionMenuView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=60)
        self.bot = bot
        self.add_item(discord.ui.Button(label="Invite Me", url=bot.config.INVITE_LINK, style=discord.ButtonStyle.link))
        self.add_item(discord.ui.Button(label="Support Server", url=bot.config.SUPPORT_SERVER, style=discord.ButtonStyle.link))
        self.add_item(discord.ui.Button(label="Website", url=bot.config.WEBSITE, style=discord.ButtonStyle.link))

class GeneralEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        
        # Check if message is JUST a mention of the bot
        mention = f"<@{self.bot.user.id}>"
        mention_nick = f"<@!{self.bot.user.id}>"
        
        if message.content.strip() in [mention, mention_nick]:
            prefix = await self.bot.prefix_manager.get_prefix(message.guild.id)
            
            embed = self.bot.embed_manager.generic(
                description=(
                    f"Hello {message.author.mention}! I am **{self.bot.user.name}**.\n\n"
                    f"My prefix for this server is `{prefix}`\n"
                    f"Type `{prefix}help` to see all my commands.\n\n"
                    "I am a high-performance, sharded Discord bot designed for professional server management and engagement."
                ),
                title="Horizen Systems"
            )
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

            await message.channel.send(embed=embed, view=MentionMenuView(self.bot))
            return

        # If content is empty but message is not a bot, it's likely missing Message Content Intent
        if not message.content and not message.attachments:
            print(f"WARNING: Received message from {message.author} with NO content. Check 'Message Content Intent' in Discord Developer Portal.")

async def setup(bot):
    await bot.add_cog(GeneralEvents(bot))
