import discord
from discord.ext import commands

class EmbedManager:

    def __init__(self, bot):
        self.bot = bot
        self.default_color = bot.config.EMBED_COLOR
        self.colors = {'success': discord.Color.green(), 'failure': discord.Color.red(), 'error': discord.Color.dark_red(), 'warning': discord.Color.orange(), 'info': self.default_color}

    def _create_embed(self, title, description, color=None, emoji=None):
        if color is None:
            color = self.default_color
        full_description = f'{emoji} {description}' if emoji else description
        embed = discord.Embed(title=title, description=full_description, color=color)
        return embed

    def generic(self, description, title=None, color=None, emoji=None):
        return self._create_embed(title, description, color, emoji)

    def success(self, description, title='Success'):
        emoji = getattr(self.bot.e, 'success', '✅')
        return self._create_embed(title, description, self.colors['success'], emoji)

    def failure(self, description, title='Failed'):
        emoji = getattr(self.bot.e, 'error', '❌')
        return self._create_embed(title, description, self.colors['failure'], emoji)

    def error(self, description, title='Error'):
        emoji = getattr(self.bot.e, 'error', '❌')
        return self._create_embed(title, description, self.colors['error'], emoji)

    def warning(self, description, title='Warning'):
        emoji = getattr(self.bot.e, 'warning', '⚠️')
        return self._create_embed(title, description, self.colors['warning'], emoji)

    def info(self, description, title='Information'):
        emoji = getattr(self.bot.e, 'info', 'ℹ️')
        return self._create_embed(title, description, self.colors['info'], emoji)

async def send_success(ctx, description, title='Success', **kwargs):
    embed = ctx.bot.embed_manager.success(description, title)
    return await ctx.send(embed=embed, **kwargs)

async def send_failure(ctx, description, title='Failed', **kwargs):
    embed = ctx.bot.embed_manager.failure(description, title)
    return await ctx.send(embed=embed, **kwargs)

async def send_error(ctx, description, title='Error', **kwargs):
    embed = ctx.bot.embed_manager.error(description, title)
    return await ctx.send(embed=embed, **kwargs)

async def send_warning(ctx, description, title='Warning', **kwargs):
    embed = ctx.bot.embed_manager.warning(description, title)
    return await ctx.send(embed=embed, **kwargs)

async def send_info(ctx, description, title='Information', **kwargs):
    embed = ctx.bot.embed_manager.info(description, title)
    return await ctx.send(embed=embed, **kwargs)

async def send_embed(ctx, description, title=None, color=None, emoji=None, **kwargs):
    embed = ctx.bot.embed_manager.generic(description, title, color, emoji)
    return await ctx.send(embed=embed, **kwargs)