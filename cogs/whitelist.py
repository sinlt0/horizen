import discord
from discord.ext import commands

class Whitelist(commands.Cog):
    category = 'config'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager

    async def get_config(self, guild_id):
        config = await self.db.find_one('automod_config', {'_id': guild_id})
        return config or {}

    @commands.group(name='whitelist', aliases=['wl'], invoke_without_command=True, help='Manage server whitelists (Global, Specific, Links, Invites, Extra Owners).')
    @commands.has_permissions(administrator=True)
    async def whitelist_group(self, ctx):
        config = await self.get_config(ctx.guild.id)
        g_roles = [ctx.guild.get_role(r).mention for r in config.get('whitelist_global_roles', []) if ctx.guild.get_role(r)]
        g_channels = [ctx.guild.get_channel(c).mention for c in config.get('whitelist_global_channels', []) if ctx.guild.get_channel(c)]
        g_users = [f"<@{u}>" for u in config.get('whitelist_global_users', [])]
        e_owners = [f"<@{u}>" for u in config.get('extra_owners', [])]
        
        desc = "**Global Exemption (Exempt from all):**\n"
        desc += f"Roles: {', '.join(g_roles) if g_roles else 'None'}\n"
        desc += f"Channels: {', '.join(g_channels) if g_channels else 'None'}\n"
        desc += f"Users: {', '.join(g_users) if g_users else 'None'}\n"
        desc += f"Extra Owners: {', '.join(e_owners) if e_owners else 'None'}\n\n"
        
        l_white = config.get('whitelist_links', [])
        i_white = config.get('whitelist_invites', [])
        desc += f"**Whitelisted Domains:** {', '.join(l_white) if l_white else 'None'}\n"
        desc += f"**Whitelisted Invites:** {', '.join(i_white) if i_white else 'None'}\n\n"
        
        spec = config.get('whitelist_specific', {})
        if spec:
            desc += "**Specific Whitelists:**\n"
            for module, data in spec.items():
                entries = []
                for r in data.get('roles', []):
                    role = ctx.guild.get_role(r)
                    if role: entries.append(role.mention)
                for c in data.get('channels', []):
                    chan = ctx.guild.get_channel(c)
                    if chan: entries.append(chan.mention)
                for u in data.get('users', []):
                    entries.append(f"<@{u}>")
                if entries:
                    desc += f"• **{module.capitalize()}**: {', '.join(entries)}\n"
                    
        await ctx.embed(desc, title="Server Whitelist Management")

    @whitelist_group.command(name='add', help='Add to a whitelist. Scopes: global, extra_owner, <module>, links, invites.')
    @commands.has_permissions(administrator=True)
    async def whitelist_add(self, ctx, scope: str, *, target: str):
        config = await self.get_config(ctx.guild.id)
        scope = scope.lower()
        
        if scope == 'links':
            links = config.get('whitelist_links', [])
            if target not in links: links.append(target)
            await self.db.update_one('automod_config', {'_id': ctx.guild.id}, {'whitelist_links': links}, upsert=True)
        elif scope == 'invites':
            invites = config.get('whitelist_invites', [])
            if target not in invites: invites.append(target)
            await self.db.update_one('automod_config', {'_id': ctx.guild.id}, {'whitelist_invites': invites}, upsert=True)
        else:
            try:
                converter = commands.RoleConverter()
                target_obj = await converter.convert(ctx, target)
            except:
                try:
                    converter = commands.TextChannelConverter()
                    target_obj = await converter.convert(ctx, target)
                except:
                    try:
                        converter = commands.MemberConverter()
                        target_obj = await converter.convert(ctx, target)
                    except: return await ctx.error("Target must be a Role, Channel, or Member.")
            
            if scope == 'global':
                if isinstance(target_obj, discord.Role): key = 'whitelist_global_roles'
                elif isinstance(target_obj, (discord.Member, discord.User)): key = 'whitelist_global_users'
                else: key = 'whitelist_global_channels'
                
                data = config.get(key, [])
                if target_obj.id not in data: data.append(target_obj.id)
                await self.db.update_one('automod_config', {'_id': ctx.guild.id}, {key: data}, upsert=True)
            elif scope == 'extra_owner':
                if not isinstance(target_obj, (discord.Member, discord.User)): return await ctx.error("Extra Owners must be users.")
                if target_obj.bot: return await ctx.error("Bots cannot be Extra Owners.")
                data = config.get('extra_owners', [])
                if target_obj.id not in data: data.append(target_obj.id)
                await self.db.update_one('automod_config', {'_id': ctx.guild.id}, {'extra_owners': data}, upsert=True)
            else:
                valid = ['links', 'invites', 'caps', 'spam', 'badwords', 'stickers', 'zalgo', 'ghostping', 'newaccount', 'images', 'mentions', 'duplicate', 'antinuke', 'verification']
                if scope not in valid: return await ctx.error("Invalid scope.")
                
                spec = config.get('whitelist_specific', {})
                if scope not in spec: spec[scope] = {'roles': [], 'channels': [], 'users': []}
                
                if isinstance(target_obj, discord.Role): t_key = 'roles'
                elif isinstance(target_obj, (discord.Member, discord.User)): t_key = 'users'
                else: t_key = 'channels'
                
                if target_obj.id not in spec[scope][t_key]: spec[scope][t_key].append(target_obj.id)
                await self.db.update_one('automod_config', {'_id': ctx.guild.id}, {'whitelist_specific': spec}, upsert=True)
        
        await ctx.success(f"Added **{target}** to **{scope}** whitelist.")

    @whitelist_group.command(name='remove', help='Remove a role/channel/user from a whitelist.')
    @commands.has_permissions(administrator=True)
    async def whitelist_remove(self, ctx, scope: str, *, target: str):
        config = await self.get_config(ctx.guild.id)
        scope = scope.lower()
        
        if scope == 'links':
            links = config.get('whitelist_links', [])
            if target in links: links.remove(target)
            await self.db.update_one('automod_config', {'_id': ctx.guild.id}, {'whitelist_links': links}, upsert=True)
        elif scope == 'invites':
            invites = config.get('whitelist_invites', [])
            if target in invites: invites.remove(target)
            await self.db.update_one('automod_config', {'_id': ctx.guild.id}, {'whitelist_invites': invites}, upsert=True)
        else:
            try:
                target_obj = await commands.RoleConverter().convert(ctx, target)
            except:
                try: target_obj = await commands.TextChannelConverter().convert(ctx, target)
                except:
                    try: target_obj = await commands.MemberConverter().convert(ctx, target)
                    except: return await ctx.error("Target must be a Role, Channel, or Member.")
            
            if scope == 'global':
                if isinstance(target_obj, discord.Role): key = 'whitelist_global_roles'
                elif isinstance(target_obj, (discord.Member, discord.User)): key = 'whitelist_global_users'
                else: key = 'whitelist_global_channels'
                
                data = config.get(key, [])
                if target_obj.id in data: data.remove(target_obj.id)
                await self.db.update_one('automod_config', {'_id': ctx.guild.id}, {key: data}, upsert=True)
            elif scope == 'extra_owner':
                data = config.get('extra_owners', [])
                if target_obj.id in data: data.remove(target_obj.id)
                await self.db.update_one('automod_config', {'_id': ctx.guild.id}, {'extra_owners': data}, upsert=True)
            else:
                spec = config.get('whitelist_specific', {})
                if scope in spec:
                    if isinstance(target_obj, discord.Role): t_key = 'roles'
                    elif isinstance(target_obj, (discord.Member, discord.User)): t_key = 'users'
                    else: t_key = 'channels'
                    
                    if target_obj.id in spec[scope][t_key]: spec[scope][t_key].remove(target_obj.id)
                    await self.db.update_one('automod_config', {'_id': ctx.guild.id}, {'whitelist_specific': spec}, upsert=True)
        
        await ctx.success(f"Removed **{target}** from **{scope}** whitelist.")

async def setup(bot):
    await bot.add_cog(Whitelist(bot))
