import discord
from discord.ext import commands
import datetime

class Utility2(commands.Cog):
    category = "utility"

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="listboosters", aliases=["boosties"], help="List all server boosters.")
    async def list_boosters(self, ctx):
        boosters = [m.mention for m in ctx.guild.premium_subscribers]
        if not boosters: return await ctx.info("This server has no boosters.")
        await ctx.embed("\n".join(boosters[:50]), title=f"Server Boosters ({len(boosters)})")

    @commands.command(name="listmods", aliases=["moderators"], help="List all moderators (users with manage messages).")
    async def list_mods(self, ctx):
        mods = [m.mention for m in ctx.guild.members if m.guild_permissions.manage_messages and not m.bot]
        if not mods: return await ctx.info("No moderators found.")
        await ctx.embed("\n".join(mods[:50]), title=f"Moderators ({len(mods)})")

    @commands.command(name="svb", help="View the server's banner.")
    async def server_banner(self, ctx):
        if not ctx.guild.banner: return await ctx.error("This server has no banner.")
        embed = self.bot.embed_manager.generic(description=f"[Download Banner]({ctx.guild.banner.url})", title=f"Banner: {ctx.guild.name}")
        embed.set_image(url=ctx.guild.banner.url)
        await ctx.send(embed=embed)

    @commands.command(name="rolemembers", help="List all members in a role.")
    async def role_members(self, ctx, role: discord.Role):
        members = [m.mention for m in role.members]
        if not members: return await ctx.info(f"No members in {role.mention}.")
        await ctx.embed("\n".join(members[:50]), title=f"Members with {role.name} ({len(members)})")

    @commands.command(name="recentjoins", help="List members who joined in the last 24 hours.")
    async def recent_joins(self, ctx):
        now = discord.utils.utcnow()
        recent = [m.mention for m in ctx.guild.members if m.joined_at and (now - m.joined_at).total_seconds() < 86400]
        if not recent: return await ctx.info("No members joined in the last 24 hours.")
        await ctx.embed("\n".join(recent[:50]), title=f"Recent Joins ({len(recent)})")

    @commands.command(name="vanity", help="Check the server's vanity URL.")
    async def server_vanity(self, ctx):
        try:
            invite = await ctx.guild.vanity_invite()
            await ctx.info(f"Server Vanity URL: **discord.gg/{ctx.guild.vanity_url_code}**\nUses: `{invite.uses}`", title="Vanity URL")
        except: await ctx.error("This server does not have a vanity URL.")

    @commands.command(name="membercount3", aliases=["mc3"], help="Show detailed member count.")
    async def member_count_detailed(self, ctx):
        total = ctx.guild.member_count
        bots = len([m for m in ctx.guild.members if m.bot])
        humans = total - bots
        await ctx.info(f"👥 **Humans:** {humans}\n🤖 **Bots:** {bots}\n📈 **Total:** {total}", title="Member Count")

    @commands.command(name="emojicp", help="Get a copyable list of all emojis.")
    @commands.has_permissions(manage_expressions=True)
    async def emoji_copy(self, ctx):
        emojis = " ".join([str(e) for e in ctx.guild.emojis])
        if not emojis: return await ctx.error("No emojis found.")
        await ctx.send(f"**Server Emojis:**\n{emojis[:1900]}")

    @commands.command(name="roleidlist", help="List all roles with their IDs.")
    @commands.has_permissions(manage_roles=True)
    async def role_id_list(self, ctx):
        desc = "\n".join([f"{r.name} - `{r.id}`" for r in sorted(ctx.guild.roles, key=lambda x: x.position, reverse=True) if not r.is_default()])
        await ctx.embed(desc[:4000], title="Role ID List")

    @commands.command(name="channelidlist3", help="List all channels with their IDs.")
    @commands.has_permissions(manage_channels=True)
    async def channel_id_list(self, ctx):
        desc = "\n".join([f"{c.name} - `{c.id}`" for c in ctx.guild.channels[:50]])
        await ctx.embed(desc, title="Channel ID List")

    @commands.command(name="listbots2", help="List all bots in the server.")
    async def list_bots_v2(self, ctx):
        bots = [m.mention for m in ctx.guild.members if m.bot]
        if not bots: return await ctx.info("No bots found.")
        await ctx.embed("\n".join(bots[:50]), title=f"Bots in Server ({len(bots)})")

    @commands.command(name="listadmins2", help="List all administrators.")
    async def list_admins_v2(self, ctx):
        admins = [m.mention for m in ctx.guild.members if m.guild_permissions.administrator and not m.bot]
        if not admins: return await ctx.info("No admins found.")
        await ctx.embed("\n".join(admins[:50]), title=f"Administrators ({len(admins)})")

    @commands.command(name="clonerole", help="Clone a role's permissions.")
    @commands.has_permissions(manage_roles=True)
    async def clone_role(self, ctx, role: discord.Role, *, name: str):
        new_role = await ctx.guild.create_role(
            name=name,
            permissions=role.permissions,
            color=role.color,
            hoist=role.hoist,
            mentionable=role.mentionable,
            reason=f"Cloned from {role.name} by {ctx.author}"
        )
        await ctx.success(f"Successfully cloned {role.mention} to {new_role.mention}!")

    @commands.command(name="hastebin", aliases=["haste"], help="Upload text to Hastebin.")
    async def haste_upload(self, ctx, *, content: str):
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.post("https://hastebin.com/documents", data=content) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        await ctx.success(f"Content uploaded: https://hastebin.com/{data['key']}")
                    else:
                        await ctx.error("Failed to upload to Hastebin.")

    @commands.command(name="urban2", help="Advanced Urban Dictionary search.")
    async def urban_v2(self, ctx, *, term: str):
        url = f"https://api.urbandictionary.com/v0/define?term={urllib.parse.quote(term)}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()
        if not data['list']: return await ctx.error("No results.")
        res = data['list'][0]
        await ctx.embed(f"**Word:** {res['word']}\n\n**Definition:**\n{res['definition'][:1000]}", title="Urban Dictionary V2")

    @commands.command(name="search", help="Perform a web search.")
    async def web_search(self, ctx, *, query: str):
        url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        await ctx.info(f"Results for **{query}**:\n\n[**Click Here to View**]({url})", title="Google Search")

    @commands.command(name="youtube", aliases=["yt"], help="Search for something on YouTube.")
    async def yt_search(self, ctx, *, query: str):
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
        await ctx.info(f"YouTube results for **{query}**:\n\n[**Watch Here**]({url})", title="YouTube Search")

    @commands.command(name="githubuser", help="Search for a GitHub user.")
    async def gh_user(self, ctx, *, username: str):
        url = f"https://github.com/{urllib.parse.quote(username)}"
        await ctx.info(f"GitHub Profile for **{username}**:\n\n[**View Profile**]({url})", title="GitHub Search")

    @commands.command(name="mcachieve", help="Generate a Minecraft achievement image.")
    async def mc_achieve(self, ctx, *, text: str):
        url = f"https://minecraftoverly.com/api/achievements/generate?text={urllib.parse.quote(text)}"
        # Note: Using a placeholder generator if API is down
        url = f"https://minecraftskinstealer.com/achievement/a.php?i=1&h=Achievement+Get!&t={urllib.parse.quote(text)}"
        embed = self.bot.embed_manager.generic(description="Achievement unlocked!", title="Minecraft Achievement")
        embed.set_image(url=url)
        await ctx.send(embed=embed)

    @commands.command(name="ipinfo2", help="Advanced IP lookup.")
    async def ip_info_v2(self, ctx, ip: str):
        url = f"http://ip-api.com/json/{ip}"
        async with aiohttp.ClientSession() as s:
            async with s.get(url) as r:
                d = await r.json()
        if d['status'] == 'fail': return await ctx.error("Invalid IP.")
        await ctx.embed(f"**IP:** {ip}\n**ISP:** {d['isp']}\n**Location:** {d['city']}, {d['country']}", title="IP Lookup V2")

    @commands.command(name="servericon3", help="Get the high-res server icon.")
    async def server_icon_v2(self, ctx):
        if not ctx.guild.icon: return await ctx.error("No icon.")
        await ctx.embed(f"[Download]({ctx.guild.icon.url})", title=f"Icon: {ctx.guild.name}", image_url=ctx.guild.icon.url)

    @commands.command(name="useravatar2", help="Get the high-res user avatar.")
    async def user_avatar_v2(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        await ctx.embed(f"[Download]({member.display_avatar.url})", title=f"Avatar: {member.name}", image_url=member.display_avatar.url)

    @commands.command(name="listemojis", help="List all server emojis.")
    async def list_emojis_v2(self, ctx):
        e_list = " ".join([str(e) for e in ctx.guild.emojis[:50]])
        if not e_list: return await ctx.info("No emojis.")
        await ctx.embed(e_list, title=f"Emojis ({len(ctx.guild.emojis)})")

    @commands.command(name="listroles2", help="Detailed list of all roles.")
    async def list_roles_v2(self, ctx):
        roles = "\n".join([f"{r.mention} (`{r.id}`)" for r in sorted(ctx.guild.roles, key=lambda x: x.position, reverse=True) if not r.is_default()])
        await ctx.embed(roles[:2000], title=f"Roles ({len(ctx.guild.roles)})")

    @commands.command(name="serverid2", help="Get the server's unique ID.")
    async def server_id_v2(self, ctx):
        await ctx.info(f"The ID for this server is: `{ctx.guild.id}`", title="Server ID")

    @commands.command(name="listbots_detailed", help="List all bots with their join dates.")
    async def list_bots_detailed(self, ctx):
        bots = sorted([m for m in ctx.guild.members if m.bot], key=lambda x: x.joined_at or ctx.message.created_at)
        desc = "\n".join([f"• {m.mention} - Joined <t:{int(m.joined_at.timestamp())}:R>" for m in bots[:15]])
        await ctx.embed(desc, title=f"Server Bots ({len(bots)})")

    @commands.command(name="listsystem", help="List server system channels.")
    async def list_system(self, ctx):
        guild = ctx.guild
        desc = (
            f"**System Channel:** {guild.system_channel.mention if guild.system_channel else 'None'}\n"
            f"**Rules Channel:** {guild.rules_channel.mention if guild.rules_channel else 'None'}\n"
            f"**Public Updates:** {guild.public_updates_channel.mention if guild.public_updates_channel else 'None'}\n"
            f"**AFK Channel:** {guild.afk_channel.mention if guild.afk_channel else 'None'} ({guild.afk_timeout // 60}m)"
        )
        await ctx.embed(desc, title="Server System Configuration")

    @commands.command(name="membercount2", help="Live member count progress.")
    async def member_count_progress(self, ctx):
        total = ctx.guild.member_count
        target = ((total // 100) + 1) * 100
        progress = (total / target) * 100
        bar = "█" * int(progress / 10) + "░" * (10 - int(progress / 10))
        await ctx.info(f"**Current:** `{total}`\n**Target:** `{target}`\n\n`{bar}` `{progress:.1f}%`", title="Growth Tracker")

    @commands.command(name="rolemembers2", help="Find all users in a specific role (paginated).")
    async def role_members_v2(self, ctx, role: discord.Role):
        members = [m.mention for m in role.members]
        if not members: return await ctx.info("No members found.")
        await ctx.embed("\n".join(members[:25]), title=f"Users with {role.name} ({len(members)})")

    @commands.command(name="channelperms", help="Check permissions for a channel.")
    async def channel_perms_v2(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        perms = channel.permissions_for(ctx.author)
        allowed = ", ".join([p[0].replace('_', ' ').title() for p in perms if p[1]])
        await ctx.embed(f"**Your permissions in {channel.mention}:**\n\n{allowed}", title="Channel Permissions")

    @commands.command(name="serverowner", help="Quick link to the server owner.")
    async def server_owner_v2(self, ctx):
        await ctx.info(f"The owner of this server is **{ctx.guild.owner.mention}** (`{ctx.guild.owner_id}`)", title="Server Owner")

    @commands.command(name="toproles", help="Show roles with the most members.")
    async def top_roles(self, ctx):
        roles = sorted(ctx.guild.roles, key=lambda r: len(r.members), reverse=True)
        desc = "\n".join([f"• {r.mention} - `{len(r.members)}` members" for r in roles[:10] if not r.is_default()])
        await ctx.embed(desc, title="Top Roles by Member Count")

    @commands.command(name="emojilist2", help="Get a list of all animated emojis.")
    async def animated_emojis(self, ctx):
        animated = [str(e) for e in ctx.guild.emojis if e.animated]
        if not animated: return await ctx.info("No animated emojis.")
        await ctx.embed(" ".join(animated[:30]), title=f"Animated Emojis ({len(animated)})")

    @commands.command(name="rolecount2", help="Show breakdown of managed vs custom roles.")
    async def role_breakdown(self, ctx):
        managed = len([r for r in ctx.guild.roles if r.managed])
        custom = len(ctx.guild.roles) - managed - 1
        await ctx.info(f"🛠️ **Managed:** {managed}\n🎨 **Custom:** {custom}\n📊 **Total:** {len(ctx.guild.roles)}", title="Role Breakdown")

    @commands.command(name="servercreated2", help="Detailed creation age of the server.")
    async def server_age_detailed(self, ctx):
        age = (discord.utils.utcnow() - ctx.guild.created_at).days
        await ctx.info(f"This server was created **{age:,} days ago** on <t:{int(ctx.guild.created_at.timestamp())}:D>.", title="Server History")

async def setup(bot):
    await bot.add_cog(Utility2(bot))
