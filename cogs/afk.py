import discord
from discord.ext import commands
import time
import datetime

class AFK(commands.Cog):
    category = 'utility'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager

    async def get_afk_config(self, guild_id):
        config = await self.db.find_one('afk_config', {'_id': guild_id, 'guild_id': guild_id})
        return config or {'nick_change': True}

    @commands.group(name='afk', invoke_without_command=True, help='Set an AFK status to notify others when you are mentioned.')
    async def afk_group(self, ctx, *, reason: str = 'AFK'):
        if len(reason) > 100:
            return await ctx.error('AFK reason cannot exceed 100 characters.')
        
        pref = await self.db.find_one('afk_prefs', {'_id': ctx.author.id})
        is_global = pref.get('global', False) if pref else False
        
        db_id = f"global-{ctx.author.id}" if is_global else f"{ctx.guild.id}-{ctx.author.id}"
        guild_id = 0 if is_global else ctx.guild.id
        
        data = {
            '_id': db_id,
            'user_id': ctx.author.id,
            'guild_id': guild_id,
            'reason': reason,
            'time': time.time(),
            'is_global': is_global
        }
        
        await self.db.update_one('afk_users', {'_id': db_id, 'guild_id': guild_id}, data, upsert=True)
        
        config = await self.get_afk_config(ctx.guild.id)
        if config.get('nick_change'):
            try:
                await ctx.author.edit(nick=f'[AFK] {ctx.author.display_name[:25]}')
            except:
                pass
            
        type_emoji = getattr(self.bot.e, 'afk_global' if is_global else 'afk_server', '💤')
        await ctx.success(f'{type_emoji} You are now AFK **{"Global" if is_global else "Server"}** with the reason: **{reason}**')

    @afk_group.command(name='global', help='Toggle whether your AFK status is global or server-specific.')
    async def afk_global(self, ctx, status: bool):
        await self.db.update_one('afk_prefs', {'_id': ctx.author.id}, {'global': status}, upsert=True)
        emoji = getattr(self.bot.e, 'afk_global' if status else 'afk_server', '🌐')
        await ctx.success(f'{emoji} Your AFK status preference has been set to: **{"Global" if status else "Server-Specific"}**')

    @afk_group.command(name='settings', help='Configure AFK settings for the server (Admin Only).')
    @commands.has_permissions(administrator=True)
    async def afk_settings(self, ctx, option: str, value: bool):
        option = option.lower()
        if option not in ['nick', 'nickname']:
            return await ctx.error("Invalid option. Use `nick`.")
            
        await self.db.update_one('afk_config', {'_id': ctx.guild.id, 'guild_id': ctx.guild.id}, {'nick_change': value}, upsert=True)
        emoji = getattr(self.bot.e, 'afk_settings', '⚙️')
        await ctx.success(f"{emoji} AFK nickname changes are now **{'enabled' if value else 'disabled'}**.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        afk_data = await self.db.find_one('afk_users', {'_id': f"global-{message.author.id}", 'guild_id': 0})
        if not afk_data:
            afk_data = await self.db.find_one('afk_users', {'_id': f"{message.guild.id}-{message.author.id}", 'guild_id': message.guild.id})
            
        if afk_data:
            await self.db.delete_one('afk_users', {'_id': afk_data['_id'], 'guild_id': afk_data['guild_id']})
            try:
                if message.author.display_name.startswith('[AFK] '):
                    await message.author.edit(nick=message.author.display_name.replace('[AFK] ', ''))
            except:
                pass
            
            elapsed = time.time() - afk_data['time']
            duration = str(datetime.timedelta(seconds=int(elapsed)))
            return_emoji = getattr(self.bot.e, 'afk_return', '👋')
            await message.info(f'{return_emoji} Welcome back {message.author.mention}, you were AFK for **{duration}**.')

        for mention in message.mentions:
            if mention == message.author:
                continue
            
            target_afk = await self.db.find_one('afk_users', {'_id': f"global-{mention.id}", 'guild_id': 0})
            if not target_afk:
                target_afk = await self.db.find_one('afk_users', {'_id': f"{message.guild.id}-{mention.id}", 'guild_id': message.guild.id})
                
            if target_afk:
                elapsed = time.time() - target_afk['time']
                duration = str(datetime.timedelta(seconds=int(elapsed)))
                reason = target_afk['reason']
                afk_emoji = getattr(self.bot.e, 'afk', '💤')
                await message.embed(
                    f'{mention.mention} is currently AFK: **{reason}** ({duration} ago)',
                    title='User is AFK',
                    emoji=afk_emoji
                )

async def setup(bot):
    await bot.add_cog(AFK(bot))
