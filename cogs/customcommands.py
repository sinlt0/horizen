import discord
from discord.ext import commands, tasks
import re
import asyncio
import random
import time

TRIGGER_COMMAND    = 'command'
TRIGGER_STARTS     = 'starts_with'
TRIGGER_CONTAINS   = 'contains'
TRIGGER_REGEX      = 'regex'
TRIGGER_EXACT      = 'exact_match'
TRIGGER_REACTION   = 'reaction'
TRIGGER_NONE       = 'none'
TRIGGER_INTERVAL   = 'interval'
TRIGGER_MSG_EDIT   = 'message_edit'

ALL_TRIGGER_TYPES  = [
    TRIGGER_COMMAND, TRIGGER_STARTS, TRIGGER_CONTAINS,
    TRIGGER_REGEX, TRIGGER_EXACT, TRIGGER_REACTION,
    TRIGGER_NONE, TRIGGER_INTERVAL, TRIGGER_MSG_EDIT,
]

ACTION_PATTERN = re.compile(
    r'\{('
    r'addrole|removerole|addroleto|removerolefrom'
    r'|togglerole'
    r'|dm|dmmember'
    r'|deleteafter|silentdelete|deletetrigger'
    r'|react|reactremove'
    r'|sendchannel|senddm|sendreply|sendephemeral'
    r'|kick|ban|softban|unban|timeout|untimeout'
    r'|mute|unmute'
    r'|setnick|resetnick'
    r'|createchannel|deletechannel|lockchannel|unlockchannel|hidechannel|showchannel'
    r'|createrole|deleterole|editrole'
    r'|editmessage|pinchannel|unpinchannel'
    r'|setembed|settitle|setcolor|setfooter|setthumbnail|setimage|addfield'
    r'|log|warn|clearwarns'
    r'|sleep|noresponse'
    r'|hasrole|hasperms|memberexists'
    r'):([^}]*)\}',
    re.IGNORECASE
)
VAR_PATTERN = re.compile(r'\{(\w+(?:\d+)?)\}')


class CCGroup:
    def __init__(self, data):
        self.name = data.get('name', 'Unnamed')
        self.allowed_channels = data.get('allowed_channels', [])
        self.denied_channels = data.get('denied_channels', [])
        self.allowed_roles = data.get('allowed_roles', [])
        self.denied_roles = data.get('denied_roles', [])


class CustomCommand:
    def __init__(self, trigger, data):
        self.trigger = trigger
        self.trigger_type = data.get('trigger_type', TRIGGER_COMMAND)
        self.responses = data.get('responses', [data.get('response', '')])
        self.case_sensitive = data.get('case_sensitive', False)
        self.embed = data.get('embed', False)
        self.embed_color = data.get('embed_color', None)
        self.embed_title = data.get('embed_title', None)
        self.delete_trigger = data.get('delete_trigger', False)
        self.delete_trigger_after = data.get('delete_trigger_after', 0)
        self.delete_response_after = data.get('delete_response_after', 0)
        self.cooldown = data.get('cooldown', 0)
        self.cooldown_type = data.get('cooldown_type', 'user')
        self.allowed_channels = data.get('allowed_channels', [])
        self.denied_channels = data.get('denied_channels', [])
        self.allowed_roles = data.get('allowed_roles', [])
        self.denied_roles = data.get('denied_roles', [])
        self.group = data.get('group', None)
        self.enabled = data.get('enabled', True)
        self.uses = data.get('uses', 0)
        self.description = data.get('description', '')
        self.numeric_id = data.get('numeric_id', 0)
        self.reaction_emoji = data.get('reaction_emoji', '')
        self.reaction_message_id = data.get('reaction_message_id', None)
        self.interval_minutes = data.get('interval_minutes', 0)
        self.interval_channel = data.get('interval_channel', None)
        self.interval_next_run = data.get('interval_next_run', 0)
        self.on_edit = data.get('on_edit', False)
        self.run_on_edit = data.get('run_on_edit', False)
        self._cooldown_cache = {}

    def to_dict(self):
        return {
            'trigger_type': self.trigger_type,
            'responses': self.responses,
            'case_sensitive': self.case_sensitive,
            'embed': self.embed,
            'embed_color': self.embed_color,
            'embed_title': self.embed_title,
            'delete_trigger': self.delete_trigger,
            'delete_trigger_after': self.delete_trigger_after,
            'delete_response_after': self.delete_response_after,
            'cooldown': self.cooldown,
            'cooldown_type': self.cooldown_type,
            'allowed_channels': self.allowed_channels,
            'denied_channels': self.denied_channels,
            'allowed_roles': self.allowed_roles,
            'denied_roles': self.denied_roles,
            'group': self.group,
            'enabled': self.enabled,
            'uses': self.uses,
            'description': self.description,
            'numeric_id': self.numeric_id,
            'reaction_emoji': self.reaction_emoji,
            'reaction_message_id': self.reaction_message_id,
            'interval_minutes': self.interval_minutes,
            'interval_channel': self.interval_channel,
            'interval_next_run': self.interval_next_run,
            'on_edit': self.on_edit,
            'run_on_edit': self.run_on_edit,
        }

    def matches(self, content, prefix_stripped):
        t = self.trigger if self.case_sensitive else self.trigger.lower()
        c = content if self.case_sensitive else content.lower()
        p = prefix_stripped if self.case_sensitive else prefix_stripped.lower()

        if self.trigger_type == TRIGGER_COMMAND:
            parts = p.split()
            return bool(parts) and parts[0] == t
        elif self.trigger_type == TRIGGER_STARTS:
            return c.startswith(t)
        elif self.trigger_type == TRIGGER_CONTAINS:
            return t in c
        elif self.trigger_type == TRIGGER_EXACT:
            return c == t
        elif self.trigger_type == TRIGGER_REGEX:
            try:
                flags = 0 if self.case_sensitive else re.IGNORECASE
                return bool(re.search(self.trigger, content, flags))
            except re.error:
                return False
        return False

    def check_cooldown(self, user_id):
        now = time.time()
        key = user_id if self.cooldown_type == 'user' else 'global'
        last = self._cooldown_cache.get(key, 0)
        if now - last < self.cooldown:
            return self.cooldown - (now - last)
        return 0

    def apply_cooldown(self, user_id):
        key = user_id if self.cooldown_type == 'user' else 'global'
        self._cooldown_cache[key] = time.time()

    def check_restrictions(self, member, channel, group=None):
        member_role_ids = [r.id for r in member.roles]

        denied_roles = list(self.denied_roles)
        allowed_roles = list(self.allowed_roles)
        denied_channels = list(self.denied_channels)
        allowed_channels = list(self.allowed_channels)

        if group:
            denied_roles += group.denied_roles
            allowed_roles += group.allowed_roles
            denied_channels += group.denied_channels
            allowed_channels += group.allowed_channels

        if any(r in member_role_ids for r in denied_roles):
            return False, 'You have a denied role for this command.'
        if denied_channels and channel.id in denied_channels:
            return False, 'This command is disabled in this channel.'
        if allowed_roles and not any(r in member_role_ids for r in allowed_roles):
            return False, 'You need a required role to use this command.'
        if allowed_channels and channel.id not in allowed_channels:
            return False, 'This command is not allowed in this channel.'

        return True, None

    def get_response(self):
        responses = [r for r in self.responses if r.strip()]
        if not responses:
            return ''
        return random.choice(responses)


def build_variables(message, args):
    member = message.author
    guild = message.guild
    all_args = ' '.join(args)
    var_map = {
        'user': member.mention,
        'username': member.display_name,
        'userid': str(member.id),
        'usertag': str(member),
        'useravatar': member.display_avatar.url,
        'server': guild.name,
        'serverid': str(guild.id),
        'servericon': guild.icon.url if guild.icon else '',
        'membercount': str(guild.member_count),
        'channel': message.channel.mention,
        'channelname': message.channel.name,
        'channelid': str(message.channel.id),
        'args': all_args,
        'argscount': str(len(args)),
        'msgid': str(message.id),
        'msglink': message.jump_url,
        'timestamp': f'<t:{int(message.created_at.timestamp())}:f>',
        'prefix': '!',
    }
    for i, arg in enumerate(args, 1):
        var_map[f'arg{i}'] = arg
    return var_map


def apply_conditionals(response, var_map):
    import re as _re
    def eval_condition(cond):
        cond = cond.strip()
        parts = cond.split()
        if len(parts) == 3:
            left = var_map.get(parts[0].strip('{}'), parts[0])
            op = parts[1]
            right = parts[2]
            if op == '==': return left == right
            if op == '!=': return left != right
            if op in ('>', '>=', '<', '<='):
                try:
                    l, r = float(left), float(right)
                    if op == '>': return l > r
                    if op == '>=': return l >= r
                    if op == '<': return l < r
                    if op == '<=': return l <= r
                except Exception:
                    pass
        if cond.startswith('hasarg '):
            idx = cond[7:].strip()
            try:
                return f'arg{idx}' in var_map and bool(var_map[f'arg{idx}'])
            except Exception:
                return False
        return bool(cond)

    pattern = _re.compile(
        r'\{if ([^}]+)\}(.*?)(?:\{else\}(.*?))?\{end\}',
        _re.DOTALL
    )
    def replacer(m):
        cond_str, if_body, else_body = m.group(1), m.group(2), m.group(3) or ''
        return if_body.strip() if eval_condition(cond_str) else else_body.strip()

    for _ in range(5):
        new = pattern.sub(replacer, response)
        if new == response:
            break
        response = new
    return response


def apply_random_blocks(response):
    import re as _re
    pattern = _re.compile(r'\{random\}(.*?)\{endrandom\}', _re.DOTALL)
    def replacer(m):
        options = [o.strip() for o in m.group(1).split('{|}') if o.strip()]
        return random.choice(options) if options else ''
    return pattern.sub(replacer, response)


def _resolve_role(guild, ref):
    ref = ref.strip().strip('<@&>').strip()
    if ref.isdigit():
        return guild.get_role(int(ref))
    return discord.utils.get(guild.roles, name=ref)


def _resolve_channel(guild, ref):
    ref = ref.strip().strip('<#>').strip()
    if ref.isdigit():
        return guild.get_channel(int(ref))
    return discord.utils.get(guild.text_channels, name=ref)


def _resolve_member(guild, ref):
    ref = ref.strip().strip('<@!>').strip()
    if ref.isdigit():
        return guild.get_member(int(ref))
    return discord.utils.find(lambda m: m.display_name.lower() == ref.lower() or str(m).lower() == ref.lower(), guild.members)


class ActionContext:
    def __init__(self, message, bot):
        self.message = message
        self.bot = bot
        self.guild = message.guild if message else None
        self.author = message.author if message else None
        self.channel = message.channel if message else None
        self.delete_after = None
        self.no_response = False
        self.channel_sends = []
        self.embed_data = {}
        self.log_lines = []


async def process_actions(response, message, bot):
    if not message or not message.guild:
        clean = ACTION_PATTERN.sub('', response).strip()
        return clean, None, []

    ctx = ActionContext(message, bot)
    guild = ctx.guild
    author = ctx.author

    for match in ACTION_PATTERN.finditer(response):
        action = match.group(1).lower()
        value = match.group(2).strip()

        try:

            if action == 'addrole':
                role = _resolve_role(guild, value)
                if role:
                    await author.add_roles(role, reason='Custom Command')

            elif action == 'removerole':
                role = _resolve_role(guild, value)
                if role:
                    await author.remove_roles(role, reason='Custom Command')

            elif action == 'togglerole':
                role = _resolve_role(guild, value)
                if role:
                    if role in author.roles:
                        await author.remove_roles(role, reason='Custom Command Toggle')
                    else:
                        await author.add_roles(role, reason='Custom Command Toggle')

            elif action in ('addroleto', 'removerolefrom'):
                parts = value.split('|', 1)
                if len(parts) == 2:
                    target = _resolve_member(guild, parts[0])
                    role = _resolve_role(guild, parts[1])
                    if target and role:
                        if action == 'addroleto':
                            await target.add_roles(role, reason='Custom Command')
                        else:
                            await target.remove_roles(role, reason='Custom Command')

            elif action in ('dm', 'dmmember'):
                parts = value.split('|', 1)
                if len(parts) == 2:
                    target = _resolve_member(guild, parts[0])
                    if target:
                        await target.send(parts[1].strip())
                else:
                    await author.send(value)

            elif action == 'sendreply':
                if message:
                    await message.reply(value, mention_author=False)

            elif action == 'sendchannel':
                parts = value.split('|', 1)
                if len(parts) == 2:
                    ch = _resolve_channel(guild, parts[0])
                    if ch:
                        ctx.channel_sends.append((ch, parts[1].strip()))

            elif action == 'deleteafter':
                ctx.delete_after = max(0, int(value))

            elif action in ('silentdelete', 'deletetrigger'):
                await message.delete()

            elif action == 'react':
                for emoji in [e.strip() for e in value.split(',')][:5]:
                    try:
                        await message.add_reaction(emoji)
                    except Exception:
                        pass

            elif action == 'reactremove':
                for emoji in [e.strip() for e in value.split(',')][:5]:
                    try:
                        await message.clear_reaction(emoji)
                    except Exception:
                        pass

            elif action == 'noresponse':
                ctx.no_response = True

            elif action == 'sleep':
                secs = min(60, max(0, int(value)))
                await asyncio.sleep(secs)

            elif action == 'kick':
                parts = value.split('|', 1)
                target = _resolve_member(guild, parts[0]) if '|' in value else author
                reason = parts[1].strip() if len(parts) > 1 else 'Custom Command'
                if guild.me.guild_permissions.kick_members:
                    await guild.kick(target, reason=reason)

            elif action == 'ban':
                parts = value.split('|', 1)
                target = _resolve_member(guild, parts[0]) if '|' in value else author
                reason = parts[1].strip() if len(parts) > 1 else 'Custom Command'
                if guild.me.guild_permissions.ban_members:
                    await guild.ban(target, reason=reason, delete_message_days=0)

            elif action == 'softban':
                parts = value.split('|', 1)
                target = _resolve_member(guild, parts[0]) if '|' in value else author
                reason = parts[1].strip() if len(parts) > 1 else 'Custom Command'
                if guild.me.guild_permissions.ban_members:
                    await guild.ban(target, reason=reason, delete_message_days=7)
                    await guild.unban(target, reason='Softban auto-unban')

            elif action == 'unban':
                try:
                    user = await bot.fetch_user(int(value.strip()))
                    if guild.me.guild_permissions.ban_members:
                        await guild.unban(user, reason='Custom Command')
                except Exception:
                    pass

            elif action in ('timeout', 'mute'):
                parts = value.split('|', 1)
                target_ref = parts[0].strip()
                duration_str = parts[1].strip() if len(parts) > 1 else '10m'
                target = _resolve_member(guild, target_ref)
                if target and guild.me.guild_permissions.moderate_members:
                    import re as _re
                    m = _re.match(r'(\d+)([smhd])', duration_str.lower())
                    if m:
                        secs = int(m.group(1)) * {'s':1,'m':60,'h':3600,'d':86400}[m.group(2)]
                        until = discord.utils.utcnow() + discord.utils.utcnow().replace() - discord.utils.utcnow() + __import__('datetime').timedelta(seconds=secs)
                        until = discord.utils.utcnow() + __import__('datetime').timedelta(seconds=secs)
                        await target.timeout(until, reason='Custom Command')

            elif action in ('untimeout', 'unmute'):
                target = _resolve_member(guild, value)
                if target and guild.me.guild_permissions.moderate_members:
                    await target.timeout(None, reason='Custom Command')

            elif action == 'setnick':
                parts = value.split('|', 1)
                target = _resolve_member(guild, parts[0]) if len(parts) > 1 else author
                nick = parts[1].strip() if len(parts) > 1 else parts[0].strip()
                if guild.me.guild_permissions.manage_nicknames:
                    await target.edit(nick=nick[:32] or None)

            elif action == 'resetnick':
                target = _resolve_member(guild, value) if value else author
                if guild.me.guild_permissions.manage_nicknames:
                    await target.edit(nick=None)

            elif action == 'createchannel':
                parts = value.split('|')
                name = parts[0].strip()
                cat_ref = parts[1].strip() if len(parts) > 1 else None
                category = None
                if cat_ref:
                    category = discord.utils.get(guild.categories, name=cat_ref) or                                (guild.get_channel(int(cat_ref)) if cat_ref.isdigit() else None)
                if guild.me.guild_permissions.manage_channels:
                    await guild.create_text_channel(name, category=category, reason='Custom Command')

            elif action == 'deletechannel':
                ch = _resolve_channel(guild, value)
                if ch and guild.me.guild_permissions.manage_channels:
                    await ch.delete(reason='Custom Command')

            elif action == 'lockchannel':
                ch = _resolve_channel(guild, value) if value else ctx.channel
                if ch and guild.me.guild_permissions.manage_channels:
                    ow = ch.overwrites_for(guild.default_role)
                    ow.send_messages = False
                    await ch.set_permissions(guild.default_role, overwrite=ow)

            elif action == 'unlockchannel':
                ch = _resolve_channel(guild, value) if value else ctx.channel
                if ch and guild.me.guild_permissions.manage_channels:
                    ow = ch.overwrites_for(guild.default_role)
                    ow.send_messages = None
                    await ch.set_permissions(guild.default_role, overwrite=ow)

            elif action == 'hidechannel':
                ch = _resolve_channel(guild, value) if value else ctx.channel
                if ch and guild.me.guild_permissions.manage_channels:
                    ow = ch.overwrites_for(guild.default_role)
                    ow.view_channel = False
                    await ch.set_permissions(guild.default_role, overwrite=ow)

            elif action == 'showchannel':
                ch = _resolve_channel(guild, value) if value else ctx.channel
                if ch and guild.me.guild_permissions.manage_channels:
                    ow = ch.overwrites_for(guild.default_role)
                    ow.view_channel = None
                    await ch.set_permissions(guild.default_role, overwrite=ow)

            elif action == 'createrole':
                parts = value.split('|')
                name = parts[0].strip()
                color_str = parts[1].strip() if len(parts) > 1 else None
                color = discord.Color(int(color_str.lstrip('#'), 16)) if color_str else discord.Color.default()
                if guild.me.guild_permissions.manage_roles:
                    await guild.create_role(name=name, color=color, reason='Custom Command')

            elif action == 'deleterole':
                role = _resolve_role(guild, value)
                if role and guild.me.guild_permissions.manage_roles:
                    await role.delete(reason='Custom Command')

            elif action == 'editrole':
                parts = value.split('|')
                if len(parts) >= 2:
                    role = _resolve_role(guild, parts[0])
                    prop, val = parts[1].strip().split('=', 1) if '=' in parts[1] else (parts[1].strip(), '')
                    prop = prop.strip().lower()
                    val = val.strip()
                    if role and guild.me.guild_permissions.manage_roles:
                        if prop == 'name':
                            await role.edit(name=val)
                        elif prop == 'color':
                            await role.edit(color=discord.Color(int(val.lstrip('#'), 16)))
                        elif prop == 'hoist':
                            await role.edit(hoist=val.lower() in ('true','yes','1'))
                        elif prop == 'mentionable':
                            await role.edit(mentionable=val.lower() in ('true','yes','1'))

            elif action == 'warn':
                parts = value.split('|', 1)
                target = _resolve_member(guild, parts[0])
                reason = parts[1].strip() if len(parts) > 1 else 'Custom Command warn'
                if target:
                    mod_cog = bot.get_cog('Moderation')
                    if mod_cog and hasattr(mod_cog, 'add_warn'):
                        await mod_cog.add_warn(guild, target, author, reason)

            elif action == 'log':
                parts = value.split('|', 1)
                if len(parts) == 2:
                    ch = _resolve_channel(guild, parts[0])
                    if ch:
                        embed = discord.Embed(description=parts[1].strip(), color=discord.Color.blurple(), timestamp=discord.utils.utcnow())
                        embed.set_author(name=str(author), icon_url=author.display_avatar.url)
                        await ch.send(embed=embed)

            elif action == 'settitle':
                ctx.embed_data['title'] = value
            elif action == 'setcolor':
                try:
                    ctx.embed_data['color'] = discord.Color(int(value.lstrip('#'), 16))
                except Exception:
                    pass
            elif action == 'setfooter':
                ctx.embed_data['footer'] = value
            elif action == 'setthumbnail':
                ctx.embed_data['thumbnail'] = value
            elif action == 'setimage':
                ctx.embed_data['image'] = value
            elif action == 'addfield':
                parts = value.split('|', 2)
                if len(parts) >= 2:
                    inline = parts[2].strip().lower() in ('true','yes','1') if len(parts) > 2 else False
                    ctx.embed_data.setdefault('fields', []).append({
                        'name': parts[0].strip(),
                        'value': parts[1].strip(),
                        'inline': inline
                    })

        except discord.Forbidden:
            pass
        except Exception as e:
            print(f'CC action error [{action}]: {e}')

    clean_response = ACTION_PATTERN.sub('', response).strip()

    if ctx.no_response:
        clean_response = ''

    return clean_response, ctx.delete_after, ctx.channel_sends, ctx.embed_data



def _build_response_embed(cmd, clean_response, embed_data, bot):
    color = embed_data.get('color') or (discord.Color(int(cmd.embed_color.lstrip('#'), 16)) if cmd.embed_color else bot.embed_manager.color)
    embed = discord.Embed(
        title=embed_data.get('title') or cmd.embed_title,
        description=clean_response or None,
        color=color
    )
    if 'footer' in embed_data:
        embed.set_footer(text=embed_data['footer'])
    if 'thumbnail' in embed_data:
        embed.set_thumbnail(url=embed_data['thumbnail'])
    if 'image' in embed_data:
        embed.set_image(url=embed_data['image'])
    for field in embed_data.get('fields', []):
        embed.add_field(name=field['name'], value=field['value'], inline=field.get('inline', False))
    return embed

class CustomCommands(commands.Cog):
    category = 'config'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager
        self._cache = {}
        self._groups = {}

    async def cog_load(self):
        configs = await self.db.find('custom_commands', {})
        for c in configs:
            gid = c['_id']
            raw_cmds = c.get('commands', {})
            self._cache[gid] = {
                trigger: CustomCommand(trigger, data)
                for trigger, data in raw_cmds.items()
            }
            raw_groups = c.get('groups', {})
            self._groups[gid] = {
                name: CCGroup(data)
                for name, data in raw_groups.items()
            }
        self._interval_loop.start()
        self._next_id = max(
            (cmd.numeric_id for guild in self._cache.values() for cmd in guild.values()),
            default=0
        ) + 1

    def _alloc_id(self):
        nid = self._next_id
        self._next_id += 1
        return nid

    def cog_unload(self):
        self._interval_loop.cancel()

    def _get_commands(self, guild_id):
        return self._cache.get(guild_id, {})

    async def _save(self, guild_id):
        cmds = {t: cmd.to_dict() for t, cmd in self._cache.get(guild_id, {}).items()}
        groups = {}
        for name, g in self._groups.get(guild_id, {}).items():
            groups[name] = {
                'name': g.name,
                'allowed_channels': g.allowed_channels,
                'denied_channels': g.denied_channels,
                'allowed_roles': g.allowed_roles,
                'denied_roles': g.denied_roles,
            }
        await self.db.update_one('custom_commands', {'_id': guild_id},
                                 {'_id': guild_id, 'commands': cmds, 'groups': groups}, upsert=True)

    @tasks.loop(minutes=1)
    async def _interval_loop(self):
        import time as _time
        now = _time.time()
        for guild_id, cmds in self._cache.items():
            guild = self.bot.get_guild(guild_id)
            if not guild:
                continue
            for trigger, cmd in cmds.items():
                if cmd.trigger_type != TRIGGER_INTERVAL or not cmd.enabled:
                    continue
                if not cmd.interval_minutes or not cmd.interval_channel:
                    continue
                if now < cmd.interval_next_run:
                    continue
                channel = guild.get_channel(cmd.interval_channel)
                if not channel:
                    continue
                var_map = {
                    'server': guild.name, 'serverid': str(guild.id),
                    'membercount': str(guild.member_count),
                    'channel': channel.mention, 'channelname': channel.name,
                    'channelid': str(channel.id),
                }
                raw = cmd.get_response()
                raw = apply_conditionals(raw, var_map)
                raw = apply_random_blocks(raw)
                for k, v in var_map.items():
                    raw = raw.replace(f'{{{k}}}', v)
                clean, _, channel_sends, embed_data = await process_actions(raw, None, self.bot)
                if clean or embed_data:
                    try:
                        if cmd.embed or embed_data:
                            embed = _build_response_embed(cmd, clean, embed_data, self.bot)
                            await channel.send(embed=embed)
                        else:
                            await channel.send(clean)
                    except Exception as e:
                        print(f'CC interval error for {trigger}: {e}')
                cmd.interval_next_run = now + (cmd.interval_minutes * 60)
                cmd.uses += 1
                await self._save(guild_id)

    @_interval_loop.before_loop
    async def _before_interval(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.member and payload.member.bot:
            return
        if not payload.guild_id:
            return
        cmds = self._get_commands(payload.guild_id)
        for trigger, cmd in cmds.items():
            if cmd.trigger_type != TRIGGER_REACTION or not cmd.enabled:
                continue
            if cmd.reaction_emoji and str(payload.emoji) != cmd.reaction_emoji:
                continue
            if cmd.reaction_message_id and payload.message_id != cmd.reaction_message_id:
                continue
            guild = self.bot.get_guild(payload.guild_id)
            if not guild:
                continue
            member = payload.member or guild.get_member(payload.user_id)
            if not member:
                continue
            channel = guild.get_channel(payload.channel_id)
            if not channel:
                continue
            group = self._groups.get(guild.id, {}).get(cmd.group) if cmd.group else None
            ok, _ = cmd.check_restrictions(member, channel, group)
            if not ok:
                continue
            remaining = cmd.check_cooldown(member.id)
            if remaining > 0:
                continue
            cmd.apply_cooldown(member.id)
            cmd.uses += 1
            var_map = {
                'user': member.mention, 'username': member.display_name,
                'userid': str(member.id), 'server': guild.name,
                'serverid': str(guild.id), 'membercount': str(guild.member_count),
                'channel': channel.mention, 'channelname': channel.name,
                'channelid': str(channel.id), 'emoji': str(payload.emoji),
                'msgid': str(payload.message_id),
            }
            raw = cmd.get_response()
            raw = apply_conditionals(raw, var_map)
            raw = apply_random_blocks(raw)
            for k, v in var_map.items():
                raw = raw.replace(f'{{{k}}}', v)
            clean, delete_after, channel_sends, embed_data = await process_actions(raw, None, self.bot)
            if clean or embed_data:
                try:
                    da = delete_after or cmd.delete_response_after or None
                    if cmd.embed or embed_data:
                        embed = _build_response_embed(cmd, clean, embed_data, self.bot)
                        await channel.send(embed=embed, delete_after=da)
                    else:
                        await channel.send(clean, delete_after=da)
                except Exception:
                    pass
            for ch, msg in channel_sends:
                try:
                    await ch.send(msg)
                except Exception:
                    pass
            await self._save(guild.id)
            break

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if after.author.bot or not after.guild:
            return
        cmds = self._get_commands(after.guild.id)
        for trigger, cmd in cmds.items():
            if cmd.trigger_type != TRIGGER_MSG_EDIT or not cmd.enabled:
                continue
            if not cmd.matches(after.content, after.content):
                continue
            channel = after.channel
            member = after.author
            group = self._groups.get(after.guild.id, {}).get(cmd.group) if cmd.group else None
            ok, reason = cmd.check_restrictions(member, channel, group)
            if not ok:
                continue
            remaining = cmd.check_cooldown(member.id)
            if remaining > 0:
                continue
            cmd.apply_cooldown(member.id)
            cmd.uses += 1
            args = after.content.split()[1:]
            var_map = build_variables(after, args)
            var_map['before'] = before.content
            raw = cmd.get_response()
            raw = apply_conditionals(raw, var_map)
            raw = apply_random_blocks(raw)
            for k, v in var_map.items():
                raw = raw.replace(f'{{{k}}}', v)
            clean, delete_after, channel_sends, embed_data = await process_actions(raw, after, self.bot)
            if clean or embed_data:
                try:
                    da = delete_after or cmd.delete_response_after or None
                    if cmd.embed or embed_data:
                        embed = _build_response_embed(cmd, clean, embed_data, self.bot)
                        await channel.send(embed=embed, delete_after=da)
                    else:
                        await channel.send(clean, delete_after=da)
                except Exception:
                    pass
            await self._save(after.guild.id)
            break

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return

        cmds = self._get_commands(message.guild.id)
        if not cmds:
            return

        prefixes = await self.bot.prefix_manager.get_prefixes(message.guild.id)
        used_prefix = next((p for p in prefixes if message.content.startswith(p)), None)
        prefix_stripped = message.content[len(used_prefix):].strip() if used_prefix else message.content
        args = prefix_stripped.split()[1:] if prefix_stripped else []

        for trigger, cmd in cmds.items():
            if not cmd.enabled:
                continue
            if not cmd.matches(message.content, prefix_stripped):
                continue

            group = self._groups.get(message.guild.id, {}).get(cmd.group) if cmd.group else None
            ok, reason = cmd.check_restrictions(message.author, message.channel, group)
            if not ok:
                try:
                    await message.channel.send(f'❌ {reason}', delete_after=5)
                except Exception:
                    pass
                return

            remaining = cmd.check_cooldown(message.author.id)
            if remaining > 0:
                try:
                    await message.channel.send(
                        f'⏳ This command is on cooldown. Try again in `{remaining:.1f}s`.',
                        delete_after=5
                    )
                except Exception:
                    pass
                return

            cmd.apply_cooldown(message.author.id)
            cmd.uses += 1

            var_map = build_variables(message, args)

            if cmd.trigger_type == TRIGGER_REGEX:
                try:
                    import re as _re
                    flags = 0 if cmd.case_sensitive else _re.IGNORECASE
                    m = _re.search(cmd.trigger, message.content, flags)
                    if m:
                        for i, grp in enumerate(m.groups(), 1):
                            var_map[f'match{i}'] = grp or ''
                        var_map['match0'] = m.group(0)
                except Exception:
                    pass

            raw_response = cmd.get_response()
            raw_response = apply_conditionals(raw_response, var_map)
            raw_response = apply_random_blocks(raw_response)
            for key, val in var_map.items():
                raw_response = raw_response.replace(f'{{{key}}}', val)

            clean_response, delete_after_secs, channel_sends, embed_data = await process_actions(raw_response, message, self.bot)

            sent_msg = None
            da = delete_after_secs or cmd.delete_response_after or None
            if clean_response or embed_data:
                if cmd.embed or embed_data:
                    embed = _build_response_embed(cmd, clean_response, embed_data, self.bot)
                    sent_msg = await message.channel.send(embed=embed, delete_after=da)
                else:
                    sent_msg = await message.channel.send(clean_response, delete_after=da)

            for ch, msg in channel_sends:
                try:
                    await ch.send(msg)
                except Exception:
                    pass

            if cmd.delete_trigger:
                if cmd.delete_trigger_after:
                    await asyncio.sleep(cmd.delete_trigger_after)
                try:
                    await message.delete()
                except Exception:
                    pass

            await self._save(message.guild.id)
            break

    @commands.group(name='cc', aliases=['customcmd', 'customcommand'], invoke_without_command=True, help='Custom command management.')
    @commands.has_permissions(manage_guild=True)
    async def cc_group(self, ctx):
        await ctx.send_help(ctx.command)

    @cc_group.command(name='add', help='Add a custom command. Usage: cc add <trigger> <response>')
    @commands.has_permissions(manage_guild=True)
    async def cc_add(self, ctx, trigger: str, *, response: str):
        trigger_key = trigger.lower()
        if len(trigger_key) > 50:
            return await ctx.error('Trigger must be under 50 characters.')
        if len(response) > 4000:
            return await ctx.error('Response must be under 4000 characters.')
        if self.bot.get_command(trigger_key):
            return await ctx.error(f'`{trigger_key}` conflicts with an existing bot command.')
        cmds = self._get_commands(ctx.guild.id)
        if len(cmds) >= 100:
            return await ctx.error('Maximum 100 custom commands per server.')
        nid = self._alloc_id()
        cmd = CustomCommand(trigger_key, {'responses': [response], 'numeric_id': nid})
        self._cache.setdefault(ctx.guild.id, {})[trigger_key] = cmd
        await self._save(ctx.guild.id)
        await ctx.success(f'{self.bot.e.success} Custom command `{trigger_key}` created.\nType: `command` | Responses: `1`')

    @cc_group.command(name='remove', aliases=['delete'], help='Remove a custom command.')
    @commands.has_permissions(manage_guild=True)
    async def cc_remove(self, ctx, trigger: str):
        trigger = trigger.lower()
        if trigger not in self._get_commands(ctx.guild.id):
            return await ctx.error(f'Command `{trigger}` not found.')
        del self._cache[ctx.guild.id][trigger]
        await self._save(ctx.guild.id)
        await ctx.success(f'{self.bot.e.success} Command `{trigger}` removed.')

    @cc_group.command(name='edit', help='Edit the primary response of a command.')
    @commands.has_permissions(manage_guild=True)
    async def cc_edit(self, ctx, trigger: str, *, response: str):
        trigger = trigger.lower()
        cmd = self._get_commands(ctx.guild.id).get(trigger)
        if not cmd:
            return await ctx.error(f'Command `{trigger}` not found.')
        cmd.responses[0] = response
        await self._save(ctx.guild.id)
        await ctx.success(f'{self.bot.e.success} Command `{trigger}` response updated.')

    @cc_group.command(name='addresponse', aliases=['ar2'], help='Add an extra random response to a command.')
    @commands.has_permissions(manage_guild=True)
    async def cc_addresponse(self, ctx, trigger: str, *, response: str):
        trigger = trigger.lower()
        cmd = self._get_commands(ctx.guild.id).get(trigger)
        if not cmd:
            return await ctx.error(f'Command `{trigger}` not found.')
        if len(cmd.responses) >= 10:
            return await ctx.error('Maximum 10 responses per command.')
        cmd.responses.append(response)
        await self._save(ctx.guild.id)
        await ctx.success(f'{self.bot.e.success} Response added. Command now has `{len(cmd.responses)}` responses (picked randomly).')

    @cc_group.command(name='removeresponse', aliases=['rr2'], help='Remove a response by index (1-based).')
    @commands.has_permissions(manage_guild=True)
    async def cc_removeresponse(self, ctx, trigger: str, index: int):
        trigger = trigger.lower()
        cmd = self._get_commands(ctx.guild.id).get(trigger)
        if not cmd:
            return await ctx.error(f'Command `{trigger}` not found.')
        if len(cmd.responses) <= 1:
            return await ctx.error('Cannot remove the only response. Use `cc edit` instead.')
        if index < 1 or index > len(cmd.responses):
            return await ctx.error(f'Index must be between 1 and `{len(cmd.responses)}`.')
        cmd.responses.pop(index - 1)
        await self._save(ctx.guild.id)
        await ctx.success(f'{self.bot.e.success} Response `{index}` removed.')

    @cc_group.command(name='triggertype', aliases=['tt'], help='Set trigger type: command, starts_with, contains, regex, exact_match.')
    @commands.has_permissions(manage_guild=True)
    async def cc_triggertype(self, ctx, trigger: str, trigger_type: str):
        trigger = trigger.lower()
        trigger_type = trigger_type.lower()
        if trigger_type not in ALL_TRIGGER_TYPES:
            return await ctx.error(f'Invalid type. Choose: `{", ".join(ALL_TRIGGER_TYPES)}`.')
        cmd = self._get_commands(ctx.guild.id).get(trigger)
        if not cmd:
            return await ctx.error(f'Command `{trigger}` not found.')
        if trigger_type == TRIGGER_REGEX:
            try:
                re.compile(cmd.trigger)
            except re.error as e:
                return await ctx.error(f'Current trigger is not a valid regex: `{e}`')
        cmd.trigger_type = trigger_type
        await self._save(ctx.guild.id)
        await ctx.success(f'{self.bot.e.success} Trigger type set to `{trigger_type}`.')

    @cc_group.command(name='casesensitive', aliases=['cs'], help='Toggle case sensitivity for a command.')
    @commands.has_permissions(manage_guild=True)
    async def cc_casesensitive(self, ctx, trigger: str):
        trigger = trigger.lower()
        cmd = self._get_commands(ctx.guild.id).get(trigger)
        if not cmd:
            return await ctx.error(f'Command `{trigger}` not found.')
        cmd.case_sensitive = not cmd.case_sensitive
        await self._save(ctx.guild.id)
        state = 'enabled' if cmd.case_sensitive else 'disabled'
        await ctx.success(f'{self.bot.e.success} Case sensitivity **{state}** for `{trigger}`.')

    @cc_group.command(name='cooldown', aliases=['cd'], help='Set a cooldown. Usage: cc cooldown <trigger> <seconds> [user|global]')
    @commands.has_permissions(manage_guild=True)
    async def cc_cooldown(self, ctx, trigger: str, seconds: int, cooldown_type: str = 'user'):
        trigger = trigger.lower()
        if cooldown_type not in ('user', 'global'):
            return await ctx.error('Cooldown type must be `user` or `global`.')
        cmd = self._get_commands(ctx.guild.id).get(trigger)
        if not cmd:
            return await ctx.error(f'Command `{trigger}` not found.')
        cmd.cooldown = max(0, seconds)
        cmd.cooldown_type = cooldown_type
        await self._save(ctx.guild.id)
        if seconds == 0:
            await ctx.success(f'{self.bot.e.success} Cooldown removed from `{trigger}`.')
        else:
            await ctx.success(f'{self.bot.e.success} Cooldown set to `{seconds}s` ({cooldown_type}) for `{trigger}`.')

    @cc_group.command(name='deleteafter', aliases=['da'], help='Auto-delete trigger/response. Usage: cc deleteafter <trigger> <trigger_secs> <response_secs>')
    @commands.has_permissions(manage_guild=True)
    async def cc_deleteafter(self, ctx, trigger: str, trigger_secs: int = 0, response_secs: int = 0):
        trigger = trigger.lower()
        cmd = self._get_commands(ctx.guild.id).get(trigger)
        if not cmd:
            return await ctx.error(f'Command `{trigger}` not found.')
        cmd.delete_trigger = trigger_secs > 0
        cmd.delete_trigger_after = max(0, trigger_secs)
        cmd.delete_response_after = max(0, response_secs)
        await self._save(ctx.guild.id)
        await ctx.success(
            f'{self.bot.e.success} Auto-delete set for `{trigger}`.\n'
            f'Trigger: `{"disabled" if not trigger_secs else f"{trigger_secs}s"}`\n'
            f'Response: `{"disabled" if not response_secs else f"{response_secs}s"}`'
        )

    @cc_group.command(name='restrict', help='Restrict a command to specific roles/channels.')
    @commands.has_permissions(manage_guild=True)
    async def cc_restrict(self, ctx, trigger: str, mode: str, target_type: str, *, targets: str):
        trigger = trigger.lower()
        cmd = self._get_commands(ctx.guild.id).get(trigger)
        if not cmd:
            return await ctx.error(f'Command `{trigger}` not found.')
        mode = mode.lower()
        target_type = target_type.lower()
        if mode not in ('allow', 'deny', 'clear'):
            return await ctx.error('Mode must be `allow`, `deny`, or `clear`.')
        if target_type not in ('role', 'channel'):
            return await ctx.error('Target type must be `role` or `channel`.')

        if mode == 'clear':
            if target_type == 'role':
                cmd.allowed_roles.clear()
                cmd.denied_roles.clear()
            else:
                cmd.allowed_channels.clear()
                cmd.denied_channels.clear()
            await self._save(ctx.guild.id)
            return await ctx.success(f'{self.bot.e.success} Cleared {target_type} restrictions for `{trigger}`.')

        ids = []
        for mention in targets.split():
            mention = mention.strip('<#@&>')
            if mention.isdigit():
                ids.append(int(mention))

        if not ids:
            return await ctx.error('No valid role/channel IDs found.')

        if target_type == 'role':
            if mode == 'allow':
                cmd.allowed_roles = list(set(cmd.allowed_roles + ids))
            else:
                cmd.denied_roles = list(set(cmd.denied_roles + ids))
        else:
            if mode == 'allow':
                cmd.allowed_channels = list(set(cmd.allowed_channels + ids))
            else:
                cmd.denied_channels = list(set(cmd.denied_channels + ids))

        await self._save(ctx.guild.id)
        await ctx.success(f'{self.bot.e.success} {mode.capitalize()}ed {len(ids)} {target_type}(s) for `{trigger}`.')

    @cc_group.command(name='toggle', help='Enable or disable a custom command.')
    @commands.has_permissions(manage_guild=True)
    async def cc_toggle(self, ctx, trigger: str):
        trigger = trigger.lower()
        cmd = self._get_commands(ctx.guild.id).get(trigger)
        if not cmd:
            return await ctx.error(f'Command `{trigger}` not found.')
        cmd.enabled = not cmd.enabled
        await self._save(ctx.guild.id)
        state = 'enabled' if cmd.enabled else 'disabled'
        await ctx.success(f'{self.bot.e.success} Command `{trigger}` **{state}**.')

    @cc_group.command(name='embed', help='Toggle embed mode and optionally set title/color.')
    @commands.has_permissions(manage_guild=True)
    async def cc_embed(self, ctx, trigger: str, title: str = None, color: str = None):
        trigger = trigger.lower()
        cmd = self._get_commands(ctx.guild.id).get(trigger)
        if not cmd:
            return await ctx.error(f'Command `{trigger}` not found.')
        cmd.embed = not cmd.embed
        if title:
            cmd.embed_title = title
        if color:
            try:
                int(color.lstrip('#'), 16)
                cmd.embed_color = color.lstrip('#')
            except ValueError:
                return await ctx.error('Invalid hex color.')
        await self._save(ctx.guild.id)
        state = 'enabled' if cmd.embed else 'disabled'
        await ctx.success(f'{self.bot.e.success} Embed mode **{state}** for `{trigger}`.')

    @cc_group.command(name='setgroup', help='Assign a command to a group.')
    @commands.has_permissions(manage_guild=True)
    async def cc_setgroup(self, ctx, trigger: str, *, group_name: str = None):
        trigger = trigger.lower()
        cmd = self._get_commands(ctx.guild.id).get(trigger)
        if not cmd:
            return await ctx.error(f'Command `{trigger}` not found.')
        if group_name and group_name not in self._groups.get(ctx.guild.id, {}):
            return await ctx.error(f'Group `{group_name}` not found. Create it with `cc group create`.')
        cmd.group = group_name
        await self._save(ctx.guild.id)
        msg = f'Command `{trigger}` assigned to group **{group_name}**.' if group_name else f'Command `{trigger}` removed from group.'
        await ctx.success(f'{self.bot.e.success} {msg}')

    @cc_group.command(name='describe', help='Set a description for a custom command.')
    @commands.has_permissions(manage_guild=True)
    async def cc_describe(self, ctx, trigger: str, *, description: str):
        trigger = trigger.lower()
        cmd = self._get_commands(ctx.guild.id).get(trigger)
        if not cmd:
            return await ctx.error(f'Command `{trigger}` not found.')
        cmd.description = description[:200]
        await self._save(ctx.guild.id)
        await ctx.success(f'{self.bot.e.success} Description updated for `{trigger}`.')

    @cc_group.command(name='info', help='View full details about a custom command.')
    async def cc_info(self, ctx, trigger: str):
        trigger = trigger.lower()
        cmd = self._get_commands(ctx.guild.id).get(trigger)
        if not cmd:
            return await ctx.error(f'Command `{trigger}` not found.')

        allowed_roles = ', '.join([f'<@&{r}>' for r in cmd.allowed_roles]) or 'None'
        denied_roles = ', '.join([f'<@&{r}>' for r in cmd.denied_roles]) or 'None'
        allowed_channels = ', '.join([f'<#{c}>' for c in cmd.allowed_channels]) or 'None'
        denied_channels = ', '.join([f'<#{c}>' for c in cmd.denied_channels]) or 'None'

        desc = (
            f'**Trigger:** `{trigger}`\n'
            f'**Type:** `{cmd.trigger_type}`\n'
            f'**Enabled:** `{cmd.enabled}`\n'
            f'**Case Sensitive:** `{cmd.case_sensitive}`\n'
            f'**Uses:** `{cmd.uses}`\n'
            f'**Responses:** `{len(cmd.responses)}`\n'
            f'**Embed:** `{cmd.embed}`\n'
            f'**Cooldown:** `{cmd.cooldown}s` ({cmd.cooldown_type})\n'
            f'**Delete Trigger After:** `{cmd.delete_trigger_after or "off"}s`\n'
            f'**Delete Response After:** `{cmd.delete_response_after or "off"}s`\n'
            f'**Group:** `{cmd.group or "None"}`\n'
            f'**Allowed Roles:** {allowed_roles}\n'
            f'**Denied Roles:** {denied_roles}\n'
            f'**Allowed Channels:** {allowed_channels}\n'
            f'**Denied Channels:** {denied_channels}\n'
        )
        if cmd.description:
            desc += f'**Description:** {cmd.description}\n'

        embed = self.bot.embed_manager.generic(description=desc, title=f'Custom Command: {trigger}')
        if cmd.responses:
            preview = cmd.responses[0][:300]
            embed.add_field(name='Primary Response', value=f'```\n{preview}\n```', inline=False)
        await ctx.send(embed=embed)

    @cc_group.command(name='list', help='List all custom commands, optionally filtered by group.')
    async def cc_list(self, ctx, group: str = None):
        cmds = self._get_commands(ctx.guild.id)
        if not cmds:
            return await ctx.info('No custom commands configured.')
        filtered = {t: c for t, c in cmds.items() if group is None or c.group == group}
        if not filtered:
            return await ctx.info(f'No commands in group `{group}`.')

        lines = []
        for trigger, cmd in sorted(filtered.items()):
            status = '🟢' if cmd.enabled else '🔴'
            cd = f' ⏱`{cmd.cooldown}s`' if cmd.cooldown else ''
            grp = f' [{cmd.group}]' if cmd.group else ''
            lines.append(f'{status} `{trigger}` — `{cmd.trigger_type}`{cd}{grp}')

        embed = self.bot.embed_manager.generic(
            description='\n'.join(lines),
            title=f'Custom Commands ({len(filtered)}/100)'
        )
        await ctx.send(embed=embed)

    @cc_group.command(name='variables', aliases=['vars2'], help='Show all available template variables.')
    async def cc_variables(self, ctx):
        desc = (
            "**User Variables:**\n"
            "`{user}` mention | `{username}` display name | `{userid}` ID\n"
            "`{usertag}` user#0000 | `{useravatar}` avatar URL\n\n"
            "**Server Variables:**\n"
            "`{server}` name | `{serverid}` ID | `{membercount}` count | `{servericon}` icon URL\n\n"
            "**Channel Variables:**\n"
            "`{channel}` mention | `{channelname}` name | `{channelid}` ID\n\n"
            "**Argument Variables:**\n"
            "`{args}` all args | `{arg1}` `{arg2}`... individual | `{argscount}` count\n\n"
            "**Regex Capture Groups:**\n"
            "`{match0}` full match | `{match1}` `{match2}`... capture groups\n\n"
            "**Message/Time:**\n"
            "`{msgid}` | `{msglink}` | `{timestamp}` | `{prefix}`\n\n"
            "**Template Blocks:**\n"
            "`{if arg1 == yes}...{else}...{end}` — conditional\n"
            "`{random}a{|}b{|}c{endrandom}` — random pick\n\n"
            "Use `cc actions` to see all available action tags."
        )
        embed = self.bot.embed_manager.generic(description=desc, title='📋 Custom Command Variables')
        await ctx.send(embed=embed)

    @cc_group.command(name='actions', aliases=['acts'], help='Show all available action tags for custom command responses.')
    async def cc_actions(self, ctx):
        pages = [
            (
                "🎭 Role Actions",
                "`{addrole:Role}` — add role to author\n"
                "`{removerole:Role}` — remove role from author\n"
                "`{togglerole:Role}` — toggle role on/off\n"
                "`{addroleto:@Member|Role}` — add role to specific member\n"
                "`{removerolefrom:@Member|Role}` — remove role from specific member\n"
                "`{createrole:Name|#hex}` — create a new role\n"
                "`{deleterole:Role}` — delete a role\n"
                "`{editrole:Role|name=New Name}` — edit role (name/color/hoist/mentionable)"
            ),
            (
                "🔨 Moderation Actions",
                "`{kick:@Member|reason}` — kick a member\n"
                "`{ban:@Member|reason}` — ban a member\n"
                "`{softban:@Member|reason}` — ban+unban to clear messages\n"
                "`{unban:user_id}` — unban a user\n"
                "`{timeout:@Member|10m}` / `{mute:@Member|1h}` — timeout\n"
                "`{untimeout:@Member}` / `{unmute:@Member}` — remove timeout\n"
                "`{warn:@Member|reason}` — add a mod warning\n"
                "`{setnick:@Member|Nick}` — set nickname\n"
                "`{resetnick:@Member}` — reset nickname"
            ),
            (
                "📨 Message Actions",
                "`{dm:message}` — DM the author\n"
                "`{dmmember:@Member|message}` — DM specific member\n"
                "`{sendreply:message}` — reply to trigger message\n"
                "`{sendchannel:#channel|message}` — send to a channel\n"
                "`{react:emoji1,emoji2}` — react to trigger\n"
                "`{reactremove:emoji}` — remove a reaction\n"
                "`{silentdelete}` / `{deletetrigger}` — delete trigger\n"
                "`{deleteafter:seconds}` — auto-delete response\n"
                "`{noresponse}` — send no response text"
            ),
            (
                "🏗️ Channel Actions",
                "`{createchannel:name|Category}` — create text channel\n"
                "`{deletechannel:#channel}` — delete a channel\n"
                "`{lockchannel:#channel}` — lock channel (deny send)\n"
                "`{unlockchannel:#channel}` — unlock channel\n"
                "`{hidechannel:#channel}` — hide channel\n"
                "`{showchannel:#channel}` — show channel"
            ),
            (
                "🎨 Embed Builder Actions",
                "`{settitle:My Title}` — set embed title\n"
                "`{setcolor:#FF5733}` — set embed color\n"
                "`{setfooter:Footer text}` — set embed footer\n"
                "`{setthumbnail:url}` — set embed thumbnail\n"
                "`{setimage:url}` — set embed image\n"
                "`{addfield:Name|Value|true}` — add embed field (inline optional)\n\n"
                "Combine with `cc embed` to force embed mode,\nor mix action tags into any response."
            ),
            (
                "⚙️ Utility Actions",
                "`{log:#channel|message}` — log to a channel\n"
                "`{sleep:seconds}` — pause execution (max 60s)\n\n"
                "**Example — Self-Role:**\n"
                "```\n{togglerole:Member}\n{if hasrole Member}\nYou now have the Member role!\n{else}\nRole removed.\n{end}\n```\n"
                "**Example — Antinuke log:**\n"
                "```\n{log:#audit-log|🚨 {username} ran the command}\n{noresponse}\n```"
            )
        ]
        class ActionPages(discord.ui.View):
            def __init__(self_inner):
                super().__init__(timeout=120)
                self_inner.page = 0
            def build_embed(self_inner):
                title, body = pages[self_inner.page]
                embed = self.bot.embed_manager.generic(description=body, title=f'⚡ Action Tags — {title}')
                embed.set_footer(text=f'Page {self_inner.page + 1}/{len(pages)} — Use buttons to navigate')
                return embed
            @discord.ui.button(label='◀', style=discord.ButtonStyle.secondary)
            async def prev(self_inner, interaction, button):
                self_inner.page = (self_inner.page - 1) % len(pages)
                await interaction.response.edit_message(embed=self_inner.build_embed(), view=self_inner)
            @discord.ui.button(label='▶', style=discord.ButtonStyle.secondary)
            async def next_btn(self_inner, interaction, button):
                self_inner.page = (self_inner.page + 1) % len(pages)
                await interaction.response.edit_message(embed=self_inner.build_embed(), view=self_inner)
        v = ActionPages()
        await ctx.send(embed=v.build_embed(), view=v)

    @cc_group.group(name='group', invoke_without_command=True, help='Custom command group management.')
    @commands.has_permissions(manage_guild=True)
    async def cc_groupcmd(self, ctx):
        await ctx.send_help(ctx.command)

    @cc_groupcmd.command(name='create', help='Create a command group.')
    @commands.has_permissions(manage_guild=True)
    async def ccg_create(self, ctx, *, name: str):
        if len(name) > 50:
            return await ctx.error('Group name must be under 50 characters.')
        groups = self._groups.setdefault(ctx.guild.id, {})
        if len(groups) >= 20:
            return await ctx.error('Maximum 20 groups per server.')
        if name in groups:
            return await ctx.error(f'Group `{name}` already exists.')
        groups[name] = CCGroup({'name': name})
        await self._save(ctx.guild.id)
        await ctx.success(f'{self.bot.e.success} Group **{name}** created.')

    @cc_groupcmd.command(name='delete', help='Delete a command group.')
    @commands.has_permissions(manage_guild=True)
    async def ccg_delete(self, ctx, *, name: str):
        groups = self._groups.get(ctx.guild.id, {})
        if name not in groups:
            return await ctx.error(f'Group `{name}` not found.')
        del groups[name]
        for cmd in self._cache.get(ctx.guild.id, {}).values():
            if cmd.group == name:
                cmd.group = None
        await self._save(ctx.guild.id)
        await ctx.success(f'{self.bot.e.success} Group **{name}** deleted.')

    @cc_groupcmd.command(name='list', help='List all command groups.')
    async def ccg_list(self, ctx):
        groups = self._groups.get(ctx.guild.id, {})
        if not groups:
            return await ctx.info('No groups configured.')
        cmds = self._cache.get(ctx.guild.id, {})
        desc = ''
        for name, g in groups.items():
            count = sum(1 for c in cmds.values() if c.group == name)
            desc += f'**{name}** — `{count}` commands\n'
        embed = self.bot.embed_manager.generic(description=desc, title=f'Command Groups ({len(groups)}/20)')
        await ctx.send(embed=embed)

    @cc_groupcmd.command(name='restrict', help='Apply role/channel restrictions to a group.')
    @commands.has_permissions(manage_guild=True)
    async def ccg_restrict(self, ctx, group_name: str, mode: str, target_type: str, *, targets: str):
        groups = self._groups.get(ctx.guild.id, {})
        if group_name not in groups:
            return await ctx.error(f'Group `{group_name}` not found.')
        g = groups[group_name]
        mode = mode.lower()
        target_type = target_type.lower()
        if mode not in ('allow', 'deny', 'clear'):
            return await ctx.error('Mode must be `allow`, `deny`, or `clear`.')
        if target_type not in ('role', 'channel'):
            return await ctx.error('Target type must be `role` or `channel`.')

        if mode == 'clear':
            if target_type == 'role':
                g.allowed_roles.clear()
                g.denied_roles.clear()
            else:
                g.allowed_channels.clear()
                g.denied_channels.clear()
            await self._save(ctx.guild.id)
            return await ctx.success(f'{self.bot.e.success} Cleared group restrictions.')

        ids = [int(m.strip('<#@&>')) for m in targets.split() if m.strip('<#@&>').isdigit()]
        if not ids:
            return await ctx.error('No valid IDs found.')

        if target_type == 'role':
            if mode == 'allow': g.allowed_roles = list(set(g.allowed_roles + ids))
            else: g.denied_roles = list(set(g.denied_roles + ids))
        else:
            if mode == 'allow': g.allowed_channels = list(set(g.allowed_channels + ids))
            else: g.denied_channels = list(set(g.denied_channels + ids))

        await self._save(ctx.guild.id)
        await ctx.success(f'{self.bot.e.success} Group **{group_name}** {mode}ed {len(ids)} {target_type}(s).')

    @cc_group.command(name='test', help='Test a custom command without using your cooldown.')
    @commands.has_permissions(manage_guild=True)
    async def cc_test(self, ctx, trigger: str, *, args: str = ''):
        trigger = trigger.lower()
        cmd = self._get_commands(ctx.guild.id).get(trigger)
        if not cmd:
            return await ctx.error(f'Command `{trigger}` not found.')
        arg_list = args.split() if args else []
        var_map = build_variables(ctx.message, arg_list)
        raw_response = cmd.get_response()
        for key, val in var_map.items():
            raw_response = raw_response.replace(f'{{{key}}}', val)
        clean_response, _, _, embed_data = await process_actions(raw_response, ctx.message, self.bot)
        embed = self.bot.embed_manager.generic(
            description=f'**Response preview:**\n{clean_response[:1000]}',
            title=f'Testing: {trigger}'
        )
        await ctx.send(embed=embed)

    @cc_group.command(name='raw', help='Show the raw unprocessed response of a command.')
    @commands.has_permissions(manage_guild=True)
    async def cc_raw(self, ctx, trigger: str, index: int = 1):
        trigger = trigger.lower()
        cmd = self._get_commands(ctx.guild.id).get(trigger)
        if not cmd:
            return await ctx.error(f'Command `{trigger}` not found.')
        if index < 1 or index > len(cmd.responses):
            return await ctx.error(f'Index must be between 1 and `{len(cmd.responses)}`.')
        raw = cmd.responses[index - 1]
        await ctx.send(f'```\n{raw[:1990]}\n```')

    @cc_group.command(name='copy', help='Copy a custom command to a new trigger name.')
    @commands.has_permissions(manage_guild=True)
    async def cc_copy(self, ctx, source: str, *, destination: str):
        source = source.lower()
        destination = destination.lower()
        cmds = self._get_commands(ctx.guild.id)
        if source not in cmds:
            return await ctx.error(f'Command `{source}` not found.')
        if destination in cmds:
            return await ctx.error(f'Command `{destination}` already exists.')
        if len(cmds) >= 100:
            return await ctx.error('Maximum 100 custom commands per server.')
        import copy
        new_cmd = CustomCommand(destination, cmds[source].to_dict())
        new_cmd.uses = 0
        self._cache[ctx.guild.id][destination] = new_cmd
        await self._save(ctx.guild.id)
        await ctx.success(f'{self.bot.e.success} Copied `{source}` → `{destination}`.')

    @cc_group.command(name='stats', help='Show usage statistics for custom commands in this server.')
    async def cc_stats(self, ctx):
        cmds = self._get_commands(ctx.guild.id)
        if not cmds:
            return await ctx.info('No custom commands configured.')
        sorted_cmds = sorted(cmds.items(), key=lambda x: x[1].uses, reverse=True)[:10]
        desc = '\n'.join([f'`{i+1}.` `{t}` — **{c.uses}** uses' for i, (t, c) in enumerate(sorted_cmds)])
        total = sum(c.uses for c in cmds.values())
        embed = self.bot.embed_manager.generic(
            description=f'**Total uses:** `{total}`\n\n{desc}',
            title='📊 Custom Command Stats'
        )
        await ctx.send(embed=embed)


    @cc_group.command(name='interval', help='Set a command to run on an interval. Usage: cc interval <trigger> <minutes> [#channel]')
    @commands.has_permissions(manage_guild=True)
    async def cc_interval(self, ctx, trigger: str, minutes: int, channel: discord.TextChannel = None):
        trigger = trigger.lower()
        cmd = self._get_commands(ctx.guild.id).get(trigger)
        if not cmd:
            return await ctx.error(f'Command `{trigger}` not found.')
        if minutes < 1:
            return await ctx.error('Minimum interval is 1 minute.')
        if minutes > 10080:
            return await ctx.error('Maximum interval is 7 days (10080 minutes).')
        channel = channel or ctx.channel
        cmd.trigger_type = TRIGGER_INTERVAL
        cmd.interval_minutes = minutes
        cmd.interval_channel = channel.id
        import time as _t
        cmd.interval_next_run = _t.time() + (minutes * 60)
        await self._save(ctx.guild.id)
        next_ts = int(cmd.interval_next_run)
        await ctx.success(
            f"{self.bot.e.success} `{trigger}` set to run every `{minutes}` minute(s) in {channel.mention}.\n"
            f"First run: <t:{next_ts}:R>"
        )

    @cc_group.command(name='reaction', help='Set a command to fire on a reaction. Usage: cc reaction <trigger> <emoji> [message_id]')
    @commands.has_permissions(manage_guild=True)
    async def cc_reaction(self, ctx, trigger: str, emoji: str, message_id: int = None):
        trigger = trigger.lower()
        cmd = self._get_commands(ctx.guild.id).get(trigger)
        if not cmd:
            return await ctx.error(f'Command `{trigger}` not found.')
        cmd.trigger_type = TRIGGER_REACTION
        cmd.reaction_emoji = emoji
        cmd.reaction_message_id = message_id
        await self._save(ctx.guild.id)
        msg = f'{self.bot.e.success} `{trigger}` will fire on reaction {emoji}'
        msg += f' on message `{message_id}`.' if message_id else ' on any message.'
        await ctx.success(msg)

    @cc_group.command(name='execcc', aliases=['exec2'], help='Execute a custom command by name or numeric ID.')
    @commands.has_permissions(manage_guild=True)
    async def cc_execcc(self, ctx, trigger_or_id: str, *, args: str = ''):
        cmds = self._get_commands(ctx.guild.id)
        cmd = cmds.get(trigger_or_id.lower())
        if not cmd and trigger_or_id.isdigit():
            cmd = next((c for c in cmds.values() if c.numeric_id == int(trigger_or_id)), None)
        if not cmd:
            return await ctx.error(f'Command `{trigger_or_id}` not found.')
        if not cmd.enabled:
            return await ctx.error(f'Command `{cmd.trigger}` is disabled.')
        arg_list = args.split() if args else []
        var_map = build_variables(ctx.message, arg_list)
        raw = cmd.get_response()
        raw = apply_conditionals(raw, var_map)
        raw = apply_random_blocks(raw)
        for k, v in var_map.items():
            raw = raw.replace(f'{{{k}}}', v)
        clean, delete_after, channel_sends, embed_data = await process_actions(raw, ctx.message, self.bot)
        da = delete_after or cmd.delete_response_after or None
        if clean or embed_data:
            if cmd.embed or embed_data:
                embed = _build_response_embed(cmd, clean, embed_data, self.bot)
                await ctx.send(embed=embed, delete_after=da)
            else:
                await ctx.send(clean, delete_after=da)
        for ch, msg in channel_sends:
            try:
                await ch.send(msg)
            except Exception:
                pass
        cmd.uses += 1
        await self._save(ctx.guild.id)

    @cc_group.command(name='id', help='Show the numeric ID of a custom command (for use with execcc).')
    async def cc_id(self, ctx, trigger: str):
        trigger = trigger.lower()
        cmd = self._get_commands(ctx.guild.id).get(trigger)
        if not cmd:
            return await ctx.error(f'Command `{trigger}` not found.')
        await ctx.success(f'Command `{trigger}` has numeric ID: `{cmd.numeric_id}`.')

    @cc_group.command(name='export', help='Export all custom commands as a JSON file.')
    @commands.has_permissions(manage_guild=True)
    async def cc_export(self, ctx):
        cmds = self._get_commands(ctx.guild.id)
        if not cmds:
            return await ctx.error('No custom commands to export.')
        import json, io
        data = {trigger: cmd.to_dict() for trigger, cmd in cmds.items()}
        buf = io.BytesIO(json.dumps(data, indent=2).encode())
        buf.seek(0)
        await ctx.send(
            f'{self.bot.e.success} Exported `{len(data)}` custom commands.',
            file=discord.File(buf, filename=f'cc_export_{ctx.guild.id}.json')
        )

    @cc_group.command(name='import', help='Import custom commands from a JSON file (attach the file).')
    @commands.has_permissions(manage_guild=True)
    async def cc_import(self, ctx):
        if not ctx.message.attachments:
            return await ctx.error('Attach a JSON file exported with `cc export`.')
        attachment = ctx.message.attachments[0]
        if not attachment.filename.endswith('.json'):
            return await ctx.error('File must be a `.json` file.')
        import json, aiohttp
        async with aiohttp.ClientSession() as s:
            async with s.get(attachment.url) as r:
                raw = await r.text()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return await ctx.error('Invalid JSON file.')
        existing = self._get_commands(ctx.guild.id)
        imported = 0
        skipped = 0
        for trigger, cmd_data in data.items():
            trigger = trigger.lower()
            if len(existing) + imported >= 100:
                skipped += 1
                continue
            if trigger in existing:
                skipped += 1
                continue
            nid = self._alloc_id()
            cmd_data['numeric_id'] = nid
            self._cache.setdefault(ctx.guild.id, {})[trigger] = CustomCommand(trigger, cmd_data)
            imported += 1
        await self._save(ctx.guild.id)
        await ctx.success(
            f'{self.bot.e.success} Imported `{imported}` commands.'
            + (f' Skipped `{skipped}` (duplicates or limit reached).' if skipped else '')
        )

    @cc_group.command(name='search', help='Search custom commands by trigger name or response content.')
    async def cc_search(self, ctx, *, query: str):
        cmds = self._get_commands(ctx.guild.id)
        query_lower = query.lower()
        matches = {
            t: c for t, c in cmds.items()
            if query_lower in t
            or any(query_lower in r.lower() for r in c.responses)
            or query_lower in (c.description or '').lower()
        }
        if not matches:
            return await ctx.info(f'No commands matching `{query}`.')
        lines = [f'`{t}` — `{c.trigger_type}`' for t, c in list(matches.items())[:15]]
        embed = self.bot.embed_manager.generic(
            description='\n'.join(lines),
            title=f'Search: "{query}" ({len(matches)} results)'
        )
        await ctx.send(embed=embed)

    @cc_group.command(name='resetcd', help='Reset the cooldown of a command for a specific user or globally.')
    @commands.has_permissions(manage_guild=True)
    async def cc_resetcd(self, ctx, trigger: str, member: discord.Member = None):
        trigger = trigger.lower()
        cmd = self._get_commands(ctx.guild.id).get(trigger)
        if not cmd:
            return await ctx.error(f'Command `{trigger}` not found.')
        if member:
            cmd._cooldown_cache.pop(member.id, None)
            await ctx.success(f'{self.bot.e.success} Cooldown reset for {member.mention} on `{trigger}`.')
        else:
            cmd._cooldown_cache.clear()
            await ctx.success(f'{self.bot.e.success} All cooldowns reset for `{trigger}`.')

    @cc_group.command(name='rename', aliases=['mv'], help='Rename a custom command trigger.')
    @commands.has_permissions(manage_guild=True)
    async def cc_rename(self, ctx, old_trigger: str, new_trigger: str):
        old_trigger = old_trigger.lower()
        new_trigger = new_trigger.lower()
        cmds = self._get_commands(ctx.guild.id)
        if old_trigger not in cmds:
            return await ctx.error(f'Command `{old_trigger}` not found.')
        if new_trigger in cmds:
            return await ctx.error(f'Command `{new_trigger}` already exists.')
        if self.bot.get_command(new_trigger):
            return await ctx.error(f'`{new_trigger}` conflicts with an existing bot command.')
        cmd = cmds.pop(old_trigger)
        cmd.trigger = new_trigger
        cmds[new_trigger] = cmd
        await self._save(ctx.guild.id)
        await ctx.success(f'{self.bot.e.success} Renamed `{old_trigger}` → `{new_trigger}`.')

    @cc_group.command(name='enableall', help='Enable all custom commands at once.')
    @commands.has_permissions(manage_guild=True)
    async def cc_enableall(self, ctx):
        cmds = self._get_commands(ctx.guild.id)
        for cmd in cmds.values():
            cmd.enabled = True
        await self._save(ctx.guild.id)
        await ctx.success(f'{self.bot.e.success} All `{len(cmds)}` commands enabled.')

    @cc_group.command(name='disableall', help='Disable all custom commands at once.')
    @commands.has_permissions(manage_guild=True)
    async def cc_disableall(self, ctx):
        cmds = self._get_commands(ctx.guild.id)
        for cmd in cmds.values():
            cmd.enabled = False
        await self._save(ctx.guild.id)
        await ctx.success(f'{self.bot.e.success} All `{len(cmds)}` commands disabled.')

    @cc_group.command(name='purge', help='Delete all custom commands for this server. Requires confirmation.')
    @commands.has_permissions(manage_guild=True)
    async def cc_purge(self, ctx):
        cmds = self._get_commands(ctx.guild.id)
        if not cmds:
            return await ctx.error('No custom commands to delete.')
        count = len(cmds)
        confirm_msg = await ctx.send(
            f'⚠️ This will permanently delete all **{count}** custom commands. '
            f'React ✅ to confirm or ❌ to cancel.'
        )
        await confirm_msg.add_reaction('✅')
        await confirm_msg.add_reaction('❌')

        def check(r, u):
            return u == ctx.author and str(r.emoji) in ('✅', '❌') and r.message.id == confirm_msg.id

        try:
            reaction, _ = await self.bot.wait_for('reaction_add', timeout=30, check=check)
        except Exception:
            return await confirm_msg.edit(content='❌ Timed out.')

        if str(reaction.emoji) == '✅':
            self._cache[ctx.guild.id] = {}
            await self._save(ctx.guild.id)
            await confirm_msg.edit(content=f'{self.bot.e.success} Deleted all `{count}` custom commands.')
        else:
            await confirm_msg.edit(content='❌ Cancelled.')

async def setup(bot):
    await bot.add_cog(CustomCommands(bot))
