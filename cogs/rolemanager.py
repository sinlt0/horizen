import discord
from discord.ext import commands
import asyncio
import datetime

class RoleManager(commands.Cog):
    category = 'utility'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager

    @commands.group(name='role', aliases=['rolecmd'], invoke_without_command=True, help='Advanced role management commands.')
    @commands.has_permissions(manage_roles=True)
    async def role_group(self, ctx):
        await ctx.send_help(ctx.command)

    @role_group.command(name='give', help='Give a role to a member.')
    @commands.has_permissions(manage_roles=True)
    async def role_give(self, ctx, member: discord.Member, role: discord.Role, *, reason: str = 'Staff action'):
        if role >= ctx.guild.me.top_role:
            return await ctx.error('That role is above my highest role.')
        await member.add_roles(role, reason=reason)
        await ctx.success(f'{self.bot.e.success} Gave {role.mention} to {member.mention}.')

    @role_group.command(name='take', help='Remove a role from a member.')
    @commands.has_permissions(manage_roles=True)
    async def role_take(self, ctx, member: discord.Member, role: discord.Role, *, reason: str = 'Staff action'):
        await member.remove_roles(role, reason=reason)
        await ctx.success(f'{self.bot.e.success} Removed {role.mention} from {member.mention}.')

    @role_group.command(name='rinfo3', help='Show detailed information about a role.')
    async def role_info2(self, ctx, role: discord.Role):
        perms = [p.replace('_', ' ').title() for p, v in role.permissions if v]
        embed = self.bot.embed_manager.generic(
            description=(
                f'**ID:** `{role.id}`\n'
                f'**Color:** `{str(role.color)}`\n'
                f'**Members:** `{len(role.members)}`\n'
                f'**Mentionable:** `{role.mentionable}`\n'
                f'**Hoisted:** `{role.hoist}`\n'
                f'**Managed:** `{role.managed}`\n'
                f'**Position:** `{role.position}`\n'
                f'**Created:** <t:{int(role.created_at.timestamp())}:R>\n'
                f'**Key Perms:** {", ".join(perms[:8]) or "None"}'
            ),
            title=f'Role: @{role.name}'
        )
        embed.color = role.color
        await ctx.send(embed=embed)

    @role_group.command(name='rmembers3', help='List all members with a specific role.')
    async def role_members2(self, ctx, role: discord.Role):
        members = role.members[:30]
        if not members:
            return await ctx.info(f'No members have {role.mention}.')
        desc = '\n'.join([f'• {m.mention} (`{m.id}`)' for m in members])
        if len(role.members) > 30:
            desc += f'\n*... and `{len(role.members) - 30}` more*'
        embed = self.bot.embed_manager.generic(description=desc, title=f'{role.name} — {len(role.members)} members')
        await ctx.send(embed=embed)

    @role_group.command(name='create', help='Create a new role. Usage: role create Name [#color]')
    @commands.has_permissions(manage_roles=True)
    async def role_create(self, ctx, name: str, color: str = None):
        c = discord.Color.default()
        if color:
            try:
                c = discord.Color(int(color.lstrip('#'), 16))
            except Exception:
                return await ctx.error('Invalid hex color.')
        role = await ctx.guild.create_role(name=name, color=c, reason=f'Created by {ctx.author}')
        await ctx.success(f'{self.bot.e.success} Created role {role.mention}.')

    @role_group.command(name='delete', help='Delete a role.')
    @commands.has_permissions(manage_roles=True)
    async def role_delete(self, ctx, role: discord.Role):
        name = role.name
        await role.delete(reason=f'Deleted by {ctx.author}')
        await ctx.success(f'{self.bot.e.success} Deleted role **{name}**.')

    @role_group.command(name='clone', help='Clone an existing role.')
    @commands.has_permissions(manage_roles=True)
    async def role_clone(self, ctx, role: discord.Role, *, new_name: str = None):
        new_role = await role.clone(name=new_name or f'{role.name} (copy)')
        await ctx.success(f'{self.bot.e.success} Cloned {role.mention} → {new_role.mention}.')

    @role_group.command(name='hoist', help='Toggle whether a role is displayed separately in member list.')
    @commands.has_permissions(manage_roles=True)
    async def role_hoist(self, ctx, role: discord.Role):
        await role.edit(hoist=not role.hoist)
        state = 'hoisted' if role.hoist else 'unhoisted'
        await ctx.success(f'{self.bot.e.success} **{role.name}** is now {state}.')

    @role_group.command(name='mentionable', help='Toggle whether a role can be mentioned by anyone.')
    @commands.has_permissions(manage_roles=True)
    async def role_mentionable(self, ctx, role: discord.Role):
        await role.edit(mentionable=not role.mentionable)
        state = 'mentionable' if role.mentionable else 'unmentionable'
        await ctx.success(f'{self.bot.e.success} **{role.name}** is now {state}.')

    @role_group.command(name='color', help='Change a role color. Usage: role color @Role #FF5733')
    @commands.has_permissions(manage_roles=True)
    async def role_color(self, ctx, role: discord.Role, color: str):
        try:
            c = discord.Color(int(color.lstrip('#'), 16))
            await role.edit(color=c)
            await ctx.success(f'{self.bot.e.success} **{role.name}** color set to `{color}`.')
        except Exception:
            await ctx.error('Invalid hex color.')

    @role_group.command(name='rename', aliases=['rname'], help='Rename a role.')
    @commands.has_permissions(manage_roles=True)
    async def role_rename(self, ctx, role: discord.Role, *, new_name: str):
        old = role.name
        await role.edit(name=new_name)
        await ctx.success(f'{self.bot.e.success} Renamed **{old}** → **{new_name}**.')

    @role_group.command(name='addperm', help='Grant a permission to a role. Usage: role addperm @Role send_messages')
    @commands.has_permissions(administrator=True)
    async def role_addperm(self, ctx, role: discord.Role, *, permission: str):
        perm = permission.lower().replace(' ', '_')
        current = dict(role.permissions)
        if perm not in current:
            return await ctx.error(f'Invalid permission: `{perm}`.')
        current[perm] = True
        await role.edit(permissions=discord.Permissions(**current))
        await ctx.success(f'{self.bot.e.success} Granted `{perm}` to **{role.name}**.')

    @role_group.command(name='removeperm', help='Revoke a permission from a role.')
    @commands.has_permissions(administrator=True)
    async def role_removeperm(self, ctx, role: discord.Role, *, permission: str):
        perm = permission.lower().replace(' ', '_')
        current = dict(role.permissions)
        if perm not in current:
            return await ctx.error(f'Invalid permission: `{perm}`.')
        current[perm] = False
        await role.edit(permissions=discord.Permissions(**current))
        await ctx.success(f'{self.bot.e.success} Revoked `{perm}` from **{role.name}**.')

    @role_group.command(name='perms', help='Show all permissions for a role.')
    async def role_perms(self, ctx, role: discord.Role):
        granted = [p.replace('_', ' ').title() for p, v in role.permissions if v]
        denied = [p.replace('_', ' ').title() for p, v in role.permissions if not v]
        embed = self.bot.embed_manager.generic(
            description=f'**Granted ({len(granted)}):**\n{", ".join(granted[:20]) or "None"}\n\n**Denied ({len(denied)}):**\n{", ".join(denied[:10]) or "None"}',
            title=f'🔐 Permissions — @{role.name}'
        )
        await ctx.send(embed=embed)

    @role_group.command(name='above', help='Move a role above another role.')
    @commands.has_permissions(manage_roles=True)
    async def role_above(self, ctx, role: discord.Role, above: discord.Role):
        if above.position >= ctx.guild.me.top_role.position:
            return await ctx.error('Cannot move role above my highest role.')
        await role.edit(position=above.position + 1)
        await ctx.success(f'{self.bot.e.success} Moved **{role.name}** above **{above.name}**.')

    @role_group.command(name='below', help='Move a role below another role.')
    @commands.has_permissions(manage_roles=True)
    async def role_below(self, ctx, role: discord.Role, below: discord.Role):
        new_pos = max(1, below.position - 1)
        await role.edit(position=new_pos)
        await ctx.success(f'{self.bot.e.success} Moved **{role.name}** below **{below.name}**.')

    @role_group.command(name='rlist3', help='List all roles in the server with member counts.')
    async def role_list2(self, ctx):
        roles = [r for r in reversed(ctx.guild.roles) if r.name != '@everyone']
        desc = '\n'.join([f'`{r.position}` {r.mention} — `{len(r.members)}` members' for r in roles[:25]])
        embed = self.bot.embed_manager.generic(description=desc, title=f'🎭 Server Roles ({len(roles)})')
        await ctx.send(embed=embed)

    @role_group.command(name='unique', help='Show members who have a role that no one else shares.')
    async def role_unique(self, ctx):
        unique = []
        for role in ctx.guild.roles:
            if len(role.members) == 1 and role.name != '@everyone':
                unique.append(f'{role.mention} — {role.members[0].mention}')
        if not unique:
            return await ctx.info('No unique roles found.')
        embed = self.bot.embed_manager.generic(description='\n'.join(unique[:20]), title='🦄 Unique Roles')
        await ctx.send(embed=embed)

    @role_group.command(name='empty', help='Show roles with no members.')
    async def role_empty(self, ctx):
        empty = [r for r in ctx.guild.roles if len(r.members) == 0 and r.name != '@everyone' and not r.managed]
        if not empty:
            return await ctx.info('No empty roles found.')
        desc = '\n'.join([r.mention for r in empty[:25]])
        embed = self.bot.embed_manager.generic(description=desc, title=f'🕳️ Empty Roles ({len(empty)})')
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(RoleManager(bot))
