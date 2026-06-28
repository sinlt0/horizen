import discord
from discord.ext import commands, tasks
import asyncio
import datetime
import re

class ModTools(commands.Cog):
    category = 'moderation'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager
        self._snipe_cache = {}
        self._edit_snipe_cache = {}
        self._mute_tasks = {}
        self._temp_role_tasks = {}

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot or not message.guild:
            return
        self._snipe_cache[message.channel.id] = {
            'content': message.content,
            'author': message.author,
            'timestamp': message.created_at,
            'attachments': [a.url for a in message.attachments]
        }

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot or not before.guild or before.content == after.content:
            return
        self._edit_snipe_cache[before.channel.id] = {
            'before': before.content,
            'after': after.content,
            'author': before.author,
            'timestamp': before.edited_at or before.created_at,
            'jump_url': after.jump_url
        }

    @commands.command(name='snipe', help='Show the last deleted message in this channel.')
    @commands.has_permissions(manage_messages=True)
    async def snipe(self, ctx):
        data = self._snipe_cache.get(ctx.channel.id)
        if not data:
            return await ctx.error('Nothing to snipe here.')
        embed = self.bot.embed_manager.generic(
            description=data['content'] or '*[No text content]*',
            title=f'{self.bot.e.warning} Sniped Message'
        )
        embed.set_author(name=str(data['author']), icon_url=data['author'].display_avatar.url)
        embed.set_footer(text=f'Deleted at {data["timestamp"].strftime("%H:%M:%S")}')
        if data['attachments']:
            embed.set_image(url=data['attachments'][0])
        await ctx.send(embed=embed)

    @commands.command(name='editsnipe', aliases=['esnipe'], help='Show the last edited message in this channel.')
    @commands.has_permissions(manage_messages=True)
    async def editsnipe(self, ctx):
        data = self._edit_snipe_cache.get(ctx.channel.id)
        if not data:
            return await ctx.error('Nothing to edit-snipe here.')
        embed = self.bot.embed_manager.generic(
            description=f'**Before:** {data["before"]}\n**After:** {data["after"]}',
            title=f'{self.bot.e.warning} Edit Sniped'
        )
        embed.set_author(name=str(data['author']), icon_url=data['author'].display_avatar.url)
        embed.add_field(name='Jump', value=f'[Click here]({data["jump_url"]})')
        await ctx.send(embed=embed)

    @commands.command(name='slowmode', aliases=['slow'], help='Set slowmode for the current channel (0 to disable).')
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, seconds: int):
        if seconds < 0 or seconds > 21600:
            return await ctx.error('Slowmode must be between 0 and 21600 seconds.')
        await ctx.channel.edit(slowmode_delay=seconds)
        if seconds == 0:
            await ctx.success(f'{self.bot.e.success} Slowmode disabled.')
        else:
            await ctx.success(f'{self.bot.e.success} Slowmode set to `{seconds}s`.')

    @commands.command(name='lock', help='Lock the current or specified channel.')
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        overwrite = channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = False
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.success(f'{self.bot.e.success} {channel.mention} locked.')

    @commands.command(name='unlock', help='Unlock the current or specified channel.')
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        overwrite = channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = None
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.success(f'{self.bot.e.success} {channel.mention} unlocked.')

    @commands.command(name='channelhide', aliases=['chide'], help='Hide the current or specified channel from everyone.')
    @commands.has_permissions(manage_channels=True)
    async def hide(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        overwrite = channel.overwrites_for(ctx.guild.default_role)
        overwrite.view_channel = False
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.success(f'{self.bot.e.success} {channel.mention} hidden.')

    @commands.command(name='channelunhide', aliases=['cunhide'], help='Unhide the current or specified channel.')
    @commands.has_permissions(manage_channels=True)
    async def unhide(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        overwrite = channel.overwrites_for(ctx.guild.default_role)
        overwrite.view_channel = None
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.success(f'{self.bot.e.success} {channel.mention} is now visible.')

    @commands.command(name='rename', help='Rename the current channel.')
    @commands.has_permissions(manage_channels=True)
    async def rename(self, ctx, *, name: str):
        if len(name) > 100:
            return await ctx.error('Channel name must be under 100 characters.')
        old = ctx.channel.name
        await ctx.channel.edit(name=name)
        await ctx.success(f'{self.bot.e.success} Channel renamed from `{old}` to `{name}`.')

    @commands.command(name='setnick', aliases=['nick'], help='Set the nickname of a member.')
    @commands.has_permissions(manage_nicknames=True)
    async def setnick(self, ctx, member: discord.Member, *, nick: str = None):
        await member.edit(nick=nick)
        if nick:
            await ctx.success(f'{self.bot.e.success} Set {member.mention}\'s nickname to **{nick}**.')
        else:
            await ctx.success(f'{self.bot.e.success} Reset {member.mention}\'s nickname.')

    @commands.command(name='resetnick', help='Reset the nickname of a member.')
    @commands.has_permissions(manage_nicknames=True)
    async def resetnick(self, ctx, member: discord.Member):
        await member.edit(nick=None)
        await ctx.success(f'{self.bot.e.success} Reset {member.mention}\'s nickname.')

    @commands.command(name='massban', help='Ban multiple users by ID. Separate IDs with spaces.')
    @commands.has_permissions(ban_members=True)
    async def massban(self, ctx, *user_ids: int):
        if not user_ids:
            return await ctx.error('Provide at least one user ID.')
        banned = []
        failed = []
        for uid in user_ids:
            try:
                user = await self.bot.fetch_user(uid)
                await ctx.guild.ban(user, reason=f'Mass ban by {ctx.author}')
                banned.append(str(uid))
            except Exception:
                failed.append(str(uid))
        msg = f'{self.bot.e.success} Banned `{len(banned)}` users.'
        if failed:
            msg += f'\nFailed: `{"`, `".join(failed)}`'
        await ctx.success(msg)

    @commands.command(name='softban', help='Ban then immediately unban a user to delete their messages.')
    @commands.has_permissions(ban_members=True)
    async def softban(self, ctx, member: discord.Member, *, reason: str = 'Softban'):
        await ctx.guild.ban(member, reason=f'Softban by {ctx.author}: {reason}', delete_message_days=7)
        await ctx.guild.unban(member, reason='Softban — automatic unban')
        await ctx.success(f'{self.bot.e.success} Softbanned {member.mention} and cleared their messages.')

    @commands.command(name='temprole', help='Temporarily assign a role to a user. Duration: 10m, 2h, 1d.')
    @commands.has_permissions(manage_roles=True)
    async def temprole(self, ctx, member: discord.Member, role: discord.Role, duration: str):
        match = re.match(r'(\d+)([smhd])', duration.lower())
        if not match:
            return await ctx.error('Invalid duration. Use `10m`, `2h`, `1d`.')
        amount, unit = int(match.group(1)), match.group(2)
        seconds = amount * {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}[unit]
        await member.add_roles(role, reason=f'Temprole by {ctx.author}')
        await ctx.success(f'{self.bot.e.success} Gave {member.mention} **{role.name}** for `{duration}`.')

        async def remove_later():
            await asyncio.sleep(seconds)
            try:
                await member.remove_roles(role, reason='Temprole expired')
            except Exception:
                pass

        task = self.bot.loop.create_task(remove_later())
        self._temp_role_tasks[f'{ctx.guild.id}:{member.id}:{role.id}'] = task

    @commands.command(name='massrole', help='Add a role to all members (or all humans/bots).')
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def massrole(self, ctx, role: discord.Role, target: str = 'all'):
        target = target.lower()
        if target == 'humans':
            members = [m for m in ctx.guild.members if not m.bot]
        elif target == 'bots':
            members = [m for m in ctx.guild.members if m.bot]
        else:
            members = ctx.guild.members
        msg = await ctx.info(f'Adding **{role.name}** to `{len(members)}` members...')
        count = 0
        for m in members:
            try:
                await m.add_roles(role)
                count += 1
                await asyncio.sleep(0.5)
            except Exception:
                pass
        await msg.edit(content=f'{self.bot.e.success} Added **{role.name}** to `{count}` members.')

    @commands.command(name='unrole', help='Remove a role from all members who have it.')
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def unrole(self, ctx, role: discord.Role):
        members = [m for m in ctx.guild.members if role in m.roles]
        msg = await ctx.info(f'Removing **{role.name}** from `{len(members)}` members...')
        count = 0
        for m in members:
            try:
                await m.remove_roles(role)
                count += 1
                await asyncio.sleep(0.5)
            except Exception:
                pass
        await msg.edit(content=f'{self.bot.e.success} Removed **{role.name}** from `{count}` members.')

    @commands.command(name='rolecolor', aliases=['rolecolour'], help='Change the color of a role. Usage: rolecolor @Role #FF5733')
    @commands.has_permissions(manage_roles=True)
    async def rolecolor(self, ctx, role: discord.Role, color: str):
        try:
            color = color.lstrip('#')
            color_int = int(color, 16)
            await role.edit(color=discord.Color(color_int))
            await ctx.success(f'{self.bot.e.success} Changed **{role.name}** color to `#{color.upper()}`.')
        except ValueError:
            await ctx.error('Invalid hex color. Example: `#FF5733`.')

    @commands.command(name='rolemention', help='Toggle whether a role can be mentioned.')
    @commands.has_permissions(manage_roles=True)
    async def rolemention(self, ctx, role: discord.Role):
        new_state = not role.mentionable
        await role.edit(mentionable=new_state)
        state = 'mentionable' if new_state else 'unmentionable'
        await ctx.success(f'{self.bot.e.success} **{role.name}** is now `{state}`.')

    @commands.command(name='note', help='Add a mod note to a user.')
    @commands.has_permissions(manage_messages=True)
    async def note(self, ctx, member: discord.Member, *, content: str):
        key = f'{ctx.guild.id}:{member.id}'
        data = await self.db.find_one('mod_notes', {'_id': key}) or {'_id': key, 'notes': []}
        data['notes'].append({'content': content, 'by': ctx.author.id, 'at': int(datetime.datetime.utcnow().timestamp())})
        await self.db.update_one('mod_notes', {'_id': key}, data, upsert=True)
        await ctx.success(f'{self.bot.e.success} Note added for {member.mention}.')

    @commands.command(name='notes', help='View all mod notes for a user.')
    @commands.has_permissions(manage_messages=True)
    async def notes(self, ctx, member: discord.Member):
        key = f'{ctx.guild.id}:{member.id}'
        data = await self.db.find_one('mod_notes', {'_id': key})
        if not data or not data.get('notes'):
            return await ctx.info(f'No notes for {member.mention}.')
        desc = '\n'.join([
            f'`{i+1}.` <t:{n["at"]}:R> by <@{n["by"]}>: {n["content"]}'
            for i, n in enumerate(data['notes'][-10:])
        ])
        embed = self.bot.embed_manager.generic(description=desc, title=f'Notes for {member}')
        await ctx.send(embed=embed)

    @commands.command(name='clearnotes', help='Clear all mod notes for a user.')
    @commands.has_permissions(manage_guild=True)
    async def clearnotes(self, ctx, member: discord.Member):
        key = f'{ctx.guild.id}:{member.id}'
        await self.db.delete_one('mod_notes', {'_id': key})
        await ctx.success(f'{self.bot.e.success} Cleared all notes for {member.mention}.')

    @commands.command(name='warnlist', help='View all warnings for a user.')
    @commands.has_permissions(manage_messages=True)
    async def warnlist(self, ctx, member: discord.Member):
        data = await self.db.find_one('mod_config', {'_id': ctx.guild.id}) or {}
        cases = data.get('cases', [])
        warns = [c for c in cases if c.get('type') == 'warn' and c.get('user_id') == member.id]
        if not warns:
            return await ctx.info(f'No warnings for {member.mention}.')
        desc = '\n'.join([f'`{i+1}.` <t:{c.get("timestamp", 0)}:R> — {c.get("reason", "No reason")}' for i, c in enumerate(warns[-10:])])
        embed = self.bot.embed_manager.generic(description=desc, title=f'Warnings for {member}')
        await ctx.send(embed=embed)

    @commands.command(name='mutelist', help='List all currently muted members.')
    @commands.has_permissions(manage_messages=True)
    async def mutelist(self, ctx):
        muted = [m for m in ctx.guild.members if m.is_timed_out()]
        if not muted:
            return await ctx.info('No members are currently muted.')
        desc = '\n'.join([f'{m.mention} — until <t:{int(m.timed_out_until.timestamp())}:R>' for m in muted[:20]])
        embed = self.bot.embed_manager.generic(description=desc, title=f'Muted Members ({len(muted)})')
        await ctx.send(embed=embed)

    @commands.command(name='tempmute', help='Temporarily mute a user. Duration: 10m, 2h, 1d.')
    @commands.has_permissions(moderate_members=True)
    async def tempmute(self, ctx, member: discord.Member, duration: str, *, reason: str = 'No reason'):
        match = re.match(r'(\d+)([smhd])', duration.lower())
        if not match:
            return await ctx.error('Invalid duration. Use `10m`, `2h`, `1d`.')
        amount, unit = int(match.group(1)), match.group(2)
        seconds = amount * {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}[unit]
        if seconds > 2419200:
            return await ctx.error('Maximum mute duration is 28 days.')
        until = discord.utils.utcnow() + datetime.timedelta(seconds=seconds)
        await member.timeout(until, reason=f'Tempmute by {ctx.author}: {reason}')
        await ctx.success(f'{self.bot.e.success} Muted {member.mention} for `{duration}`. Reason: {reason}')

    @commands.command(name='stickymsg', aliases=['sticky'], help='Pin a sticky message to a channel.')
    @commands.has_permissions(manage_messages=True)
    async def stickymsg(self, ctx, *, content: str):
        msg = await ctx.send(f'📌 **Sticky Message**\n{content}')
        await self.db.update_one('sticky_messages', {'_id': ctx.channel.id}, {'_id': ctx.channel.id, 'content': content, 'msg_id': msg.id}, upsert=True)
        await ctx.message.delete()

    @commands.command(name='unstickymsg', aliases=['unsticky'], help='Remove the sticky message from this channel.')
    @commands.has_permissions(manage_messages=True)
    async def unstickymsg(self, ctx):
        data = await self.db.find_one('sticky_messages', {'_id': ctx.channel.id})
        if not data:
            return await ctx.error('No sticky message in this channel.')
        try:
            msg = await ctx.channel.fetch_message(data['msg_id'])
            await msg.delete()
        except Exception:
            pass
        await self.db.delete_one('sticky_messages', {'_id': ctx.channel.id})
        await ctx.success(f'{self.bot.e.success} Sticky message removed.')

    @commands.command(name='listpins', help='List all pinned messages in the current channel.')
    async def listpins(self, ctx):
        pins = await ctx.channel.pins()
        if not pins:
            return await ctx.info('No pinned messages in this channel.')
        desc = '\n'.join([f'`{i+1}.` [Jump]({p.jump_url}) by **{p.author}** — {p.content[:60] or "[Attachment]"}' for i, p in enumerate(pins[:20])])
        embed = self.bot.embed_manager.generic(description=desc, title=f'Pinned Messages ({len(pins)})')
        await ctx.send(embed=embed)

    @commands.command(name='pinmsg', help='Pin a message by its ID.')
    @commands.has_permissions(manage_messages=True)
    async def pinmsg(self, ctx, message_id: int):
        try:
            msg = await ctx.channel.fetch_message(message_id)
            await msg.pin()
            await ctx.success(f'{self.bot.e.success} Message pinned.')
        except discord.NotFound:
            await ctx.error('Message not found.')
        except discord.HTTPException:
            await ctx.error('Could not pin — channel may already have 50 pins.')

    @commands.command(name='unpinmsg', help='Unpin a message by its ID.')
    @commands.has_permissions(manage_messages=True)
    async def unpinmsg(self, ctx, message_id: int):
        try:
            msg = await ctx.channel.fetch_message(message_id)
            await msg.unpin()
            await ctx.success(f'{self.bot.e.success} Message unpinned.')
        except discord.NotFound:
            await ctx.error('Message not found.')

    @commands.command(name='say', aliases=['botecho'], help='Make the bot say a message.')
    @commands.has_permissions(manage_messages=True)
    async def say(self, ctx, *, text: str):
        await ctx.message.delete()
        await ctx.send(text)

    @commands.command(name='announcement', aliases=['announce'], help='Send an embedded announcement to a channel.')
    @commands.has_permissions(manage_guild=True)
    async def announcement(self, ctx, channel: discord.TextChannel, *, content: str):
        embed = self.bot.embed_manager.generic(description=content, title='📢 Announcement')
        embed.set_footer(text=f'Announced by {ctx.author}', icon_url=ctx.author.display_avatar.url)
        await channel.send(embed=embed)
        await ctx.success(f'{self.bot.e.success} Announcement sent to {channel.mention}.')

    @commands.command(name='threadcreate', aliases=['thread'], help='Create a public thread on a message.')
    @commands.has_permissions(manage_threads=True)
    async def threadcreate(self, ctx, message_id: int, *, name: str):
        try:
            msg = await ctx.channel.fetch_message(message_id)
            thread = await msg.create_thread(name=name)
            await ctx.success(f'{self.bot.e.success} Thread **{thread.name}** created.')
        except discord.NotFound:
            await ctx.error('Message not found.')
        except Exception as e:
            await ctx.error(str(e))

    @commands.command(name='threadarchive', help='Archive a thread by ID or in the current thread.')
    @commands.has_permissions(manage_threads=True)
    async def threadarchive(self, ctx):
        if not isinstance(ctx.channel, discord.Thread):
            return await ctx.error('Run this inside a thread.')
        await ctx.channel.edit(archived=True)
        await ctx.success(f'{self.bot.e.success} Thread archived.')

    @commands.command(name='memberlist', aliases=['members'], help='List all members in the server.')
    @commands.has_permissions(manage_guild=True)
    async def memberlist(self, ctx):
        members = sorted(ctx.guild.members, key=lambda m: m.joined_at or discord.utils.utcnow())
        desc = '\n'.join([f'`{i+1}.` {m.mention} — joined <t:{int(m.joined_at.timestamp())}:R>' for i, m in enumerate(members[:20])])
        if len(members) > 20:
            desc += f'\n*... and `{len(members) - 20}` more*'
        embed = self.bot.embed_manager.generic(description=desc, title=f'Member List ({len(members)})')
        await ctx.send(embed=embed)

    @commands.command(name='noticeboard', aliases=['notice'], help='Post a formatted notice to a channel.')
    @commands.has_permissions(manage_guild=True)
    async def noticeboard(self, ctx, channel: discord.TextChannel, title: str, *, content: str):
        embed = discord.Embed(title=f'📋 {title}', description=content, color=discord.Color.yellow(), timestamp=discord.utils.utcnow())
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        await channel.send(embed=embed)
        await ctx.success(f'{self.bot.e.success} Notice posted to {channel.mention}.')

    @commands.command(name='rawmsg', help='Show the raw markdown content of a message by ID.')
    async def rawmsg(self, ctx, message_id: int):
        try:
            msg = await ctx.channel.fetch_message(message_id)
            raw = discord.utils.escape_markdown(msg.content) if msg.content else '*[No text content]*'
            await ctx.send(f'```\n{raw[:1990]}\n```')
        except discord.NotFound:
            await ctx.error('Message not found.')

    @commands.command(name='charinfo', help='Get Unicode info about characters in text.')
    async def charinfo(self, ctx, *, text: str):
        if len(text) > 25:
            return await ctx.error('Max 25 characters.')
        lines = []
        for char in text:
            name = f'\\N{{{char}}}'.encode('unicode_escape').decode('ascii')
            lines.append(f'`{char}` — `U+{ord(char):04X}` — {name}')
        embed = self.bot.embed_manager.generic(description='\n'.join(lines), title='Character Info')
        await ctx.send(embed=embed)

    @commands.command(name='emojiinfo', help='Get detailed info about a custom emoji.')
    async def emojiinfo(self, ctx, emoji: discord.Emoji):
        embed = self.bot.embed_manager.generic(
            description=(
                f'**Name:** `{emoji.name}`\n'
                f'**ID:** `{emoji.id}`\n'
                f'**Animated:** `{emoji.animated}`\n'
                f'**Guild:** `{emoji.guild}`\n'
                f'**Created:** <t:{int(emoji.created_at.timestamp())}:R>\n'
                f'**URL:** [Click here]({emoji.url})'
            ),
            title=f'{emoji} Emoji Info'
        )
        embed.set_thumbnail(url=emoji.url)
        await ctx.send(embed=embed)

    @commands.command(name='snowflake', aliases=['sfinfo'], help='Decode a Discord snowflake ID into creation time and info.')
    async def snowflake(self, ctx, snowflake_id: int):
        try:
            timestamp = ((snowflake_id >> 22) + 1420070400000) / 1000
            worker = (snowflake_id & 0x3E0000) >> 17
            process = (snowflake_id & 0x1F000) >> 12
            increment = snowflake_id & 0xFFF
            embed = self.bot.embed_manager.generic(
                description=(
                    f'**Created:** <t:{int(timestamp)}:F> (<t:{int(timestamp)}:R>)\n'
                    f'**Worker ID:** `{worker}`\n'
                    f'**Process ID:** `{process}`\n'
                    f'**Increment:** `{increment}`'
                ),
                title=f'Snowflake: `{snowflake_id}`'
            )
            await ctx.send(embed=embed)
        except Exception:
            await ctx.error('Invalid snowflake ID.')

    @commands.command(name='stickerinfo', help='Get info about a sticker in the server.')
    async def stickerinfo(self, ctx, *, name: str):
        sticker = discord.utils.get(ctx.guild.stickers, name=name)
        if not sticker:
            return await ctx.error(f'Sticker `{name}` not found.')
        embed = self.bot.embed_manager.generic(
            description=(
                f'**Name:** `{sticker.name}`\n'
                f'**ID:** `{sticker.id}`\n'
                f'**Format:** `{sticker.format.name}`\n'
                f'**Created:** <t:{int(sticker.created_at.timestamp())}:R>'
            ),
            title='Sticker Info'
        )
        embed.set_thumbnail(url=sticker.url)
        await ctx.send(embed=embed)

    @commands.command(name='stickers', help='List all stickers in this server.')
    async def stickers(self, ctx):
        if not ctx.guild.stickers:
            return await ctx.info('This server has no stickers.')
        desc = '\n'.join([f'`{i+1}.` **{s.name}** — `{s.format.name}`' for i, s in enumerate(ctx.guild.stickers)])
        embed = self.bot.embed_manager.generic(description=desc, title=f'Server Stickers ({len(ctx.guild.stickers)})')
        await ctx.send(embed=embed)

    @commands.command(name='stealsticker', help='Add a sticker from a message to this server.')
    @commands.has_permissions(manage_emojis_and_stickers=True)
    async def stealsticker(self, ctx, message_id: int = None):
        msg = None
        if message_id:
            try:
                msg = await ctx.channel.fetch_message(message_id)
            except discord.NotFound:
                return await ctx.error('Message not found.')
        else:
            msg = ctx.message.reference and await ctx.channel.fetch_message(ctx.message.reference.message_id)
        if not msg or not msg.stickers:
            return await ctx.error('No sticker found in that message.')
        sticker = msg.stickers[0]
        fetched = await sticker.fetch()
        await ctx.guild.create_sticker(
            name=fetched.name,
            description=fetched.description or fetched.name,
            emoji='⭐',
            file=await fetched.to_file()
        )
        await ctx.success(f'{self.bot.e.success} Sticker **{fetched.name}** added to this server.')

    @commands.command(name='createemoji', aliases=['addemoji2'], help='Create an emoji from a URL or attachment.')
    @commands.has_permissions(manage_emojis=True)
    async def createemoji(self, ctx, name: str, url: str = None):
        if not url and ctx.message.attachments:
            url = ctx.message.attachments[0].url
        if not url:
            return await ctx.error('Provide a URL or attach an image.')
        import aiohttp, io
        async with aiohttp.ClientSession() as s:
            async with s.get(url) as r:
                if r.status != 200:
                    return await ctx.error('Failed to fetch image.')
                data = await r.read()
        emoji = await ctx.guild.create_custom_emoji(name=name, image=data)
        await ctx.success(f'{self.bot.e.success} Created emoji {emoji}.')

    @commands.command(name='createsticker', help='Create a sticker from an attachment (PNG/APNG).')
    @commands.has_permissions(manage_emojis_and_stickers=True)
    async def createsticker(self, ctx, name: str, *, description: str = None):
        if not ctx.message.attachments:
            return await ctx.error('Attach a PNG or APNG image.')
        attachment = ctx.message.attachments[0]
        sticker_file = await attachment.to_file()
        sticker = await ctx.guild.create_sticker(
            name=name,
            description=description or name,
            emoji='⭐',
            file=sticker_file
        )
        await ctx.success(f'{self.bot.e.success} Created sticker **{sticker.name}**.')

    @commands.command(name='listwebhooks', aliases=['webhooks'], help='List all webhooks in the server.')
    @commands.has_permissions(manage_webhooks=True)
    async def listwebhooks(self, ctx):
        webhooks = await ctx.guild.webhooks()
        if not webhooks:
            return await ctx.info('No webhooks found.')
        desc = '\n'.join([f'`{i+1}.` **{w.name}** — {w.channel.mention if w.channel else "Unknown"}' for i, w in enumerate(webhooks[:20])])
        embed = self.bot.embed_manager.generic(description=desc, title=f'Webhooks ({len(webhooks)})')
        await ctx.send(embed=embed)

    @commands.command(name='createwebhook', help='Create a webhook in the current channel.')
    @commands.has_permissions(manage_webhooks=True)
    async def createwebhook(self, ctx, *, name: str):
        webhook = await ctx.channel.create_webhook(name=name)
        await ctx.success(f'{self.bot.e.success} Webhook **{name}** created.\nURL: ||{webhook.url}||')

    @commands.command(name='deletewebhook', help='Delete a webhook by its URL.')
    @commands.has_permissions(manage_webhooks=True)
    async def deletewebhook(self, ctx, url: str):
        try:
            webhook = await self.bot.fetch_webhook_with_token(*url.split('/api/webhooks/')[1].split('/'))
            await webhook.delete()
            await ctx.success(f'{self.bot.e.success} Webhook deleted.')
        except Exception:
            await ctx.error('Invalid webhook URL or already deleted.')

    @commands.command(name='boostedfor', help='Check how long a member has been boosting the server.')
    async def boostedfor(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        if not member.premium_since:
            return await ctx.info(f'{member.mention} is not boosting this server.')
        delta = discord.utils.utcnow() - member.premium_since
        days = delta.days
        await ctx.success(f'{member.mention} has been boosting for **{days} day{"s" if days != 1 else ""}**.')

    @commands.command(name='boostcount', help='Show the current boost count and level of the server.')
    async def boostcount(self, ctx):
        guild = ctx.guild
        embed = self.bot.embed_manager.generic(
            description=(
                f'**Boost Level:** `{guild.premium_tier}`\n'
                f'**Total Boosts:** `{guild.premium_subscription_count}`\n'
                f'**Boosters:** `{len(guild.premium_subscribers)}`'
            ),
            title=f'{self.bot.e.success} Boost Stats'
        )
        await ctx.send(embed=embed)

    @commands.command(name='servertemplate', aliases=['template'], help='Get the server template link if one exists.')
    @commands.has_permissions(manage_guild=True)
    async def servertemplate(self, ctx):
        templates = await ctx.guild.templates()
        if not templates:
            return await ctx.info('This server has no templates.')
        t = templates[0]
        embed = self.bot.embed_manager.generic(
            description=f'**Name:** {t.name}\n**Uses:** `{t.usage_count}`\n**URL:** {t.url}',
            title='Server Template'
        )
        await ctx.send(embed=embed)

    @commands.command(name='clearchannel', aliases=['purgeall'], help='Delete all messages in a channel by recreating it.')
    @commands.has_permissions(manage_channels=True)
    async def clearchannel(self, ctx):
        channel = ctx.channel
        pos = channel.position
        new_channel = await channel.clone(reason=f'Clearchannel by {ctx.author}')
        await new_channel.edit(position=pos)
        await channel.delete()
        await new_channel.send(f'{self.bot.e.success} Channel cleared by {ctx.author.mention}.', delete_after=5)

    @commands.command(name='tts', help='Send a text-to-speech message.')
    @commands.has_permissions(send_tts_messages=True)
    async def tts(self, ctx, *, text: str):
        await ctx.message.delete()
        await ctx.send(text, tts=True)

    @commands.command(name='prefixes', help='Show all active prefixes for this server.')
    async def prefixes(self, ctx):
        prefixes = await self.bot.prefix_manager.get_prefixes(ctx.guild.id)
        desc = '\n'.join([f'`{p}`' for p in prefixes])
        embed = self.bot.embed_manager.generic(description=desc, title='Active Prefixes')
        await ctx.send(embed=embed)

    @commands.command(name='resetprefix', help='Reset all server prefixes to the default.')
    @commands.has_permissions(manage_guild=True)
    async def resetprefix(self, ctx):
        await self.bot.prefix_manager.reset_prefix(ctx.guild.id)
        await ctx.success(f'{self.bot.e.success} Prefix reset to default.')

    @commands.command(name='memberinfo', aliases=['minfo'], help='Show detailed info about a member.')
    async def memberinfo(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        roles = [r.mention for r in reversed(member.roles) if r != ctx.guild.default_role]
        embed = self.bot.embed_manager.generic(
            description=(
                f'**ID:** `{member.id}`\n'
                f'**Nickname:** `{member.nick or "None"}`\n'
                f'**Account Created:** <t:{int(member.created_at.timestamp())}:R>\n'
                f'**Joined Server:** <t:{int(member.joined_at.timestamp())}:R>\n'
                f'**Boosting Since:** {f"<t:{int(member.premium_since.timestamp())}:R>" if member.premium_since else "`Not boosting`"}\n'
                f'**Bot:** `{member.bot}`\n'
                f'**Top Role:** {member.top_role.mention}\n'
                f'**Roles ({len(roles)}):** {", ".join(roles[:10]) or "None"}'
            ),
            title=str(member)
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name='channelinfo2', aliases=['cinfo2'], help='Show detailed info about a channel.')
    async def channelinfo(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        embed = self.bot.embed_manager.generic(
            description=(
                f'**ID:** `{channel.id}`\n'
                f'**Type:** `{channel.type}`\n'
                f'**Category:** `{channel.category}`\n'
                f'**Topic:** {channel.topic or "`None`"}\n'
                f'**NSFW:** `{channel.is_nsfw()}`\n'
                f'**Slowmode:** `{channel.slowmode_delay}s`\n'
                f'**Created:** <t:{int(channel.created_at.timestamp())}:R>\n'
                f'**Position:** `{channel.position}`'
            ),
            title=f'#{channel.name}'
        )
        await ctx.send(embed=embed)

    @commands.command(name='roleinfo2', aliases=['rinfo2'], help='Show detailed info about a role.')
    async def roleinfo(self, ctx, role: discord.Role):
        perms = [p.replace('_', ' ').title() for p, v in role.permissions if v]
        embed = self.bot.embed_manager.generic(
            description=(
                f'**ID:** `{role.id}`\n'
                f'**Color:** `{str(role.color)}`\n'
                f'**Members:** `{len(role.members)}`\n'
                f'**Mentionable:** `{role.mentionable}`\n'
                f'**Hoisted:** `{role.hoist}`\n'
                f'**Managed:** `{role.managed}`\n'
                f'**Created:** <t:{int(role.created_at.timestamp())}:R>\n'
                f'**Key Perms:** {", ".join(perms[:8]) or "None"}'
            ),
            title=f'@{role.name}'
        )
        embed.color = role.color
        await ctx.send(embed=embed)

    @commands.command(name='serveravatar', aliases=['sav'], help='Show the server avatar of a member if they have one.')
    async def serveravatar(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        if not member.guild_avatar:
            return await ctx.info(f'{member.mention} has no server avatar.')
        embed = self.bot.embed_manager.generic(description=f'[Download]({member.guild_avatar.url})', title=f'{member}\'s Server Avatar')
        embed.set_image(url=member.guild_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name='botavatar', help='Show the bot\'s current avatar.')
    async def botavatar(self, ctx):
        embed = self.bot.embed_manager.generic(description=f'[Download]({self.bot.user.display_avatar.url})', title=f'{self.bot.user.name}\'s Avatar')
        embed.set_image(url=self.bot.user.display_avatar.url)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ModTools(bot))
