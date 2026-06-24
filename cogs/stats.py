import discord
from discord.ext import commands, tasks
import asyncio
import datetime
import collections
import pytz

class Statistics(commands.Cog):
    category = 'utility'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager
        self.pending_updates = {}
        self.last_updates = collections.defaultdict(float)
        self.last_full_sync = collections.defaultdict(float)
        self.queue_processor.start()
        self.automatic_sync.start()

    def cog_unload(self):
        self.queue_processor.cancel()
        self.automatic_sync.cancel()

    async def _is_premium(self, ctx):
        is_p, _ = await self.bot.premium_manager.get_premium_status(ctx.guild.id)
        if not is_p:
            await ctx.error("This command is for **Premium Servers** only! Upgrade to unlock manual synchronization.")
            return False
        return True

    async def get_config(self, guild_id):
        return await self.bot.get_config('stats_config', guild_id)

    async def update_config(self, guild_id, data):
        await self.bot.update_config('stats_config', guild_id, data)

    @tasks.loop(seconds=10)
    async def queue_processor(self):
        if not self.pending_updates: return
        
        to_process = list(self.pending_updates.items())
        
        for (guild_id, channel_id), name in to_process:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                self.pending_updates.pop((guild_id, channel_id), None)
                continue
            
            channel = guild.get_channel(channel_id)
            if not channel:
                self.pending_updates.pop((guild_id, channel_id), None)
                continue

            now = datetime.datetime.utcnow().timestamp()
            if now - self.last_updates[channel_id] < 330:
                continue

            try:
                if channel.name != name:
                    await channel.edit(name=name, reason="Horizen Statistics Update")
                    self.last_updates[channel_id] = now
                self.pending_updates.pop((guild_id, channel_id), None)
            except discord.Forbidden:
                self.pending_updates.pop((guild_id, channel_id), None)
            except discord.HTTPException as e:
                if e.status == 429:
                    await asyncio.sleep(e.retry_after or 10)
                else:
                    self.pending_updates.pop((guild_id, channel_id), None)
            except:
                self.pending_updates.pop((guild_id, channel_id), None)

    @tasks.loop(minutes=10)
    async def automatic_sync(self):
        now = datetime.datetime.utcnow().timestamp()
        for guild in self.bot.guilds:
            is_p, _ = await self.bot.premium_manager.get_premium_status(guild.id)
            if is_p:
                await self._trigger_update(guild)
            else:
                if now - self.last_full_sync[guild.id] >= 1800:
                    await self._trigger_update(guild)
                    self.last_full_sync[guild.id] = now

    def _resolve_stat(self, guild, s_type, meta=None):
        if s_type == 'members': return guild.member_count
        if s_type == 'online': return len([m for m in guild.members if m.status != discord.Status.offline])
        if s_type == 'boosts': return guild.premium_subscription_count
        if s_type == 'bots': return len([m for m in guild.members if m.bot])
        if s_type == 'humans': return guild.member_count - len([m for m in guild.members if m.bot])
        if s_type == 'channels': return len(guild.channels)
        if s_type == 'roles': return len(guild.roles)
        if s_type == 'clock': return datetime.datetime.now(pytz.utc).strftime("%H:%M UTC")
        if s_type == 'role' and meta:
            role = guild.get_role(int(meta))
            return len(role.members) if role else 0
        return 0

    async def _trigger_update(self, guild):
        config = await self.get_config(guild.id)
        if not config or not config.get('enabled'): return

        feeds = config.get('feeds', [])
        for feed in feeds:
            ch = guild.get_channel(feed['channel_id'])
            if not ch: continue
            
            val = self._resolve_stat(guild, feed['type'], feed.get('meta'))
            formatted_val = f"{val:,}" if isinstance(val, int) else val
            
            current_name = ch.name
            if ":" in current_name:
                prefix = current_name.split(":")[0]
                new_name = f"{prefix}: {formatted_val}"
            else:
                label = feed['type'].capitalize()
                if feed['type'] == 'role' and feed.get('meta'):
                    role = guild.get_role(int(feed['meta']))
                    label = role.name if role else "Role"
                new_name = f"{label}: {formatted_val}"
            
            if current_name != new_name:
                self.pending_updates[(guild.id, ch.id)] = new_name

    @commands.Cog.listener()
    async def on_member_join(self, member): await self._trigger_update(member.guild)

    @commands.Cog.listener()
    async def on_member_remove(self, member): await self._trigger_update(member.guild)

    @commands.group(name="stats", aliases=["statistics"], invoke_without_command=True, help="Smart server statistics management.")
    @commands.has_permissions(administrator=True)
    async def stats_group(self, ctx):
        config = await self.get_config(ctx.guild.id)
        is_p, _ = await self.bot.premium_manager.get_premium_status(ctx.guild.id)
        
        status = f"{ctx.e.success} Enabled" if config.get('enabled') else f"{ctx.e.error} Disabled"
        tier = "✨ Premium" if is_p else "🛡️ Regular"
        
        feeds = config.get('feeds', [])
        desc = f"**Status:** {status}\n**Tier:** {tier}\n\n**Active Counters:** (`{len(feeds)}`)\n"
        
        if not feeds:
            desc += "└ *No counters active. Use `!stats add`.*"
        else:
            for i, f in enumerate(feeds, 1):
                ch = ctx.guild.get_channel(f['channel_id'])
                desc += f"`{i}.` **{f['type'].capitalize()}** -> {ch.mention if ch else '`Deleted/Restricted`'}\n"

        desc += "\n**How to customize names:**\nSimply rename the channel in Discord. Ensure it contains a `:` (e.g., `Members : 0`). The bot will update only the part after the colon."
        await ctx.embed(desc, title=f"{ctx.e.server} Statistics Hub")

    @stats_group.command(name="add", help="Add a stat counter. Types: members, online, boosts, humans, bots, channels, roles, clock, role")
    @commands.has_permissions(administrator=True)
    async def stats_add(self, ctx, s_type: str, target: discord.abc.GuildChannel = None):
        s_type = s_type.lower()
        valid = ['members', 'online', 'boosts', 'humans', 'bots', 'channels', 'roles', 'clock', 'role']
        if s_type not in valid:
            return await ctx.error(f"Invalid type. Use: {', '.join(valid)}")

        config = await self.get_config(ctx.guild.id)
        feeds = config.get('feeds', [])
        
        if len(feeds) >= 15: return await ctx.error("Maximum 15 counters allowed.")

        meta = None
        if s_type == 'role':
            if not isinstance(target, discord.Role):
                return await ctx.error("For 'role' type, please provide a role mention or ID.")
            meta = str(target.id)
            target = None

        channel = target if isinstance(target, discord.VoiceChannel) else None

        if not channel:
            overwrites = {
                ctx.guild.default_role: discord.PermissionOverwrite(connect=False),
                ctx.guild.me: discord.PermissionOverwrite(manage_channels=True, connect=True)
            }
            cat_id = config.get('category_id')
            category = ctx.guild.get_channel(cat_id) if cat_id else None
            
            label = s_type.capitalize()
            if s_type == 'role' and meta:
                r = ctx.guild.get_role(int(meta))
                label = r.name if r else "Role"
                
            channel = await ctx.guild.create_voice_channel(name=f"{label}: ...", category=category, overwrites=overwrites)
        
        if not channel.permissions_for(ctx.guild.me).manage_channels:
            return await ctx.error(f"I do not have permission to manage the channel {channel.mention}. Please grant me 'Manage Channels'.")

        feeds.append({
            'type': s_type,
            'channel_id': channel.id,
            'meta': meta
        })
        
        await self.update_config(ctx.guild.id, {
            'enabled': True,
            'feeds': feeds
        })
        
        await self._trigger_update(ctx.guild)
        await ctx.success(f"Added **{s_type}** counter in {channel.mention}!")

    @stats_group.command(name="remove", help="Remove a counter by its index.")
    @commands.has_permissions(administrator=True)
    async def stats_remove(self, ctx, index: int):
        config = await self.get_config(ctx.guild.id)
        feeds = config.get('feeds', [])
        if not feeds or index < 1 or index > len(feeds):
            return await ctx.error("Invalid index.")

        feeds.pop(index - 1)
        await self.update_config(ctx.guild.id, {'feeds': feeds})
        await ctx.success("Counter unlinked.")

    @stats_group.command(name="sync", help="Force a manual sync (Premium Only).")
    @commands.has_permissions(administrator=True)
    async def stats_sync(self, ctx):
        if not await self._is_premium(ctx): return
        await self._trigger_update(ctx.guild)
        
        pending = 0
        for (gid, cid) in self.pending_updates.keys():
            if gid == ctx.guild.id: pending += 1
            
        await ctx.success(f"Synchronization triggered. `{pending}` counters are currently in the throttled update queue.")

async def setup(bot):
    await bot.add_cog(Statistics(bot))
