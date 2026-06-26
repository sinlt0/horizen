import discord
from discord.ext import commands
import asyncio

class Starboard(commands.Cog):
    category = 'utility'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager

    async def get_config(self, guild_id):
        config = await self.bot.get_config('starboard_config', guild_id)
        if not config:
            config = {'channel_id': None, 'limit': 3, 'emoji': '⭐', 'enabled': False}
        return config

    async def update_config(self, guild_id, data):
        await self.bot.update_config('starboard_config', guild_id, data)

    def _create_star_embed(self, message, count, emoji):
        embed = self.bot.embed_manager.generic(
            description=message.content,
            title=f"{emoji} {count} | #{message.channel.name}"
        )
        embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
        embed.add_field(name="Source", value=f"[Jump to Message]({message.jump_url})")
        
        if message.attachments:
            embed.set_image(url=message.attachments[0].url)
        elif message.embeds:
            if message.embeds[0].image:
                embed.set_image(url=message.embeds[0].image.url)
            elif message.embeds[0].thumbnail:
                embed.set_image(url=message.embeds[0].thumbnail.url)
                
        embed.set_footer(text=f"ID: {message.id}")
        embed.timestamp = message.created_at
        return embed

    @commands.group(name='starboard', invoke_without_command=True, help='Configure the server starboard system.')
    @commands.has_permissions(manage_guild=True)
    async def starboard_group(self, ctx):
        config = await self.get_config(ctx.guild.id)
        channel = ctx.guild.get_channel(config['channel_id'])
        
        desc = (
            f"**Status:** {'Enabled ✅' if config['enabled'] else 'Disabled ❌'}\n"
            f"**Channel:** {channel.mention if channel else 'Not Set'}\n"
            f"**Threshold:** `{config['limit']}` {config['emoji']}\n"
            f"**Emoji:** {config['emoji']}"
        )
        await ctx.embed(desc, title="Starboard Configuration")

    @starboard_group.command(name='channel', help='Set the starboard channel.')
    @commands.has_permissions(manage_guild=True)
    async def starboard_channel(self, ctx, channel: discord.TextChannel):
        await self.db.update_one('starboard_config', {'_id': ctx.guild.id}, {'channel_id': channel.id, 'enabled': True}, upsert=True)
        await ctx.success(f"Starboard channel has been set to {channel.mention}.")

    @starboard_group.command(name='limit', help='Set the minimum reactions required.')
    @commands.has_permissions(manage_guild=True)
    async def starboard_limit(self, ctx, limit: int):
        if limit < 1: return await ctx.error("Limit must be at least 1.")
        await self.db.update_one('starboard_config', {'_id': ctx.guild.id}, {'limit': limit}, upsert=True)
        await ctx.success(f"Starboard threshold set to `{limit}`.")

    @starboard_group.command(name='emoji', help='Set a custom emoji for the starboard.')
    @commands.has_permissions(manage_guild=True)
    async def starboard_emoji(self, ctx, emoji: str):
        await self.db.update_one('starboard_config', {'_id': ctx.guild.id}, {'emoji': emoji}, upsert=True)
        await ctx.success(f"Starboard emoji set to {emoji}.")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if not payload.guild_id: return
        config = await self.get_config(payload.guild_id)
        if not config['enabled'] or not config['channel_id']: return
        
        if str(payload.emoji) != config['emoji']: return
        
        guild = self.bot.get_guild(payload.guild_id)
        channel = guild.get_channel(payload.channel_id)
        try:
            message = await channel.fetch_message(payload.message_id)
        except: return

        if message.author.bot: return
        if message.channel.id == config['channel_id']: return

        # Count reactions
        reaction = discord.utils.get(message.reactions, emoji=payload.emoji.name if payload.emoji.is_unicode_emoji() else payload.emoji)
        count = reaction.count if reaction else 0
        
        star_msg = await self.db.find_one('starboard_messages', {'_id': message.id})
        star_channel = guild.get_channel(config['channel_id'])
        if not star_channel: return

        if count >= config['limit']:
            embed = self._create_star_embed(message, count, config['emoji'])
            
            if star_msg:
                try:
                    m = await star_channel.fetch_message(star_msg['starboard_message_id'])
                    await m.edit(embed=embed)
                    await self.db.update_one('starboard_messages', {'_id': message.id}, {'count': count}, upsert=True)
                except:
                    # If message was deleted, treat as new
                    msg = await star_channel.send(embed=embed)
                    await self.db.update_one('starboard_messages', {'_id': message.id}, {'starboard_message_id': msg.id, 'count': count}, upsert=True)
            else:
                msg = await star_channel.send(embed=embed)
                await self.db.update_one('starboard_messages', {'_id': message.id}, {'starboard_message_id': msg.id, 'count': count, 'guild_id': guild.id}, upsert=True)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if not payload.guild_id: return
        config = await self.get_config(payload.guild_id)
        if not config['enabled'] or not config['channel_id']: return
        
        if str(payload.emoji) != config['emoji']: return
        
        star_msg = await self.db.find_one('starboard_messages', {'_id': payload.message_id})
        if not star_msg: return

        guild = self.bot.get_guild(payload.guild_id)
        channel = guild.get_channel(payload.channel_id)
        try:
            message = await channel.fetch_message(payload.message_id)
            reaction = discord.utils.get(message.reactions, emoji=payload.emoji.name if payload.emoji.is_unicode_emoji() else payload.emoji)
            count = reaction.count if reaction else 0
        except:
            count = star_msg['count'] - 1 # Fallback if message fetch fails

        star_channel = guild.get_channel(config['channel_id'])
        if not star_channel: return

        try:
            m = await star_channel.fetch_message(star_msg['starboard_message_id'])
            if count < config['limit']:
                await m.delete()
                await self.db.delete_one('starboard_messages', {'_id': payload.message_id})
            else:
                embed = self._create_star_embed(message, count, config['emoji'])
                await m.edit(embed=embed)
                await self.db.update_one('starboard_messages', {'_id': payload.message_id}, {'count': count}, upsert=True)
        except: pass

async def setup(bot):
    await bot.add_cog(Starboard(bot))
