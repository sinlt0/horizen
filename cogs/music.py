import discord
from discord.ext import commands, tasks
import wavelink
import asyncio
import io
import time
import datetime
import math
import collections
from PIL import Image, ImageDraw, ImageFont, ImageFilter

class RateLimitManager:
    def __init__(self):
        self.limited = False
        self.retry_after = 0
        self.failures = 0

    def is_limited(self):
        now = time.time() * 1000
        if self.limited and now < self.retry_after:
            return True
        if self.limited and now >= self.retry_after:
            self.limited = False
            self.failures = 0
        return False

    def on_rate_limit(self, retry_after_ms=30000):
        self.limited = True
        self.failures += 1
        backoff = min(retry_after_ms * (2 ** (self.failures - 1)), 120000)
        self.retry_after = (time.time() * 1000) + backoff

    def on_success(self):
        self.failures = 0

class MusicPlayer(wavelink.Player):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.controller_msg = None
        self.is_247 = False
        self.loop_mode = "off"
        self.track_start_time = 0
        self.update_task = None
        self.rl_manager = RateLimitManager()
        self._last_update = 0

    def get_next(self):
        if self.loop_mode == "track": return self.current
        if self.queue.is_empty: return None
        track = self.queue.get()
        if self.loop_mode == "queue": self.queue.put(track)
        return track

class FilterMenuView(discord.ui.View):
    def __init__(self, bot, player):
        super().__init__(timeout=60)
        self.bot = bot
        self.player = player
        self.filter_select.options = [
            discord.SelectOption(label="Reset Filters", value="reset", emoji="🔄"),
            discord.SelectOption(label="Bassboost", value="bass", emoji=bot.e.volume_high),
            discord.SelectOption(label="Nightcore", value="night", emoji="⚡"),
            discord.SelectOption(label="Vaporwave", value="vapor", emoji="🌊"),
            discord.SelectOption(label="8D Audio", value="8d", emoji="🎧")
        ]

    @discord.ui.select(placeholder="🎛️ Choose an audio filter...")
    async def filter_select(self, interaction, select):
        val = select.values[0]
        filters = wavelink.Filters()
        if val == "bass": 
            bands = [wavelink.EqualizerBand(band=0, gain=0.3), wavelink.EqualizerBand(band=1, gain=0.25)]
            filters.equalizer = wavelink.Equalizer(bands=bands)
        elif val == "night": filters.timescale = wavelink.Timescale(speed=1.2, pitch=1.2)
        elif val == "vapor": filters.timescale = wavelink.Timescale(speed=0.8, pitch=0.8)
        elif val == "8d": filters.rotation = wavelink.Rotation(rotation_hz=0.2)
        await self.player.set_filters(filters)
        await interaction.response.send_message(f"{self.bot.e.music_filter} Applied: **{val.capitalize()}**", ephemeral=True)

class PlayerView(discord.ui.View):
    def __init__(self, bot, player):
        super().__init__(timeout=None)
        self.bot = bot
        self.player = player
        self.stop_btn.emoji = bot.e.stop
        self.pause_resume_btn.emoji = bot.e.play if player.paused else bot.e.pause
        self.skip_btn.emoji = bot.e.skip
        self.autoplay_btn.emoji = bot.e.autoplay
        self.autoplay_btn.style = discord.ButtonStyle.success if player.autoplay != wavelink.AutoPlayMode.disabled else discord.ButtonStyle.secondary
        self.loop_btn.emoji = bot.e.loop if player.loop_mode == "off" else bot.e.loop_one if player.loop_mode == "track" else bot.e.loop
        self.shuffle_btn.emoji = bot.e.shuffle
        self.filters_btn.emoji = bot.e.music_filter

    @discord.ui.button(style=discord.ButtonStyle.danger)
    async def stop_btn(self, interaction, button):
        self.player.queue.clear()
        await self.player.disconnect()
        await interaction.response.send_message(f"{self.bot.e.stop} Stopped.", ephemeral=True)

    @discord.ui.button(style=discord.ButtonStyle.secondary)
    async def pause_resume_btn(self, interaction, button):
        await self.player.pause(not self.player.paused)
        button.emoji = self.bot.e.play if self.player.paused else self.bot.e.pause
        await interaction.response.edit_message(view=self)

    @discord.ui.button(style=discord.ButtonStyle.secondary)
    async def skip_btn(self, interaction, button):
        await self.player.skip()
        await interaction.response.send_message(f"{self.bot.e.skip} Skipped.", ephemeral=True)

    @discord.ui.button(style=discord.ButtonStyle.secondary)
    async def autoplay_btn(self, interaction, button):
        if self.player.autoplay == wavelink.AutoPlayMode.disabled:
            self.player.autoplay = wavelink.AutoPlayMode.enabled
            button.style = discord.ButtonStyle.success
        else:
            self.player.autoplay = wavelink.AutoPlayMode.disabled
            button.style = discord.ButtonStyle.secondary
        await interaction.response.edit_message(view=self)

    @discord.ui.button(style=discord.ButtonStyle.secondary)
    async def loop_btn(self, interaction, button):
        modes = ["off", "track", "queue"]
        idx = (modes.index(self.player.loop_mode) + 1) % len(modes)
        self.player.loop_mode = modes[idx]
        button.emoji = self.bot.e.loop if self.player.loop_mode == "off" else self.bot.e.loop_one if self.player.loop_mode == "track" else self.bot.e.loop
        await interaction.response.edit_message(view=self)

    @discord.ui.button(style=discord.ButtonStyle.secondary)
    async def shuffle_btn(self, interaction, button):
        self.player.queue.shuffle()
        await interaction.response.send_message(f"{self.bot.e.shuffle} Shuffled queue.", ephemeral=True)

    @discord.ui.button(style=discord.ButtonStyle.secondary)
    async def filters_btn(self, interaction, button):
        view = FilterMenuView(self.bot, self.player)
        await interaction.response.send_message("Audio Filters:", view=view, ephemeral=True)

class LofiSelectView(discord.ui.View):
    def __init__(self, bot, ctx, custom_stations=None):
        super().__init__(timeout=60)
        self.bot = bot
        self.ctx = ctx
        
        options = []
        for name in bot.config.LOFI_STATIONS.keys():
            options.append(discord.SelectOption(label=name, value=f"default:{name}", emoji=bot.e.lofi))
        
        if custom_stations:
            for name in custom_stations.keys():
                options.append(discord.SelectOption(label=f"⭐ {name}", value=f"custom:{name}", description="Guild Custom Station"))
        
        self.station_select.options = options[:25]

    @discord.ui.select(placeholder="🎧 Select a Lo-Fi Station...")
    async def station_select(self, interaction, select):
        val = select.values[0]
        type, station_name = val.split(":", 1)
        
        if type == "default":
            url = self.bot.config.LOFI_STATIONS[station_name]
        else:
            config = await self.bot.db_manager.find_one('music_config', {'_id': interaction.guild.id})
            url = config.get('custom_lofi', {}).get(station_name)
        
        if not url:
            return await interaction.response.send_message("Station not found.", ephemeral=True)
        
        if not interaction.user.voice:
            return await interaction.response.send_message("Join a voice channel first!", ephemeral=True)
        
        node = self.bot.get_cog("Music")._get_best_node()
        if not node:
            return await interaction.response.send_message("All music servers are offline.", ephemeral=True)
            
        p: MusicPlayer = interaction.guild.voice_client or await interaction.user.voice.channel.connect(cls=MusicPlayer, timeout=30.0, node=node)
        
        await interaction.response.defer()
        tracks = await wavelink.Playable.search(url)
        if not tracks:
            return await interaction.followup.send("Failed to load stream.", ephemeral=True)
            
        t = tracks[0]
        t.ctx, t.requester = self.ctx, interaction.user
        p.is_247 = True
        await p.play(t)
        
        await interaction.followup.send(f"{self.bot.e.lofi} **{station_name}** started! 24/7 mode enabled.")
        await interaction.message.delete()

class Music(commands.Cog):
    category = "music"

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager
        self.bot.loop.create_task(self._start_nodes())
        self.node_monitor.start()

    def cog_unload(self):
        self.node_monitor.cancel()

    async def _start_nodes(self):
        await self.bot.wait_until_ready()
        nodes = []
        for n in self.bot.config.LAVALINK_NODES:
            try:
                scheme = "https" if n.get('secure') else "http"
                uri = f"{scheme}://{n['host']}:{n['port']}"
                
                node = wavelink.Node(
                    uri=uri, 
                    password=n['password'], 
                    identifier=n['identifier'],
                    retries=999999
                )
                nodes.append(node)
                
            except Exception as e:
                print(f"Lavalink: Failed to setup node object '{n.get('identifier')}': {e}")

        if nodes:
            try:
                await wavelink.Pool.connect(nodes=nodes, client=self.bot, cache_capacity=100)
            except Exception as e:
                print(f"Lavalink Pool: Failed to connect nodes: {e}")

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        print(f"Lavalink Node '{payload.node.identifier}' ready.")

    @tasks.loop(minutes=5)
    async def node_monitor(self):
        for node in wavelink.Pool.nodes.values():
            if node.status != wavelink.NodeStatus.CONNECTED:
                print(f"WARNING: Lavalink Node '{node.identifier}' is currently {node.status.name}.")

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        player: MusicPlayer = payload.player
        if player.update_task: player.update_task.cancel()
        if player.controller_msg:
            try: await player.controller_msg.delete()
            except: pass
            player.controller_msg = None
        player.track_start_time = time.time() * 1000
        await self._update_controller(player)
        player.update_task = self.bot.loop.create_task(self._controller_loop(player))

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        player = payload.player
        if player.update_task: player.update_task.cancel()
        
        next_track = player.get_next()
        if next_track: 
            await player.play(next_track)
        elif player.autoplay != wavelink.AutoPlayMode.disabled:
            try:
                res = await payload.track.get_recommendations()
                if res: await player.play(res[0])
            except: pass
        elif player.is_247:
            await player.play(payload.track)
        else:
            await asyncio.sleep(60)
            if not player.playing: await player.disconnect()

    async def _controller_loop(self, player):
        while player.playing:
            if player.paused or not player.playing:
                await asyncio.sleep(5); continue
            if player.rl_manager.is_limited():
                await asyncio.sleep(10); continue
            if time.time() - player._last_update < 20:
                await asyncio.sleep(5); continue
            await self._update_controller(player)
            await asyncio.sleep(20)

    async def _update_controller(self, player):
        if not player.current: return
        try:
            embed = self.bot.embed_manager.generic(description="", title=f"{self.bot.e.play} Now Playing")
            card = await self._generate_music_card(player)
            embed.set_image(url="attachment://music-card.png")
            
            view = PlayerView(self.bot, player)
            if player.controller_msg:
                try: 
                    await player.controller_msg.edit(embed=embed, view=view, attachments=[card])
                    player.rl_manager.on_success()
                except discord.HTTPException as e:
                    if e.status == 429: player.rl_manager.on_rate_limit(e.retry_after * 1000)
                    else: player.controller_msg = None
            else:
                track = player.current
                if hasattr(track, 'ctx'):
                    player.controller_msg = await track.ctx.send(embed=embed, view=view, file=card)
                    player._last_update = time.time()
        except: pass

    async def _generate_music_card(self, player):
        track = player.current
        width, height = 800, 300
        canvas = Image.new('RGB', (width, height), (20, 20, 20))
        draw = ImageDraw.Draw(canvas)
        
        try:
            async with self.bot.session.get(track.artwork or "") as r:
                if r.status == 200:
                    art = Image.open(io.BytesIO(await r.read())).resize((200, 200))
                    canvas.paste(art, (50, 50))
        except: pass
        
        draw.text((300, 50), track.title[:40], fill=(255, 255, 255))
        draw.text((300, 100), track.author, fill=(200, 200, 200))
        
        pos = player.position
        dur = track.length
        pct = pos / dur if dur > 0 else 0
        bx, by, bw, bh = 300, 200, 450, 10
        draw.rounded_rectangle([bx, by, bx + bw, by + bh], 4, (60, 60, 60))
        draw.rounded_rectangle([bx, by, bx + (bw * pct), by + bh], 4, (138, 99, 255))
        
        buf = io.BytesIO()
        canvas.save(buf, format="PNG")
        buf.seek(0)
        return discord.File(buf, "music-card.png")

    def _get_best_node(self):
        nodes = [n for n in wavelink.Pool.nodes.values() if n.status == wavelink.NodeStatus.CONNECTED]
        if not nodes: return None
        return sorted(nodes, key=lambda n: (len(n.players), n.heartbeat_latency))[0]

    @commands.command(name="mplay", aliases=["p"])
    async def play(self, ctx, *, query: str):
        if not ctx.author.voice: return await self.bot.error("Join VC.")
        
        node = self._get_best_node()
        if not node: return await self.bot.error("All music servers are currently offline.")
        
        try:
            player: MusicPlayer = ctx.voice_client or await ctx.author.voice.channel.connect(cls=MusicPlayer, timeout=30.0, node=node)
        except Exception as e:
            return await self.bot.error(f"Failed to connect to music server: {e}")

        if not query.startswith(("http", "ytsearch:", "scsearch:", "ytmsearch:")): query = f"ytmsearch:{query}"
        
        res = await wavelink.Playable.search(query)
        if not res: return await self.bot.error("No results found.")
        
        if isinstance(res, wavelink.Playlist):
            for t in res.tracks: t.ctx, t.requester = ctx, ctx.author; player.queue.put(t)
            await ctx.success(f"Added playlist **{res.name}** ({len(res.tracks)} tracks)")
        else:
            track = res[0]
            track.ctx, track.requester = ctx, ctx.author
            if not player.playing: await player.play(track)
            else: player.queue.put(track); await ctx.success(f"Added **{track.title}** to queue.")

    @commands.command(name="mstop")
    async def stop(self, ctx):
        if ctx.voice_client: ctx.voice_client.queue.clear(); await ctx.voice_client.disconnect(); await ctx.success(f"{self.bot.e.stop} Stopped.")

    @commands.command(name="mskip", aliases=["s"])
    async def skip(self, ctx):
        if ctx.voice_client: await ctx.voice_client.skip(); await ctx.success(f"{self.bot.e.skip} Skipped.")

    @commands.command(name="mvolume", aliases=["vol"])
    async def volume(self, ctx, vol: int):
        if ctx.voice_client: await ctx.voice_client.set_volume(vol); await ctx.success(f"Volume set to `{vol}%`.")

    @commands.command(name="mloop")
    async def loop(self, ctx, mode: str = "off"):
        if ctx.voice_client:
            mode = mode.lower()
            if mode not in ["off", "track", "queue"]: return await ctx.error("Invalid mode: off, track, queue")
            ctx.voice_client.loop_mode = mode
            await ctx.success(f"Loop mode set to `{mode}`.")

    @commands.command(name="mautoplay")
    async def autoplay(self, ctx):
        if ctx.voice_client:
            p = ctx.voice_client
            p.autoplay = wavelink.AutoPlayMode.enabled if p.autoplay == wavelink.AutoPlayMode.disabled else wavelink.AutoPlayMode.disabled
            await ctx.success(f"Autoplay is now `{'Enabled' if p.autoplay != wavelink.AutoPlayMode.disabled else 'Disabled'}`.")

    @commands.command(name="mqueue", aliases=["q"])
    async def queue(self, ctx):
        if not ctx.voice_client: return
        p = ctx.voice_client
        if p.queue.is_empty: return await ctx.info("The queue is empty.")
        
        desc = "\n".join([f"`{i+1}.` {t.title}" for i, t in enumerate(p.queue[:15])])
        await self.bot.embed(desc, title="Queue")

    @commands.command(name="msearch")
    async def search(self, ctx, *, query: str):
        if not ctx.author.voice: return await self.bot.error("Join VC.")
        
        node = self._get_best_node()
        if not node: return await self.bot.error("All music servers are currently offline.")

        player: MusicPlayer = ctx.voice_client or await ctx.author.voice.channel.connect(cls=MusicPlayer, timeout=30.0, node=node)
        res = await wavelink.Playable.search(query)
        if not res: return await self.bot.error("No results.")
        options = [discord.SelectOption(label=f"{i+1}. {t.title[:50]}", value=str(i), emoji=self.bot.e.music_note) for i, t in enumerate(res[:10])]
        class SearchView(discord.ui.View):
            def __init__(self, tracks, player):
                super().__init__(timeout=30); self.tracks, self.player, self.msg = tracks, player, None
            @discord.ui.select(options=options)
            async def sel(self, interaction, select):
                t = self.tracks[int(select.values[0])]; t.ctx, t.requester = ctx, interaction.user
                if not self.player.playing: await self.player.play(t); await interaction.response.send_message(f"Playing {t.title}")
                else: self.player.queue.put(t); await interaction.response.send_message(f"Added {t.title}")
                await self.msg.delete()
        v = SearchView(res[:10], player); v.msg = await ctx.send("Choose:", view=v)

    @commands.command(name="m247")
    async def m247(self, ctx):
        if ctx.voice_client: ctx.voice_client.is_247 = not ctx.voice_client.is_247; await ctx.success(f"24/7 mode is now `{'Enabled' if ctx.voice_client.is_247 else 'Disabled'}`.")

    @commands.group(name="mlofi", aliases=["lofi"], invoke_without_command=True)
    async def lofi_group(self, ctx): await ctx.send_help(ctx.command)

    @lofi_group.command(name="on", help="Start 24/7 Lo-Fi with station selection.")
    async def lofi_on(self, ctx):
        if not ctx.author.voice: return await self.bot.error("Join a voice channel first.")
        
        node = self._get_best_node()
        if not node: return await self.bot.error("All music servers are currently offline.")
        
        config = await self.db.find_one('music_config', {'_id': ctx.guild.id}) or {}
        custom = config.get('custom_lofi', {})
        
        view = LofiSelectView(self.bot, ctx, custom_stations=custom)
        await ctx.send("### 🎧 Horizen Lo-Fi Radio\nSelect a station to start 24/7 playback:", view=view)

    @lofi_group.command(name="add", help="Add a custom 24/7 Lo-Fi station/playlist.")
    @commands.has_permissions(manage_guild=True)
    async def lofi_add(self, ctx, name: str, url: str):
        if len(name) > 20: return await ctx.error("Name must be under 20 characters.")
        
        tracks = await wavelink.Playable.search(url)
        if not tracks: return await ctx.error("Invalid URL or no tracks found.")
        
        await self.db.update_one('music_config', {'_id': ctx.guild.id}, {'$set': {f'custom_lofi.{name}': url}}, upsert=True)
        await ctx.success(f"Added custom station: **{name}**")

    @lofi_group.command(name="remove", help="Remove a custom Lo-Fi station.")
    @commands.has_permissions(manage_guild=True)
    async def lofi_remove(self, ctx, *, name: str):
        await self.db.update_one('music_config', {'_id': ctx.guild.id}, {'$unset': {f'custom_lofi.{name}': ""}})
        await ctx.success(f"Removed custom station: **{name}**")

    @lofi_group.command(name="list", help="List all Lo-Fi stations.")
    async def lofi_list(self, ctx):
        config = await self.db.find_one('music_config', {'_id': ctx.guild.id}) or {}
        custom = config.get('custom_lofi', {})
        
        desc = "**Default Stations:**\n" + "\n".join([f"• {n}" for n in self.bot.config.LOFI_STATIONS.keys()])
        if custom:
            desc += "\n\n**Custom Stations:**\n" + "\n".join([f"• {n}" for n in custom.keys()])
            
        await self.bot.embed(desc, title="Lo-Fi Radio Stations")

    @lofi_group.command(name="off", help="Stop Lo-Fi.")
    async def lofi_off(self, ctx):
        if ctx.voice_client: await ctx.voice_client.disconnect(); await ctx.success(f"{self.bot.e.stop} Lo-Fi Stopped.")

    @lofi_group.command(name="setchannel", help="Set dedicated Lo-Fi channel.")
    @commands.has_permissions(manage_guild=True)
    async def lofi_setchannel(self, ctx, channel: discord.VoiceChannel):
        await self.db.update_one('music_config', {'_id': ctx.guild.id}, {'lofi_channel': channel.id}, upsert=True)
        await ctx.success(f"Dedicated Lo-Fi channel set to {channel.mention}")

    @commands.group(name="mplaylist", aliases=["mpl", "playlist"], invoke_without_command=True, help="Manage your personal music playlists.")
    async def playlist_group(self, ctx):
        await ctx.send_help(ctx.command)

    @playlist_group.command(name="create", help="Create a new empty playlist.")
    async def playlist_create(self, ctx, *, name: str):
        if len(name) > 30: return await ctx.error("Playlist name too long.")
        
        user_data = await self.db.find_one('user_playlists', {'_id': ctx.author.id}) or {'playlists': {}}
        if name in user_data['playlists']:
            return await ctx.error(f"You already have a playlist named **{name}**.")
            
        user_data['playlists'][name] = []
        await self.db.update_one('user_playlists', {'_id': ctx.author.id}, user_data, upsert=True)
        await ctx.success(f"Created playlist: **{name}**")

    @playlist_group.command(name="add", help="Add the current song or a search query to a playlist.")
    async def playlist_add(self, ctx, playlist_name: str, *, query: str = None):
        user_data = await self.db.find_one('user_playlists', {'_id': ctx.author.id})
        if not user_data or playlist_name not in user_data['playlists']:
            return await ctx.error(f"Playlist **{playlist_name}** not found.")

        if not query:
            if not ctx.voice_client or not ctx.voice_client.current:
                return await ctx.error("Nothing is playing. Provide a search query.")
            track = ctx.voice_client.current
            track_data = {"title": track.title, "uri": track.uri, "author": track.author, "length": track.length}
        else:
            res = await wavelink.Playable.search(query)
            if not res: return await self.bot.error("No results found.")
            track = res[0]
            track_data = {"title": track.title, "uri": track.uri, "author": track.author, "length": track.length}

        user_data['playlists'][playlist_name].append(track_data)
        await self.db.update_one('user_playlists', {'_id': ctx.author.id}, user_data, upsert=True)
        await ctx.success(f"Added **{track_data['title']}** to **{playlist_name}**")

    @playlist_group.command(name="remove", help="Remove a song from a playlist by its index.")
    async def playlist_remove(self, ctx, playlist_name: str, index: int):
        user_data = await self.db.find_one('user_playlists', {'_id': ctx.author.id})
        if not user_data or playlist_name not in user_data['playlists']:
            return await ctx.error(f"Playlist **{playlist_name}** not found.")
            
        playlist = user_data['playlists'][playlist_name]
        if index < 1 or index > len(playlist):
            return await ctx.error("Invalid index.")
            
        removed = playlist.pop(index - 1)
        await self.db.update_one('user_playlists', {'_id': ctx.author.id}, user_data, upsert=True)
        await ctx.success(f"Removed **{removed['title']}** from **{playlist_name}**")

    @playlist_group.command(name="delete", help="Delete an entire playlist.")
    async def playlist_delete(self, ctx, *, name: str):
        user_data = await self.db.find_one('user_playlists', {'_id': ctx.author.id})
        if not user_data or name not in user_data['playlists']:
            return await ctx.error(f"Playlist **{name}** not found.")
            
        del user_data['playlists'][name]
        await self.db.update_one('user_playlists', {'_id': ctx.author.id}, user_data, upsert=True)
        await ctx.success(f"Deleted playlist: **{name}**")

    @playlist_group.command(name="list", help="List all your playlists or songs in a playlist.")
    async def playlist_list(self, ctx, *, name: str = None):
        user_data = await self.db.find_one('user_playlists', {'_id': ctx.author.id})
        if not user_data or not user_data.get('playlists'):
            return await ctx.info("You don't have any playlists.")
            
        if not name:
            desc = "\n".join([f"• **{n}** ({len(p)} tracks)" for n, p in user_data['playlists'].items()])
            return await self.bot.embed(desc, title=f"{ctx.author.name}'s Playlists")
            
        if name not in user_data['playlists']:
            return await ctx.error(f"Playlist **{name}** not found.")
            
        playlist = user_data['playlists'][name]
        if not playlist: return await ctx.info(f"Playlist **{name}** is empty.")
        
        desc = "\n".join([f"`{i+1}.` [{t['title']}]({t['uri']})" for i, t in enumerate(playlist[:20])])
        if len(playlist) > 20: desc += f"\n*... and {len(playlist) - 20} more*"
        await self.bot.embed(desc, title=f"Playlist: {name}")

    @playlist_group.command(name="load", aliases=["play"], help="Load and play a playlist.")
    async def playlist_load(self, ctx, *, name: str):
        if not ctx.author.voice: return await self.bot.error("Join a voice channel.")
        
        node = self._get_best_node()
        if not node: return await self.bot.error("All music servers are currently offline.")

        user_data = await self.db.find_one('user_playlists', {'_id': ctx.author.id})
        if not user_data or name not in user_data['playlists']:
            return await ctx.error(f"Playlist **{name}** not found.")
            
        tracks_data = user_data['playlists'][name]
        if not tracks_data: return await ctx.error("Playlist is empty.")
        
        player: MusicPlayer = ctx.voice_client or await ctx.author.voice.channel.connect(cls=MusicPlayer, timeout=30.0, node=node)
        
        count = 0
        first_track = None
        for data in tracks_data:
            res = await wavelink.Playable.search(data['uri'])
            if res:
                track = res[0]
                track.ctx, track.requester = ctx, ctx.author
                if not player.playing and not first_track:
                    first_track = track
                else:
                    player.queue.put(track)
                count += 1
        
        if first_track:
            await player.play(first_track)
            
        await ctx.success(f"Loaded **{count}** tracks from playlist **{name}**")

    @commands.command(name="mjoin")
    async def join(self, ctx):
        if not ctx.author.voice: return await self.bot.error("Join VC.")
        node = self._get_best_node()
        if not node: return await self.bot.error("All music servers are currently offline.")
        await ctx.author.voice.channel.connect(cls=MusicPlayer, timeout=30.0, node=node)
        await ctx.success(f"{self.bot.e.play} Joined {ctx.author.voice.channel.mention}")

    @commands.command(name="mleave")
    async def leave(self, ctx):
        if ctx.voice_client: await ctx.voice_client.disconnect(); await ctx.success(f"{self.bot.e.stop} Disconnected.")

    def _format_ms(self, ms):
        s = int(ms / 1000); m, s = divmod(s, 60); h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"

async def setup(bot):
    await bot.add_cog(Music(bot))
