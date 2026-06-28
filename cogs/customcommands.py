import discord
from discord.ext import commands
import re

class CustomCommands(commands.Cog):
    category = 'config'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager
        self._cache = {}

    async def cog_load(self):
        configs = await self.db.find('custom_commands', {})
        for c in configs:
            self._cache[c['_id']] = c.get('commands', {})

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return
        cmds = self._cache.get(message.guild.id, {})
        if not cmds:
            return
        prefixes = await self.bot.prefix_manager.get_prefixes(message.guild.id)
        used_prefix = next((p for p in prefixes if message.content.startswith(p)), None)
        if not used_prefix:
            return
        content = message.content[len(used_prefix):].strip()
        trigger = content.split()[0].lower() if content else ''
        if trigger not in cmds:
            return
        cmd = cmds[trigger]
        response = cmd.get('response', '')
        response = response.replace('{user}', message.author.mention)
        response = response.replace('{username}', message.author.display_name)
        response = response.replace('{server}', message.guild.name)
        response = response.replace('{membercount}', str(message.guild.member_count))
        if cmd.get('embed', False):
            embed = discord.Embed(description=response, color=self.bot.embed_manager.color)
            await message.channel.send(embed=embed)
        else:
            await message.channel.send(response)
        if cmd.get('delete_trigger', False):
            try:
                await message.delete()
            except Exception:
                pass

    @commands.group(name='cc', aliases=['customcmd', 'customcommand'], invoke_without_command=True, help='Custom command management.')
    @commands.has_permissions(manage_guild=True)
    async def cc_group(self, ctx):
        await ctx.send_help(ctx.command)

    @cc_group.command(name='add', help='Add a custom command. Usage: cc add <trigger> <response>')
    @commands.has_permissions(manage_guild=True)
    async def cc_add(self, ctx, trigger: str, *, response: str):
        trigger = trigger.lower()
        if len(trigger) > 30:
            return await ctx.error('Trigger must be under 30 characters.')
        if len(response) > 2000:
            return await ctx.error('Response must be under 2000 characters.')
        if self.bot.get_command(trigger):
            return await ctx.error(f'`{trigger}` is an existing bot command.')
        config = await self.db.find_one('custom_commands', {'_id': ctx.guild.id}) or {'_id': ctx.guild.id, 'commands': {}}
        if len(config.get('commands', {})) >= 50:
            return await ctx.error('Maximum 50 custom commands per server.')
        config.setdefault('commands', {})[trigger] = {'response': response, 'embed': False, 'delete_trigger': False, 'uses': 0}
        await self.db.update_one('custom_commands', {'_id': ctx.guild.id}, config, upsert=True)
        self._cache.setdefault(ctx.guild.id, {})[trigger] = config['commands'][trigger]
        await ctx.success(f'{self.bot.e.success} Custom command `{trigger}` created.')

    @cc_group.command(name='remove', aliases=['delete'], help='Remove a custom command.')
    @commands.has_permissions(manage_guild=True)
    async def cc_remove(self, ctx, trigger: str):
        trigger = trigger.lower()
        config = await self.db.find_one('custom_commands', {'_id': ctx.guild.id})
        if not config or trigger not in config.get('commands', {}):
            return await ctx.error(f'Command `{trigger}` not found.')
        del config['commands'][trigger]
        await self.db.update_one('custom_commands', {'_id': ctx.guild.id}, config, upsert=True)
        self._cache.get(ctx.guild.id, {}).pop(trigger, None)
        await ctx.success(f'{self.bot.e.success} Custom command `{trigger}` removed.')

    @cc_group.command(name='list', help='List all custom commands in this server.')
    async def cc_list(self, ctx):
        config = await self.db.find_one('custom_commands', {'_id': ctx.guild.id})
        cmds = config.get('commands', {}) if config else {}
        if not cmds:
            return await ctx.info('No custom commands configured.')
        desc = '\n'.join([f'`{trigger}` — {cmd["response"][:50]}{"..." if len(cmd["response"]) > 50 else ""}' for trigger, cmd in cmds.items()])
        embed = self.bot.embed_manager.generic(description=desc, title=f'Custom Commands ({len(cmds)}/50)')
        await ctx.send(embed=embed)

    @cc_group.command(name='edit', help='Edit the response of an existing custom command.')
    @commands.has_permissions(manage_guild=True)
    async def cc_edit(self, ctx, trigger: str, *, response: str):
        trigger = trigger.lower()
        config = await self.db.find_one('custom_commands', {'_id': ctx.guild.id})
        if not config or trigger not in config.get('commands', {}):
            return await ctx.error(f'Command `{trigger}` not found.')
        config['commands'][trigger]['response'] = response
        await self.db.update_one('custom_commands', {'_id': ctx.guild.id}, config, upsert=True)
        self._cache.setdefault(ctx.guild.id, {})[trigger] = config['commands'][trigger]
        await ctx.success(f'{self.bot.e.success} Command `{trigger}` updated.')

    @cc_group.command(name='info', help='View details about a custom command.')
    async def cc_info(self, ctx, trigger: str):
        trigger = trigger.lower()
        config = await self.db.find_one('custom_commands', {'_id': ctx.guild.id})
        cmd = config.get('commands', {}).get(trigger) if config else None
        if not cmd:
            return await ctx.error(f'Command `{trigger}` not found.')
        embed = self.bot.embed_manager.generic(
            description=(
                f'**Trigger:** `{trigger}`\n'
                f'**Response:** {cmd["response"][:200]}\n'
                f'**Embed:** `{cmd.get("embed", False)}`\n'
                f'**Delete Trigger:** `{cmd.get("delete_trigger", False)}`\n'
                f'**Uses:** `{cmd.get("uses", 0)}`'
            ),
            title=f'Custom Command: {trigger}'
        )
        await ctx.send(embed=embed)

    @cc_group.command(name='toggleembed', help='Toggle embed mode for a custom command.')
    @commands.has_permissions(manage_guild=True)
    async def cc_toggleembed(self, ctx, trigger: str):
        trigger = trigger.lower()
        config = await self.db.find_one('custom_commands', {'_id': ctx.guild.id})
        if not config or trigger not in config.get('commands', {}):
            return await ctx.error(f'Command `{trigger}` not found.')
        config['commands'][trigger]['embed'] = not config['commands'][trigger].get('embed', False)
        await self.db.update_one('custom_commands', {'_id': ctx.guild.id}, config, upsert=True)
        self._cache.setdefault(ctx.guild.id, {})[trigger] = config['commands'][trigger]
        state = 'enabled' if config['commands'][trigger]['embed'] else 'disabled'
        await ctx.success(f'{self.bot.e.success} Embed mode **{state}** for `{trigger}`.')

    @cc_group.command(name='toggledelete', help='Toggle auto-deletion of trigger message for a custom command.')
    @commands.has_permissions(manage_guild=True)
    async def cc_toggledelete(self, ctx, trigger: str):
        trigger = trigger.lower()
        config = await self.db.find_one('custom_commands', {'_id': ctx.guild.id})
        if not config or trigger not in config.get('commands', {}):
            return await ctx.error(f'Command `{trigger}` not found.')
        config['commands'][trigger]['delete_trigger'] = not config['commands'][trigger].get('delete_trigger', False)
        await self.db.update_one('custom_commands', {'_id': ctx.guild.id}, config, upsert=True)
        state = 'enabled' if config['commands'][trigger]['delete_trigger'] else 'disabled'
        await ctx.success(f'{self.bot.e.success} Delete trigger **{state}** for `{trigger}`.')

async def setup(bot):
    await bot.add_cog(CustomCommands(bot))
