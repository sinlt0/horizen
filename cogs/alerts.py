import discord
from discord.ext import commands, tasks
import aiohttp
import datetime
import re
import xml.etree.ElementTree as ET
import json
import asyncio
import random

class AlertPlatform:
    YOUTUBE = "youtube"
    TWITCH = "twitch"
    REDDIT = "reddit"
    TWITTER = "twitter"

class AlertStyle:
    COLORS = {
        "youtube": 0xFF0000,
        "twitch": 0x9146FF,
        "reddit": 0xFF4500,
        "twitter": 0x1DA1F2
    }
    ICONS = {
        "youtube": "https://i.imgur.com/7K5967Y.png",
        "twitch": "https://i.imgur.com/978wP83.png",
        "reddit": "https://i.imgur.com/83uXmKx.png",
        "twitter": "https://i.imgur.com/B94p9rV.png"
    }

class EditMessageModal(discord.ui.Modal, title="Edit Notification Message"):
    message_input = discord.ui.TextInput(
        label="Announcement Message",
        style=discord.TextStyle.paragraph,
        placeholder="Use !alerts variables to see all tags (e.g. {url}, {channelname}, {mention})",
        required=True,
        min_length=10,
        max_length=500
    )

    def __init__(self, bot, platform, index, feed, config_callback):
        super().__init__()
        self.bot = bot
        self.platform = platform
        self.index = index
        self.feed = feed
        self.config_callback = config_callback
        self.message_input.default = feed.get('message', "{mention} **{author}** is now available on **{platform}**!")

    async def on_submit(self, interaction: discord.Interaction):
        await self.config_callback(interaction, self.platform, self.index, self.message_input.value)

class AddFeedModal(discord.ui.Modal, title="Add Social Media Feed"):
    id_input = discord.ui.TextInput(label="Channel ID / Username / Subreddit", placeholder="e.g. UC_x5XG1OV2P6uYZ5FqEBtSw or MrBeast", required=True)
    channel_input = discord.ui.TextInput(label="Discord Channel ID", placeholder="Right click channel -> Copy ID", required=True, min_length=17, max_length=20)
    role_input = discord.ui.TextInput(label="Role ID to Ping (Optional)", placeholder="Leave blank for no ping", required=False)

    def __init__(self, bot, platform, add_callback):
        super().__init__()
        self.bot = bot
        self.platform = platform
        self.add_callback = add_callback

    async def on_submit(self, interaction: discord.Interaction):
        await self.add_callback(interaction, self.platform, self.id_input.value, self.channel_input.value, self.role_input.value)

class AlertDashboard(discord.ui.View):
    def __init__(self, bot, guild_id, config):
        super().__init__(timeout=120)
        self.bot = bot
        self.guild_id = guild_id
        self.config = config
        self.current_platform = None
        self.selected_index = None

    def _build_embed(self):
        desc = f"### {self.bot.e.presence} Social Hub Interface\nSelect a platform below to manage your server's automated feeds.\n\n"
        
        for platform in ["youtube", "twitch", "reddit", "twitter"]:
            feeds = self.config.get(platform, [])
            icon = "✅" if feeds else "❌"
            desc += f"**{platform.capitalize()}** • {icon} (`{len(feeds)}` feeds)\n"
        
        if self.current_platform:
            feeds = self.config.get(self.current_platform, [])
            desc += f"\n---\n**Current Platform:** `{self.current_platform.capitalize()}`\n"
            if feeds:
                for i, f in enumerate(feeds, 1):
                    mark = "⭐" if self.selected_index == i-1 else "└"
                    ch = self.bot.get_guild(self.guild_id).get_channel(f['discord_channel_id'])
                    desc += f"{mark} `{i}.` **{f.get('name', f['channel_id'])}** -> {ch.mention if ch else '`Unknown`'}\n"
            else:
                desc += "└ *No feeds configured yet.*"

        embed = self.bot.embed_manager.generic(description=desc, title="Notification Center")
        embed.set_footer(text="Manage feeds visually with buttons below")
        return embed

    @discord.ui.select(placeholder="🌐 Choose a Platform...", options=[
        discord.SelectOption(label="YouTube", value="youtube", emoji="🔴"),
        discord.SelectOption(label="Twitch", value="twitch", emoji="🟣"),
        discord.SelectOption(label="Reddit", value="reddit", emoji="🟠"),
        discord.SelectOption(label="Twitter / X", value="twitter", emoji="🔵")
    ])
    async def platform_select(self, interaction, select):
        self.current_platform = select.values[0]
        self.selected_index = None
        await interaction.response.edit_message(embed=self._build_embed(), view=self)

    @discord.ui.button(label="Add Feed", style=discord.ButtonStyle.success, emoji="➕")
    async def add_btn(self, interaction, button):
        if not self.current_platform:
            return await interaction.response.send_message("Please select a platform first!", ephemeral=True)
        await interaction.response.send_modal(AddFeedModal(self.bot, self.current_platform, self.bot.get_cog("SocialAlerts")._modal_add_feed))

    @discord.ui.button(label="Edit Message", style=discord.ButtonStyle.primary, emoji="📝")
    async def edit_btn(self, interaction, button):
        if not self.current_platform:
            return await interaction.response.send_message("Please select a platform first!", ephemeral=True)
        
        feeds = self.config.get(self.current_platform, [])
        if not feeds: return await interaction.response.send_message("No feeds found.", ephemeral=True)

        if len(feeds) > 1 and self.selected_index is None:
            options = [discord.SelectOption(label=f"{i}. {f.get('name', f['channel_id'])}", value=str(i-1)) for i, f in enumerate(feeds)]
            class FeedSelect(discord.ui.View):
                def __init__(self, outer):
                    super().__init__(timeout=30); self.outer = outer
                @discord.ui.select(placeholder="Choose a feed to edit...", options=options)
                async def sel(self, interaction, select):
                    idx = int(select.values[0])
                    await interaction.response.send_modal(EditMessageModal(self.outer.bot, self.outer.current_platform, idx, self.outer.config[self.outer.current_platform][idx], self.outer.bot.get_cog("SocialAlerts")._modal_edit_message))
            return await interaction.response.send_message("Select a feed to edit:", view=FeedSelect(self), ephemeral=True)
        
        idx = self.selected_index or 0
        await interaction.response.send_modal(EditMessageModal(self.bot, self.current_platform, idx, feeds[idx], self.bot.get_cog("SocialAlerts")._modal_edit_message))

    @discord.ui.button(label="Test", style=discord.ButtonStyle.secondary, emoji="🧪")
    async def test_btn(self, interaction, button):
        if not self.current_platform:
            return await interaction.response.send_message("Please select a platform first!", ephemeral=True)
        
        feeds = self.config.get(self.current_platform, [])
        if not feeds: return await interaction.response.send_message("No feeds to test.", ephemeral=True)
        
        feed = feeds[0]
        dummy_data = {
            "title": "Professional Content Title",
            "url": "https://horizen.systems",
            "author": feed.get('name', "Creator"),
            "image": self.bot.user.display_avatar.url,
            "extra": "🎮 Category: **Gaming**" if self.current_platform == "twitch" else None
        }
        await interaction.response.defer(ephemeral=True)
        await self.bot.get_cog("SocialAlerts")._dispatch_alert(interaction.guild, feed, self.current_platform, dummy_data, is_test=True)
        await interaction.followup.send(f"{self.bot.e.success} Test notification sent to <#{feed['discord_channel_id']}>!")

    @discord.ui.button(label="Variables", style=discord.ButtonStyle.secondary, emoji="🏷️")
    async def variables_btn(self, interaction, button):
        desc = (
            "### 🏷️ Notification Variables\n"
            "**General Content:**\n"
            "• `{title}` / `{contenttitle}` — The title of the post/video/tweet.\n"
            "• `{url}` / `{contenturl}` — Direct link to the new content.\n"
            "• `{id}` — Unique ID of the content.\n"
            "• `{icon}` — Platform emoji (e.g. 🔴).\n\n"
            "**Creator Info:**\n"
            "• `{channelname}` / `{author}` — Name of creator/subreddit.\n"
            "• `{channelurl}` — Link to profile/channel.\n"
            "• `{channelid}` — Social media account ID.\n\n"
            "**Server & Utility:**\n"
            "• `{mention}` / `{ping}` — Pings the assigned role.\n"
            "• `{guildname}` — This server's name.\n"
            "• `{membercount}` — Total member count.\n"
            "• `{timestamp}` — Absolute time.\n"
            "• `{relativetime}` — Relative time."
        )
        embed = self.bot.embed_manager.generic(description=desc, title="Alert Variables Guide")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Remove", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def remove_btn(self, interaction, button):
        if not self.current_platform:
            return await interaction.response.send_message("Please select a platform first!", ephemeral=True)
        
        feeds = self.config.get(self.current_platform, [])
        if not feeds: return await interaction.response.send_message("No feeds found.", ephemeral=True)

        if len(feeds) > 1 and self.selected_index is None:
            options = [discord.SelectOption(label=f"{i}. {f.get('name', f['channel_id'])}", value=str(i-1)) for i, f in enumerate(feeds)]
            class FeedRemove(discord.ui.View):
                def __init__(self, outer):
                    super().__init__(timeout=30); self.outer = outer
                @discord.ui.select(placeholder="Choose a feed to remove...", options=options)
                async def sel(self, interaction, select):
                    await self.outer.bot.get_cog("SocialAlerts")._process_remove(interaction, self.outer.current_platform, int(select.values[0]))
            return await interaction.response.send_message("Select a feed to remove:", view=FeedRemove(self), ephemeral=True)

        await self.bot.get_cog("SocialAlerts")._process_remove(interaction, self.current_platform, self.selected_index or 0)

class SocialAlerts(commands.Cog):
    category = 'utility'

    _TIMEOUT = aiohttp.ClientTimeout(total=15)

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager
        self.session = None
        self.twitch_token = None
        self.nitter_instances = ["nitter.net", "nitter.cz", "nitter.it", "nitter.privacydev.net"]

    async def cog_load(self):
        reddit_ua = "discord:HorizenBot:2.0 (by /u/HorizenSystems)"
        self.session = aiohttp.ClientSession(headers={"User-Agent": reddit_ua})
        await self._update_twitch_token()
        self.check_loop.start()

    def cog_unload(self):
        self.check_loop.cancel()
        if self.session:
            self.bot.loop.create_task(self.session.close())

    @tasks.loop(minutes=5)
    async def check_loop(self):
        all_configs = await self.db.find('social_alerts', {})
        for config in all_configs:
            guild_id = config['_id']
            guild = self.bot.get_guild(guild_id)
            if not guild:
                continue
            await self._process_youtube(guild, config)
            await self._process_twitch(guild, config)
            await self._process_reddit(guild, config)
            await self._process_twitter(guild, config)
            await asyncio.sleep(1)

    @check_loop.before_loop
    async def before_check_loop(self):
        await self.bot.wait_until_ready()

    async def _update_twitch_token(self):
        if not self.bot.config.TWITCH_CLIENT_ID or not self.bot.config.TWITCH_CLIENT_SECRET:
            return
        url = (
            f"https://id.twitch.tv/oauth2/token"
            f"?client_id={self.bot.config.TWITCH_CLIENT_ID}"
            f"&client_secret={self.bot.config.TWITCH_CLIENT_SECRET}"
            f"&grant_type=client_credentials"
        )
        try:
            async with self.session.post(url, timeout=self._TIMEOUT) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.twitch_token = data.get('access_token')
                else:
                    print(f"SocialAlerts: Twitch Token Update Failed ({resp.status})")
        except Exception as e:
            print(f"SocialAlerts: Twitch Error: {e}")

    async def _fetch_rss(self, url):
        try:
            async with self.session.get(url, timeout=self._TIMEOUT) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    return ET.fromstring(text)
        except ET.ParseError as e:
            print(f"SocialAlerts: RSS parse error for {url}: {e}")
        except Exception as e:
            print(f"SocialAlerts: RSS fetch error for {url}: {e}")
        return None

    async def _fetch_json(self, url, headers=None):
        try:
            async with self.session.get(url, timeout=self._TIMEOUT, headers=headers) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    print(f"SocialAlerts: HTTP {resp.status} for {url}")
        except Exception as e:
            print(f"SocialAlerts: JSON fetch error for {url}: {e}")
        return None

    async def _process_youtube(self, guild, config):
        feeds = config.get('youtube', [])
        changed = False
        for feed in feeds:
            root = await self._fetch_rss(f"https://www.youtube.com/feeds/videos.xml?channel_id={feed['channel_id']}")
            if root is None:
                continue
            
            namespace = {'ns': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}
            entries = root.findall('ns:entry', namespace)
            if not entries:
                continue

            latest = entries[0]
            v_id_el = latest.find('yt:videoId', namespace)
            if v_id_el is None:
                continue
            v_id = v_id_el.text
            if v_id != feed.get('last_id'):
                feed['last_id'] = v_id
                changed = True
                title_el = latest.find('ns:title', namespace)
                link_el = latest.find('ns:link', namespace)
                channel_title_el = root.find('ns:title', namespace)
                await self._dispatch_alert(guild, feed, "youtube", {
                    "title": title_el.text if title_el is not None else "New Video",
                    "url": link_el.attrib.get('href', '') if link_el is not None else '',
                    "author": channel_title_el.text if channel_title_el is not None else feed.get('name', feed['channel_id']),
                    "image": f"https://img.youtube.com/vi/{v_id}/maxresdefault.jpg"
                })
        if changed:
            await self.db.update_one('social_alerts', {'_id': guild.id}, {'youtube': feeds})

    async def _process_twitch(self, guild, config):
        if not self.twitch_token:
            return
        feeds = config.get('twitch', [])
        if not feeds:
            return
        
        changed = False
        headers = {
            "Client-ID": self.bot.config.TWITCH_CLIENT_ID,
            "Authorization": f"Bearer {self.twitch_token}"
        }
        
        for feed in feeds:
            data = await self._fetch_json(f"https://api.twitch.tv/helix/streams?user_login={feed['channel_id']}", headers)
            if not data:
                continue

            if data.get('status') == 401:
                await self._update_twitch_token()
                continue
            
            stream_list = data.get('data', [])
            if not stream_list:
                continue
            
            stream = stream_list[0]
            if stream['id'] != feed.get('last_id'):
                feed['last_id'] = stream['id']
                changed = True
                await self._dispatch_alert(guild, feed, "twitch", {
                    "title": stream['title'],
                    "url": f"https://twitch.tv/{stream['user_login']}",
                    "author": stream['user_name'],
                    "image": stream['thumbnail_url'].replace("{width}", "1280").replace("{height}", "720"),
                    "extra": f"🎮 Category: **{stream['game_name']}**"
                })
        if changed:
            await self.db.update_one('social_alerts', {'_id': guild.id}, {'twitch': feeds})

    async def _process_reddit(self, guild, config):
        feeds = config.get('reddit', [])
        changed = False
        for feed in feeds:
            data = await self._fetch_json(f"https://www.reddit.com/r/{feed['channel_id']}/new.json?limit=1")
            if not data:
                continue
            children = data.get('data', {}).get('children', [])
            if not children:
                continue
            
            post = children[0]['data']
            if post['id'] != feed.get('last_id'):
                feed['last_id'] = post['id']
                changed = True
                await self._dispatch_alert(guild, feed, "reddit", {
                    "title": post['title'][:200],
                    "url": f"https://reddit.com{post['permalink']}",
                    "author": f"u/{post['author']}",
                    "image": post.get('url') if post.get('post_hint') == 'image' else None,
                    "extra": f"🔖 Subreddit: **r/{feed['channel_id']}**"
                })
        if changed:
            await self.db.update_one('social_alerts', {'_id': guild.id}, {'reddit': feeds})

    async def _process_twitter(self, guild, config):
        feeds = config.get('twitter', [])
        changed = False
        instance = random.choice(self.nitter_instances)
        for feed in feeds:
            root = await self._fetch_rss(f"https://{instance}/{feed['channel_id']}/rss")
            if root is None:
                continue
            
            channel = root.find('channel')
            if channel is None:
                continue
            items = channel.findall('item')
            if not items:
                continue

            latest = items[0]
            guid_el = latest.find('guid')
            link_el = latest.find('link')
            t_id = (guid_el.text if guid_el is not None else None) or (link_el.text if link_el is not None else None)
            if not t_id:
                continue

            if t_id != feed.get('last_id'):
                feed['last_id'] = t_id
                changed = True
                desc_el = latest.find('description')
                desc_text = (desc_el.text or "View on Twitter") if desc_el is not None else "View on Twitter"
                await self._dispatch_alert(guild, feed, "twitter", {
                    "title": desc_text[:300].replace("<br>", "\n"),
                    "url": link_el.text if link_el is not None else f"https://twitter.com/{feed['channel_id']}",
                    "author": f"@{feed['channel_id']}",
                    "image": None
                })
        if changed:
            await self.db.update_one('social_alerts', {'_id': guild.id}, {'twitter': feeds})

    async def _dispatch_alert(self, guild, feed, platform, data, is_test=False):
        target_channel = guild.get_channel(feed['discord_channel_id'])
        if not target_channel:
            return

        color = AlertStyle.COLORS.get(platform, 0x2F3136)
        icon_url = AlertStyle.ICONS.get(platform)
        platform_emoji = {"youtube": "🔴", "twitch": "🟣", "reddit": "🟠", "twitter": "🔵"}.get(platform, "📡")
        cid = feed['channel_id']
        
        channel_urls = {
            "youtube": f"https://youtube.com/channel/{cid}",
            "twitch": f"https://twitch.tv/{cid}",
            "reddit": f"https://reddit.com/r/{cid}",
            "twitter": f"https://twitter.com/{cid}"
        }
        
        placeholders = {
            "mention": f"<@&{feed['role_id']}>" if feed.get('role_id') else "",
            "ping": f"<@&{feed['role_id']}>" if feed.get('role_id') else "",
            "author": data['author'],
            "channelname": data['author'],
            "title": data['title'],
            "contenttitle": data['title'],
            "url": data['url'],
            "contenturl": data['url'],
            "channelurl": channel_urls.get(platform, data['url']),
            "platform": platform.capitalize(),
            "guildname": guild.name,
            "membercount": f"{guild.member_count:,}",
            "timestamp": f"<t:{int(datetime.datetime.utcnow().timestamp())}:f>",
            "relativetime": f"<t:{int(datetime.datetime.utcnow().timestamp())}:R>",
            "channelid": cid,
            "id": data.get('id', 'N/A'),
            "icon": platform_emoji
        }
        
        embed = discord.Embed(color=color, timestamp=discord.utils.utcnow())
        embed.set_author(
            name=f"{data['author']} • {platform.capitalize()}{' (TEST)' if is_test else ''}",
            icon_url=icon_url,
            url=placeholders["channelurl"]
        )
        
        main_title = data['title']
        if len(main_title) > 250:
            main_title = main_title[:247] + "..."
        
        embed.title = f"✨ {main_title}"
        embed.url = data['url']
        
        info_fields = f"**Platform:** `{platform.capitalize()}`"
        if data.get('extra'):
            info_fields += f"\n{data['extra']}"
        
        embed.description = f"{info_fields}\n\n[Click here to view the content]({data['url']})"
        if data.get('image'):
            embed.set_image(url=data['image'])
        embed.set_footer(text=f"Horizen Systems • {platform.capitalize()} Intelligence", icon_url=self.bot.user.display_avatar.url)
        
        raw_msg = feed.get('message', "{mention} **{author}** is now available on **{platform}**!")
        try:
            formatted_msg = raw_msg.format(**placeholders)
        except Exception:
            formatted_msg = raw_msg
        
        try:
            await target_channel.send(content=formatted_msg, embed=embed)
        except discord.Forbidden:
            print(f"SocialAlerts: Missing permissions in {guild.name} (#{target_channel.name})")
        except Exception as e:
            print(f"SocialAlerts: Dispatch Error: {e}")

    @commands.group(name="alerts", aliases=["notifications", "notifs"], invoke_without_command=True, help="Open the Social Hub dashboard to manage platform notification feeds.")
    @commands.has_permissions(administrator=True)
    async def alerts_group(self, ctx):
        config = await self.db.find_one('social_alerts', {'_id': ctx.guild.id}) or {}
        view = AlertDashboard(self.bot, ctx.guild.id, config)
        await ctx.send(embed=view._build_embed(), view=view)

    @alerts_group.command(name="variables", aliases=["tags", "vars"], help="View all available dynamic tags for custom messages.")
    @commands.has_permissions(administrator=True)
    async def alerts_variables(self, ctx):
        desc = (
            "### 🏷️ Notification Variables\n"
            "Use these tags in your custom announcement messages to dynamically insert content.\n\n"
            "**General Content:**\n"
            "• `{title}` / `{contenttitle}` — The title of the post/video/tweet.\n"
            "• `{url}` / `{contenturl}` — Direct link to the new content.\n"
            "• `{id}` — Unique ID of the content (e.g. Video ID).\n"
            "• `{icon}` — Platform-specific emoji (e.g. 🔴 for YouTube).\n\n"
            "**Creator Info:**\n"
            "• `{channelname}` / `{author}` — Name of the creator or subreddit.\n"
            "• `{channelurl}` — Direct link to the creator's profile/channel.\n"
            "• `{channelid}` — The ID of the social media channel/account.\n\n"
            "**Server & Utility:**\n"
            "• `{mention}` / `{ping}` — Pings the assigned reward/notification role.\n"
            "• `{guildname}` — Name of this Discord server.\n"
            "• `{membercount}` — Total members in this server.\n"
            "• `{timestamp}` — Absolute time of the alert.\n"
            "• `{relativetime}` — Relative time (e.g. '5 minutes ago')."
        )
        await ctx.embed(desc, title="Alert Variables Guide")

    async def _modal_edit_message(self, interaction, platform, index, new_message):
        config = await self.db.find_one('social_alerts', {'_id': interaction.guild.id})
        feeds = config.get(platform, [])
        feeds[index]['message'] = new_message
        await self.db.update_one('social_alerts', {'_id': interaction.guild.id}, {platform: feeds}, upsert=True)
        await interaction.response.send_message(f"{self.bot.e.success} Custom message updated for **{platform.capitalize()}**!", ephemeral=True)

    async def _modal_add_feed(self, interaction, platform, cid, dch_id, role_id):
        try:
            dch_id = int(dch_id)
            rid = int(role_id) if role_id.strip() else None
        except Exception:
            return await interaction.response.send_message("Invalid Channel/Role ID. Must be numbers.", ephemeral=True)

        dch = interaction.guild.get_channel(dch_id)
        if not dch:
            return await interaction.response.send_message("Discord Channel not found.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        name = cid
        if platform == "youtube":
            root = await self._fetch_rss(f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}")
            if not root:
                return await interaction.followup.send("Invalid YouTube Channel ID.")
            title_el = root.find('{http://www.w3.org/2005/Atom}title')
            name = title_el.text if title_el is not None else cid
        elif platform == "reddit":
            data = await self._fetch_json(f"https://www.reddit.com/r/{cid}/about.json")
            if not data or 'error' in data:
                return await interaction.followup.send("Invalid Subreddit.")
            name = f"r/{cid}"

        config = await self.db.find_one('social_alerts', {'_id': interaction.guild.id}) or {}
        feeds = config.get(platform, [])
        if any(f['channel_id'] == cid for f in feeds):
            return await interaction.followup.send(f"Alerts for **{name}** are already setup.")
        
        feeds.append({
            'channel_id': cid,
            'name': name,
            'discord_channel_id': dch_id,
            'role_id': rid,
            'last_id': None,
            'message': "{mention} **{author}** is now available on **{platform}**!"
        })
        await self.db.update_one('social_alerts', {'_id': interaction.guild.id}, {platform: feeds}, upsert=True)
        await interaction.followup.send(f"{self.bot.e.success} Added **{platform.capitalize()}** alerts for **{name}**!")

    async def _process_remove(self, interaction, platform, index):
        config = await self.db.find_one('social_alerts', {'_id': interaction.guild.id})
        feeds = config.get(platform, [])
        removed = feeds.pop(index)
        await self.db.update_one('social_alerts', {'_id': interaction.guild.id}, {platform: feeds}, upsert=True)
        await interaction.response.send_message(
            f"{self.bot.e.success} Removed **{platform.capitalize()}** alerts for **{removed.get('name', removed['channel_id'])}**.",
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(SocialAlerts(bot))
