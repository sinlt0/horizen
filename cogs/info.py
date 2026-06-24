import discord
from discord.ext import commands
import time
import datetime
import platform
try:
    import psutil
except ImportError:
    psutil = None
import os

class Information(commands.Cog):
    category = 'info'

    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()

    @commands.command(name="ping", help="Checks the bot's latency.")
    async def ping_cmd(self, ctx):
        start_time = time.time()
        message = await ctx.info(f"Pinging... {getattr(self.bot.e, 'loading', '⏳')}")
        end_time = time.time()
        
        latency = round(self.bot.latency * 1000)
        api_latency = round((end_time - start_time) * 1000)
        
        await message.edit(embed=self.bot.embed_manager.success(
            f"**Gateway:** `{latency}ms`\n**API:** `{api_latency}ms`",
            title="Pong! 🏓"
        ))

    @commands.command(name='serverinfo', aliases=['si'], help='View detailed information about the server.')
    async def server_info(self, ctx):
        guild = ctx.guild
        owner = guild.owner
        
        embed = self.bot.embed_manager.generic(
            title=f"{ctx.e.server} Server Information: {guild.name}",
            description=guild.description or "No server description."
        )
        embed.set_thumbnail(url=guild.icon.url if guild.icon else "")
        
        embed.add_field(name=f"{ctx.e.owner} Owner", value=f"{owner.mention}\n`{owner.id}`", inline=True)
        embed.add_field(name=f"{ctx.e.id} Server ID", value=f"`{guild.id}`", inline=True)
        embed.add_field(name=f"{ctx.e.created} Created", value=f"<t:{int(guild.created_at.timestamp())}:R>", inline=True)
        
        counts = (
            f"**Total:** {guild.member_count}\n"
            f"**Humans:** {len([m for m in guild.members if not m.bot])}\n"
            f"**Bots:** {len([m for m in guild.members if m.bot])}"
        )
        embed.add_field(name=f"{ctx.e.members} Members", value=counts, inline=True)
        
        channels = (
            f"**Total:** {len(guild.channels)}\n"
            f"**Text:** {len(guild.text_channels)}\n"
            f"**Voice:** {len(guild.voice_channels)}"
        )
        embed.add_field(name=f"{ctx.e.channels} Channels", value=channels, inline=True)
        
        boosts = (
            f"**Level:** {guild.premium_tier}\n"
            f"**Boosts:** {guild.premium_subscription_count}"
        )
        embed.add_field(name=f"{ctx.e.boost} Boosts", value=boosts, inline=True)
        
        roles = sorted(guild.roles, key=lambda x: x.position, reverse=True)
        roles_mentions = [role.mention for role in roles[1:11]] # Top 10
        roles_str = ", ".join(roles_mentions)
        if len(roles) > 11:
            roles_str += f" and {len(roles) - 11} more..."
            
        embed.add_field(name=f"{ctx.e.roles} Roles ({len(guild.roles) - 1})", value=roles_str if roles_str else "None", inline=False)
        
        if guild.features:
            features = ", ".join([f"`{f.replace('_', ' ').capitalize()}`" for f in guild.features[:15]])
            embed.add_field(name="Features", value=features, inline=False)
            
        # Module Status
        v_conf = await self.bot.db_manager.find_one('verification_config', {'_id': guild.id})
        vm_conf = await self.bot.db_manager.find_one('voicemaster_config', {'_id': guild.id})
        am_conf = await self.bot.db_manager.find_one('automod_config', {'_id': guild.id})
        
        status_line = (
            f"**Verification:** {'✅' if v_conf and v_conf.get('enabled') else '❌'} | "
            f"**VoiceMaster:** {'✅' if vm_conf else '❌'} | "
            f"**AutoMod:** {'✅' if am_conf else '❌'} | "
            f"**AntiNuke:** {'✅' if am_conf and am_conf.get('antinuke_enabled') else '❌'}"
        )
        embed.add_field(name="🛡️ Security Modules", value=status_line, inline=False)
            
        if guild.banner: embed.set_image(url=guild.banner.url)
        
        await ctx.send(embed=embed)

    @commands.command(name='userinfo', aliases=['ui'], help='View detailed information about a user.')
    async def user_info(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        roles = sorted(member.roles, key=lambda x: x.position, reverse=True)
        
        embed = self.bot.embed_manager.generic(
            description="",
            title=f"{ctx.e.user} User Information: {member.name}"
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        embed.add_field(name="Name", value=str(member), inline=True)
        embed.add_field(name=f"{ctx.e.id} ID", value=f"`{member.id}`", inline=True)
        embed.add_field(name="Nickname", value=member.nick or "None", inline=True)
        
        embed.add_field(name=f"{ctx.e.created} Account Created", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
        embed.add_field(name=f"{ctx.e.joined} Joined Server", value=f"<t:{int(member.joined_at.timestamp())}:R>", inline=True)
        
        if member.premium_since:
            embed.add_field(name=f"{ctx.e.boost} Boosting Since", value=f"<t:{int(member.premium_since.timestamp())}:R>", inline=True)

        role_str = ", ".join([role.mention for role in roles[1:15]]) # Top 15
        if len(roles) > 16:
            role_str += f" and {len(roles) - 16} more..."
        embed.add_field(name=f"{ctx.e.roles} Roles ({len(member.roles) - 1})", value=role_str or "None", inline=False)
        
        permissions = [p[0].replace('_', ' ').capitalize() for p in member.guild_permissions if p[1]]
        if 'Administrator' in permissions:
            perm_str = "`Administrator`"
        else:
            perm_str = ", ".join([f"`{p}`" for p in permissions[:10]])
            if len(permissions) > 10: perm_str += f" and {len(permissions) - 10} more..."
            
        embed.add_field(name=f"{ctx.e.permissions} Key Permissions", value=perm_str or "None", inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name='botinfo', aliases=['bi', 'info'], help='View technical information about the bot.')
    async def information_command(self, ctx):
        uptime = str(datetime.timedelta(seconds=int(round(time.time() - self.start_time))))
        if psutil:
            process = psutil.Process(os.getpid())
            memory = process.memory_info().rss / 1024 / 1024
        else:
            memory = 0.0
        
        embed = self.bot.embed_manager.generic(description="", title=f"{ctx.e.bot} Bot Statistics: {self.bot.user.name}")
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        
        embed.add_field(name=f"{ctx.e.uptime} Uptime", value=f"`{uptime}`", inline=True)
        embed.add_field(name=f"{ctx.e.ping} Ping", value=f"`{round(self.bot.latency * 1000)}ms`", inline=True)
        embed.add_field(name=f"{ctx.e.memory} Memory", value=f"`{memory:.2f} MB`", inline=True)
        
        embed.add_field(name=f"{ctx.e.server} Guilds", value=f"`{len(self.bot.guilds)}`", inline=True)
        embed.add_field(name=f"{ctx.e.members} Total Users", value=f"`{sum(g.member_count for g in self.bot.guilds)}`", inline=True)
        embed.add_field(name=f"{ctx.e.commands} Commands", value=f"`{len(self.bot.commands)}`", inline=True)
        
        db_type = self.bot.db_manager.primary_type.upper() if self.bot.db_manager else "UNKNOWN"
        embed.add_field(name=f"{ctx.e.database} Database", value=f"`{db_type}`", inline=True)
        embed.add_field(name="Library", value="`discord.py`", inline=True)
        embed.add_field(name="Python", value=f"`{platform.python_version()}`", inline=True)
        
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Invite Bot", url=self.bot.config.INVITE_LINK, style=discord.ButtonStyle.link))
        view.add_item(discord.ui.Button(label="Support Server", url=self.bot.config.SUPPORT_SERVER, style=discord.ButtonStyle.link))
        view.add_item(discord.ui.Button(label="Website", url=self.bot.config.WEBSITE, style=discord.ButtonStyle.link))
        
        await ctx.send(embed=embed, view=view)

    @commands.command(name='avatar', aliases=['av', 'pfp'], help='View the avatar of a user.')
    async def avatar(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        avatar = member.display_avatar
        embed = self.bot.embed_manager.generic(description="", title=f"{ctx.e.user} Avatar: {member.name}")
        embed.set_image(url=avatar.url)
        
        formats = ["png", "jpg", "webp"]
        if avatar.is_animated():
            formats.append("gif")
            
        links = []
        for fmt in formats:
            try:
                links.append(f"[{fmt.upper()}]({avatar.replace(format=fmt).url})")
            except: continue
            
        embed.description = " | ".join(links)
        await ctx.send(embed=embed)

    @commands.command(name='roleinfo', aliases=['ri'], help='View detailed information about a role.')
    async def role_info(self, ctx, *, role: discord.Role):
        embed = self.bot.embed_manager.generic(description="", title=f"{ctx.e.roles} Role Information: {role.name}", color=role.color if role.color.value != 0 else None)
        embed.add_field(name=f"{ctx.e.id} ID", value=f"`{role.id}`", inline=True)
        embed.add_field(name="Color", value=f"`{str(role.color).upper()}`", inline=True)
        embed.add_field(name="Position", value=f"`{role.position}`", inline=True)
        embed.add_field(name="Mentionable", value=f"`{role.mentionable}`", inline=True)
        embed.add_field(name="Hoisted", value=f"`{role.hoist}`", inline=True)
        embed.add_field(name="Managed", value=f"`{role.managed}`", inline=True)
        embed.add_field(name=f"{ctx.e.members} Members", value=f"`{len(role.members)}`", inline=True)
        embed.add_field(name=f"{ctx.e.created} Created", value=f"<t:{int(role.created_at.timestamp())}:R>", inline=True)
        
        perms = [p[0].replace('_', ' ').capitalize() for p in role.permissions if p[1]]
        embed.add_field(name=f"{ctx.e.permissions} Permissions", value=", ".join([f"`{p}`" for p in perms[:15]]) + (f" and {len(perms)-15} more..." if len(perms) > 15 else "") or "None", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name='channelinfo', aliases=['ci'], help='View detailed information about a channel.')
    async def channel_info(self, ctx, *, channel: discord.abc.GuildChannel = None):
        channel = channel or ctx.channel
        embed = self.bot.embed_manager.generic(description="", title=f"{ctx.e.channels} Channel Information: {channel.name}")
        embed.add_field(name=f"{ctx.e.id} ID", value=f"`{channel.id}`", inline=True)
        embed.add_field(name="Type", value=f"`{str(channel.type).capitalize()}`", inline=True)
        embed.add_field(name="Category", value=f"`{channel.category.name if channel.category else 'None'}`", inline=True)
        embed.add_field(name="Position", value=f"`{channel.position}`", inline=True)
        embed.add_field(name=f"{ctx.e.created} Created", value=f"<t:{int(channel.created_at.timestamp())}:R>", inline=True)
        
        if isinstance(channel, discord.TextChannel):
            embed.add_field(name="NSFW", value=f"`{channel.is_nsfw()}`", inline=True)
            embed.add_field(name="Slowmode", value=f"`{channel.slowmode_delay}s`", inline=True)
            if channel.topic: embed.description = f"**Topic:** {channel.topic}"
        elif isinstance(channel, discord.VoiceChannel):
            embed.add_field(name="Bitrate", value=f"`{channel.bitrate//1000}kbps`", inline=True)
            embed.add_field(name="User Limit", value=f"`{channel.user_limit or 'Unlimited'}`", inline=True)
            
        await ctx.send(embed=embed)

    @commands.command(name='membercount', aliases=['mc'], help='View detailed member counts for the server.')
    async def member_count(self, ctx):
        guild = ctx.guild
        humans = len([m for m in guild.members if not m.bot])
        bots = len([m for m in guild.members if m.bot])
        
        embed = self.bot.embed_manager.generic(
            description=(
                f"👥 **Total Members:** {guild.member_count}\n"
                f"👤 **Humans:** {humans}\n"
                f"🤖 **Bots:** {bots}"
            ),
            title=f"Member Count: {guild.name}"
        )
        await ctx.send(embed=embed)

    @commands.command(name='boosters', help='View the list of server boosters.')
    async def list_boosters(self, ctx):
        boosters = sorted([m for m in ctx.guild.members if m.premium_since], key=lambda x: x.premium_since)
        
        if not boosters:
            return await ctx.info("This server doesn't have any boosters yet.")
            
        desc = "\n".join([f"• {m.mention} - <t:{int(m.premium_since.timestamp())}:R>" for m in boosters[:20]])
        if len(boosters) > 20:
            desc += f"\n... and {len(boosters) - 20} more."
            
        embed = self.bot.embed_manager.generic(
            description=desc,
            title=f"Server Boosters ({len(boosters)})"
        )
        await ctx.send(embed=embed)

    @commands.command(name='banner', help='View the banner of the server or a user.')
    async def banner(self, ctx, member: discord.Member = None):
        if member:
            # Fetch full user to get banner
            user = await self.bot.fetch_user(member.id)
            if not user.banner:
                return await ctx.error(f"{member.name} does not have a banner.")
            url = user.banner.url
            title = f"Banner: {member.name}"
        else:
            if not ctx.guild.banner:
                return await ctx.error("This server does not have a banner.")
            url = ctx.guild.banner.url
            title = f"Server Banner: {ctx.guild.name}"
            
        embed = self.bot.embed_manager.generic(description=f"[Download Banner]({url})", title=title)
        embed.set_image(url=url)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Information(bot))
