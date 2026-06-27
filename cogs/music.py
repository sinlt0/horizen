import discord
from discord.ext import commands, tasks
import wavelink
import asyncio
import aiohttp
import io
import time
import datetime
from PIL import Image, ImageDraw


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
        self.track_start_time = 0
        self.update_task = None
        self.rl_manager = RateLimitManager()
        self._last_update = 0
        self.ctx = None


class FilterMenuView(discord.ui.View):
    def __init__(self, bot, player):
        super().__init__(timeout=60)
        self.bot = bot
        self.player = player
        self.filter_select.options = [
            discord.SelectOption(label="Reset Filters", value="reset", emoji="🔄"),
            discord.SelectOption(label="Bassboost", value="bass", emoji=bot.e.volume_high),
            discord.SelectOption(label="Nightcore", value="nightcore", emoji="⚡"),
            discord.SelectOption(label="Vaporwave", value="vaporwave", emoji="🌊"),
            discord.SelectOption(label="8D Audio", value="8d", emoji="🎧"),
        ]

    @discord.ui.select(placeholder="🎛️ Choose an audio filter...")
    async def filter_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        val = select.values[0]
        filters = wavelink.Filters()
        if val == "bass":
            filters.equalizer.set(bands=[
                {"band": 0, "gain": 0.3},
                {"band": 1, "gain": 0.25},
                {"band": 2, "gain": 0.2},
            ])
        elif val == "nightcore":
            filters.timescale.set(speed=1.2, pitch=1.2, rate=1.0)
        elif val == "vaporwave":
            filters.timescale.set(speed=0.8, pitch=0.8, rate=1.0)
        elif val == "8d":
            filters.rotation.set(rotation_hz=0.2)
        await self.player.set_filters(filters)
        label = val.capitalize() if val != "reset" else "Filters Reset"
        await interaction.response.send_message(f"{self.bot.e.music_filter} Applied: **{label}**", ephemeral=True)


class PlayerView(discord.ui.View):
    def __init__(self, bot, player):
        super().__init__(timeout=None)
        self.bot = bot
        self.player = player
        self.stop_btn.emoji = bot.e.stop
        self.pause_resume_btn.emoji = bot.e.pause if not player.paused else bot.e.resume
        self.skip_btn.emoji = bot.e.skip
        self.shuffle_btn.emoji = bot.e.shuffle
        self.loop_btn.emoji = bot.e.loop_one if player.queue.mode == wavelink.QueueMode.loop else bot.e.loop
        self.filters_btn.emoji = bot.e.music_filter
        self.autoplay_btn.emoji = bot.e.autoplay
        self.autoplay_btn.style = (
            discord.ButtonStyle.success
            if player.autoplay != wavelink.AutoPlayMode.disabled
            else discord.ButtonStyle.secondary
        )

    def _alive(self):
        return self.player and self.player.connected

    @discord.ui.button(style=discord.ButtonStyle.danger)
    async def stop_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self._alive():
            return await interaction.response.send_message("Player not active.", ephemeral=True)
        self.player.queue.clear()
        await self.player.disconnect()
        await interaction.response.send_message(f"{self.bot.e.stop} Stopped.", ephemeral=True)

    @discord.ui.button(style=discord.ButtonStyle.secondary)
    async def pause_resume_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self._alive():
            return await interaction.response.send_message("Player not active.", ephemeral=True)
        await self.player.pause(not self.player.paused)
        button.emoji = self.bot.e.resume if self.player.paused else self.bot.e.pause
        await interaction.response.edit_message(view=self)

    @discord.ui.button(style=discord.ButtonStyle.secondary)
    async def skip_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self._alive():
            return await interaction.response.send_message("Player not active.", ephemeral=True)
        await self.player.skip()
        await interaction.response.send_message(f"{self.bot.e.skip} Skipped.", ephemeral=True)

    @discord.ui.button(style=discord.ButtonStyle.secondary)
    async def shuffle_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self._alive():
            return await interaction.response.send_message("Player not active.", ephemeral=True)
        self.player.queue.shuffle()
        await interaction.response.send_message(f"{self.bot.e.shuffle} Queue shuffled.", ephemeral=True)

    @discord.ui.button(style=discord.ButtonStyle.secondary)
    async def loop_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self._alive():
            return await interaction.response.send_message("Player not active.", ephemeral=True)
        modes = [wavelink.QueueMode.normal, wavelink.QueueMode.loop, wavelink.QueueMode.loop_all]
        labels = ["Off", "Track", "Queue"]
        current = self.player.queue.mode
        idx = (modes.index(current) + 1) % len(modes)
        self.player.queue.mode = modes[idx]
        button.emoji = self.bot.e.loop_one if modes[idx] == wavelink.QueueMode.loop else self.bot.e.loop
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(f"{self.bot.e.loop} Loop: **{labels[idx]}**", ephemeral=True)

    @discord.ui.button(style=discord.ButtonStyle.secondary)
    async def filters_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self._alive():
            return await interaction.response.send_message("Player not active.", ephemeral=True)
        view = FilterMenuView(self.bot, self.player)
        await interaction.response.send_message(f"{self.bot.e.music_filter} Audio Filters:", view=view, ephemeral=True)

    @discord.ui.button(style=discord.ButtonStyle.secondary)
    async def autoplay_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self._alive():
            return await interaction.response.send_message("Player not active.", ephemeral=True)
        if self.player.autoplay == wavelink.AutoPlayMode.disabled:
            self.player.autoplay = wavelink.AutoPlayMode.enabled
            button.style = discord.ButtonStyle.success
            label = "Enabled"
        else:
            self.player.autoplay = wavelink.AutoPlayMode.disabled
            button.style = discord.ButtonStyle.secondary
            label = "Disabled"
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(f"{self.bot.e.autoplay} AutoPlay: **{label}**", ephemeral=True)


FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

class LofiPlayer:
    def __init__(self, voice_client: discord.VoiceClient, station_name: str, url: str):
        self.voice_client = voice_client
        self.station_name = station_name
        self.url = url

    def is_playing(self):
        return self.voice_client.is_playing() or self.voice_client.is_paused()

    async def stop(self):
        if self.voice_client.is_playing() or self.voice_client.is_paused():
            self.voice_client.stop()
        if self.voice_client.is_connected():
            await self.voice_client.disconnect()


class LofiSelectView(discord.ui.View):
    def __init__(self, bot, ctx, custom_stations=None):
        super().__init__(timeout=60)
        self.bot = bot
        self.ctx = ctx
        options = [
            discord.SelectOption(label=name, value=f"default:{name}", emoji=bot.e.lofi)
            for name in bot.config.LOFI_STATIONS.keys()
        ]
        if custom_stations:
            for name in custom_stations.keys():
                options.append(discord.SelectOption(label=f"⭐ {name}", value=f"custom:{name}", description="Custom Station"))
        self.station_select.options = options[:25]

    @discord.ui.select(placeholder="🎧 Select a Lo-Fi Station...")
    async def station_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        val = select.values[0]
        kind, station_name = val.split(":", 1)

        if kind == "default":
            url = self.bot.config.LOFI_STATIONS.get(station_name)
        else:
            config = await self.bot.db_manager.find_one('music_config', {'_id': interaction.guild.id})
            url = (config or {}).get('custom_lofi', {}).get(station_name)

        if not url:
            return await interaction.response.send_message("Station not found.", ephemeral=True)
        if not interaction.user.voice:
            return await interaction.response.send_message("Join a voice channel first!", ephemeral=True)

        music_cog = self.bot.get_cog("Music")

        if music_cog._lofi_players.get(interaction.guild.id):
            old = music_cog._lofi_players[interaction.guild.id]
            await old.stop()

        await interaction.response.defer()

        try:
            vc = await interaction.user.voice.channel.connect(self_deaf=True)
        except discord.ClientException:
            vc = interaction.guild.voice_client
            if vc:
                try:
                    await vc.move_to(interaction.user.voice.channel)
                except Exception:
                    pass

        if not vc:
            return await interaction.followup.send("Failed to connect to voice channel.", ephemeral=True)

        stream_url = url
        if "youtube.com" in url or "youtu.be" in url:
            try:
                import yt_dlp
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'quiet': True,
                    'no_warnings': True,
                    'source_address': '0.0.0.0',
                    'live_from_start': False,
                    'noplaylist': True,
                }
                loop = asyncio.get_event_loop()
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))

                if info.get('is_live') or info.get('was_live'):
                    formats = [
                        f for f in info.get('formats', [])
                        if f.get('acodec') != 'none'
                        and f.get('vcodec') == 'none'
                        and f.get('protocol') in ('https', 'http', 'm3u8_native', 'm3u8')
                    ]
                    if not formats:
                        formats = [f for f in info.get('formats', []) if f.get('acodec') != 'none']
                    if not formats:
                        return await interaction.followup.send("No audio stream found in this YouTube URL.", ephemeral=True)
                    formats.sort(key=lambda f: f.get('abr') or 0, reverse=True)
                    stream_url = formats[0]['url']
                else:
                    stream_url = info.get('url')
                    if not stream_url:
                        formats = [f for f in info.get('formats', []) if f.get('acodec') != 'none']
                        if not formats:
                            return await interaction.followup.send("No audio stream found in this YouTube URL.", ephemeral=True)
                        stream_url = formats[0]['url']
            except Exception as e:
                return await interaction.followup.send(f"Failed to extract YouTube stream: {e}", ephemeral=True)

        try:
            source = discord.FFmpegPCMAudio(stream_url, **FFMPEG_OPTIONS)
            source = discord.PCMVolumeTransformer(source, volume=0.5)
            vc.play(source)
        except Exception as e:
            return await interaction.followup.send(f"Failed to start playback: {e}", ephemeral=True)

        lofi_player = LofiPlayer(vc, station_name, url)
        music_cog._lofi_players[interaction.guild.id] = lofi_player
        await music_cog._save_lofi_state(interaction.guild.id, station_name, url, vc.channel.id)

        await interaction.followup.send(f"{self.bot.e.lofi} **{station_name}** started — 24/7 mode enabled.")
        try:
            await interaction.message.delete()
        except Exception:
            pass


class Music(commands.Cog):
    category = "music"

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager
        self._session = None
        self._lofi_players = {}

    async def cog_load(self):
        self._session = aiohttp.ClientSession()
        self.bot.loop.create_task(self._start_nodes())
        self.bot.loop.create_task(self._restore_sessions())
        self.node_monitor.start()

    def cog_unload(self):
        self.node_monitor.cancel()
        if self._session:
            self.bot.loop.create_task(self._session.close())

    async def _save_247_state(self, guild_id: int, enabled: bool, voice_channel_id: int = None, text_channel_id: int = None):
        if enabled:
            await self.db.update_one('music_config', {'_id': guild_id}, {
                'vc247_active': True,
                'vc247_channel': voice_channel_id,
                'vc247_text_channel': text_channel_id
            }, upsert=True)
        else:
            await self.db.update_one('music_config', {'_id': guild_id}, {
                'vc247_active': False,
                'vc247_channel': None,
                'vc247_text_channel': None
            }, upsert=True)

    async def _save_lofi_state(self, guild_id: int, station_name: str = None, url: str = None, voice_channel_id: int = None):
        if station_name and url and voice_channel_id:
            await self.db.update_one('music_config', {'_id': guild_id}, {
                'lofi_active': True,
                'lofi_station': station_name,
                'lofi_url': url,
                'lofi_voice_channel': voice_channel_id
            }, upsert=True)
        else:
            await self.db.update_one('music_config', {'_id': guild_id}, {
                'lofi_active': False,
                'lofi_station': None,
                'lofi_url': None,
                'lofi_voice_channel': None
            }, upsert=True)

    async def _restore_sessions(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(5)

        configs = await self.db.find('music_config', {})
        for config in configs:
            guild_id = config.get('_id')
            guild = self.bot.get_guild(guild_id)
            if not guild:
                continue

            if config.get('lofi_active') and config.get('lofi_voice_channel') and config.get('lofi_url'):
                try:
                    vc_channel = guild.get_channel(config['lofi_voice_channel'])
                    if not vc_channel:
                        continue
                    vc = await vc_channel.connect(self_deaf=True)
                    stream_url = config['lofi_url']
                    if 'youtube.com' in stream_url or 'youtu.be' in stream_url:
                        try:
                            import yt_dlp
                            ydl_opts = {'format': 'bestaudio/best', 'quiet': True, 'no_warnings': True, 'source_address': '0.0.0.0', 'live_from_start': False, 'noplaylist': True}
                            loop = asyncio.get_event_loop()
                            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                                info = await loop.run_in_executor(None, lambda: ydl.extract_info(stream_url, download=False))
                            if info.get('is_live') or info.get('was_live'):
                                formats = [f for f in info.get('formats', []) if f.get('acodec') != 'none' and f.get('vcodec') == 'none' and f.get('protocol') in ('https', 'http', 'm3u8_native', 'm3u8')]
                                if not formats:
                                    formats = [f for f in info.get('formats', []) if f.get('acodec') != 'none']
                                if formats:
                                    formats.sort(key=lambda f: f.get('abr') or 0, reverse=True)
                                    stream_url = formats[0]['url']
                            else:
                                stream_url = info.get('url') or stream_url
                        except Exception as e:
                            print(f"Music: Lofi restore yt-dlp error for guild {guild_id}: {e}")
                            continue
                    source = discord.FFmpegPCMAudio(stream_url, **FFMPEG_OPTIONS)
                    source = discord.PCMVolumeTransformer(source, volume=0.5)
                    vc.play(source)
                    lofi_player = LofiPlayer(vc, config['lofi_station'], config['lofi_url'])
                    self._lofi_players[guild_id] = lofi_player
                    print(f"Music: Restored lofi session for guild {guild_id} ({config['lofi_station']})")
                except Exception as e:
                    print(f"Music: Failed to restore lofi for guild {guild_id}: {e}")

            elif config.get('vc247_active') and config.get('vc247_channel'):
                try:
                    vc_channel = guild.get_channel(config['vc247_channel'])
                    if not vc_channel:
                        continue
                    node = self._get_best_node()
                    if not node:
                        continue
                    player = await vc_channel.connect(cls=MusicPlayer, timeout=30.0, self_deaf=True)
                    player.is_247 = True
                    if config.get('vc247_text_channel'):
                        text_channel = guild.get_channel(config['vc247_text_channel'])
                        if text_channel:
                            player.ctx = await text_channel.history(limit=1).__anext__()
                    print(f"Music: Restored 247 session for guild {guild_id}")
                except Exception as e:
                    print(f"Music: Failed to restore 247 for guild {guild_id}: {e}")

    async def _start_nodes(self):
        await self.bot.wait_until_ready()
        nodes = []
        for n in self.bot.config.LAVALINK_NODES:
            try:
                scheme = "https" if n.get('secure') else "http"
                uri = f"{scheme}://{n['host']}:{n['port']}"
                nodes.append(wavelink.Node(
                    uri=uri,
                    password=n['password'],
                    identifier=n['identifier'],
                    retries=999999
                ))
            except Exception as e:
                print(f"Music: Failed to build node '{n.get('identifier')}': {e}")
        if nodes:
            try:
                await wavelink.Pool.connect(nodes=nodes, client=self.bot, cache_capacity=100)
            except Exception as e:
                print(f"Music: Pool connect failed: {e}")

    @tasks.loop(minutes=5)
    async def node_monitor(self):
        for node in wavelink.Pool.nodes.values():
            if node.status != wavelink.NodeStatus.CONNECTED:
                print(f"Music: Node '{node.identifier}' is {node.status.name}.")

    @node_monitor.before_loop
    async def before_node_monitor(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        print(f"Lavalink Node '{payload.node.identifier}' ready.")

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        player: MusicPlayer = payload.player
        if not player:
            return
        if player.update_task:
            player.update_task.cancel()
        if player.controller_msg:
            try:
                await player.controller_msg.delete()
            except Exception:
                pass
            player.controller_msg = None
        player.track_start_time = time.time() * 1000
        await self._update_controller(player)
        player.update_task = self.bot.loop.create_task(self._controller_loop(player))

    @commands.Cog.listener()
    async def on_wavelink_inactive_player(self, player: MusicPlayer):
        if not player.is_247:
            await player.disconnect()

    async def _controller_loop(self, player: MusicPlayer):
        while player.playing:
            if player.paused or not player.playing:
                await asyncio.sleep(5)
                continue
            if player.rl_manager.is_limited():
                await asyncio.sleep(10)
                continue
            if time.time() - player._last_update < 20:
                await asyncio.sleep(5)
                continue
            await self._update_controller(player)
            await asyncio.sleep(20)

    async def _update_controller(self, player: MusicPlayer):
        if not player.current or not player.ctx:
            return
        try:
            embed = self.bot.embed_manager.generic(description="", title=f"{self.bot.e.now_playing} Now Playing")
            card = await self._generate_music_card(player)
            embed.set_image(url="attachment://music-card.png")
            view = PlayerView(self.bot, player)
            if player.controller_msg:
                try:
                    await player.controller_msg.edit(embed=embed, view=view, attachments=[card])
                    player.rl_manager.on_success()
                    player._last_update = time.time()
                except discord.HTTPException as e:
                    if e.status == 429:
                        player.rl_manager.on_rate_limit(getattr(e, 'retry_after', 30) * 1000)
                    else:
                        player.controller_msg = None
            else:
                player.controller_msg = await player.ctx.send(embed=embed, view=view, file=card)
                player._last_update = time.time()
        except Exception as e:
            print(f"Music: Controller update error: {e}")

    async def _generate_music_card(self, player: MusicPlayer):
        track = player.current
        width, height = 800, 300
        canvas = Image.new('RGB', (width, height), (20, 20, 20))
        draw = ImageDraw.Draw(canvas)

        if track.artwork and self._session:
            try:
                async with self._session.get(track.artwork, timeout=aiohttp.ClientTimeout(total=5)) as r:
                    if r.status == 200:
                        art = Image.open(io.BytesIO(await r.read())).resize((220, 220))
                        canvas.paste(art, (40, 40))
            except Exception:
                pass

        draw.text((300, 50), (track.title or "Unknown")[:40], fill=(255, 255, 255))
        draw.text((300, 90), track.author or "Unknown", fill=(180, 180, 180))

        pos = player.position
        dur = track.length or 1
        pct = min(pos / dur, 1.0)
        bx, by, bw, bh = 300, 180, 450, 10
        draw.rounded_rectangle([bx, by, bx + bw, by + bh], 4, fill=(60, 60, 60))
        if pct > 0:
            draw.rounded_rectangle([bx, by, bx + int(bw * pct), by + bh], 4, fill=(138, 99, 255))

        def fmt(ms):
            s = int(ms / 1000)
            m, s = divmod(s, 60)
            h, m = divmod(m, 60)
            return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

        draw.text((300, 200), fmt(pos), fill=(200, 200, 200))
        draw.text((700, 200), fmt(dur), fill=(200, 200, 200))

        mode_labels = {
            wavelink.QueueMode.normal: "Off",
            wavelink.QueueMode.loop: "Track",
            wavelink.QueueMode.loop_all: "Queue"
        }
        draw.text(
            (300, 240),
            f"Loop: {mode_labels.get(player.queue.mode, 'Off')}  |  Queue: {len(player.queue)} tracks",
            fill=(140, 140, 140)
        )

        buf = io.BytesIO()
        canvas.save(buf, format="PNG")
        buf.seek(0)
        return discord.File(buf, "music-card.png")

    def _get_best_node(self):
        try:
            return wavelink.Pool.get_node()
        except wavelink.InvalidNodeException:
            return None

    def _get_player(self, ctx) -> MusicPlayer | None:
        return ctx.voice_client

    async def _ensure_player(self, ctx) -> MusicPlayer | None:
        if not ctx.author.voice:
            await ctx.error("Join a voice channel first.")
            return None
        node = self._get_best_node()
        if not node:
            await ctx.error("All music nodes are currently offline.")
            return None
        player = self._get_player(ctx)
        if not player:
            try:
                player = await ctx.author.voice.channel.connect(cls=MusicPlayer, timeout=30.0, self_deaf=True)
                player.ctx = ctx
            except Exception as e:
                await ctx.error(f"Failed to connect: {e}")
                return None
        return player

    def _fmt_ms(self, ms):
        s = int(ms / 1000)
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

    @commands.command(name="mplay", aliases=["p"], help="Play a track or playlist from a URL or search query.")
    async def play(self, ctx, *, query: str):
        player = await self._ensure_player(ctx)
        if not player:
            return

        if not query.startswith(("http", "ytsearch:", "scsearch:", "ytmsearch:")):
            query = f"ytmsearch:{query}"

        tracks = await wavelink.Playable.search(query)
        if not tracks:
            return await ctx.error("No results found.")

        if isinstance(tracks, wavelink.Playlist):
            for t in tracks.tracks:
                t.extras = {"requester_id": ctx.author.id}
                player.queue.put(t)
            await ctx.success(f"{self.bot.e.added_track} Added playlist **{tracks.name}** — `{len(tracks.tracks)}` tracks.")
        else:
            track = tracks[0]
            track.extras = {"requester_id": ctx.author.id}
            if not player.playing:
                await player.play(track)
            else:
                player.queue.put(track)
                await ctx.success(f"{self.bot.e.added_track} Added **{track.title}** to queue — position `{len(player.queue)}`.")

    @commands.command(name="mstop", help="Stop playback, clear the queue, and disconnect.")
    async def stop(self, ctx):
        player = self._get_player(ctx)
        if not player:
            return await ctx.error("Not playing anything.")
        player.queue.clear()
        player.is_247 = False
        await self._save_247_state(ctx.guild.id, False)
        await player.disconnect()
        await ctx.success(f"{self.bot.e.stop} Stopped and disconnected.")

    @commands.command(name="mskip", aliases=["s"], help="Skip the current track. Pass force=True to skip past loop mode.")
    async def skip(self, ctx, force: bool = False):
        player = self._get_player(ctx)
        if not player or not player.playing:
            return await ctx.error("Nothing is playing.")
        await player.skip(force=force)
        await ctx.success(f"{self.bot.e.skip} Skipped.")

    @commands.command(name="mpause", help="Pause or resume playback.")
    async def pause(self, ctx):
        player = self._get_player(ctx)
        if not player:
            return await ctx.error("Not playing anything.")
        await player.pause(not player.paused)
        if player.paused:
            await ctx.success(f"{self.bot.e.pause} Paused.")
        else:
            await ctx.success(f"{self.bot.e.resume} Resumed.")

    @commands.command(name="mseek", help="Seek to a position in the current track (in seconds).")
    async def seek(self, ctx, seconds: int):
        player = self._get_player(ctx)
        if not player or not player.playing:
            return await ctx.error("Nothing is playing.")
        if not player.current.is_seekable:
            return await ctx.error("This track is not seekable.")
        await player.seek(seconds * 1000)
        await ctx.success(f"{self.bot.e.music_note} Seeked to `{seconds}s`.")

    @commands.command(name="mvolume", aliases=["vol"], help="Set the player volume (0–1000).")
    async def volume(self, ctx, vol: int):
        player = self._get_player(ctx)
        if not player:
            return await ctx.error("Not playing anything.")
        vol = max(0, min(1000, vol))
        await player.set_volume(vol)
        emoji = self.bot.e.volume_high if vol > 50 else self.bot.e.volume_low if vol > 0 else self.bot.e.volume_mute
        await ctx.success(f"{emoji} Volume set to `{vol}%`.")

    @commands.command(name="mloop", help="Set loop mode: off, track, or queue.")
    async def loop(self, ctx, mode: str = "off"):
        player = self._get_player(ctx)
        if not player:
            return await ctx.error("Not playing anything.")
        mode_map = {
            "off": wavelink.QueueMode.normal,
            "track": wavelink.QueueMode.loop,
            "queue": wavelink.QueueMode.loop_all
        }
        if mode.lower() not in mode_map:
            return await ctx.error("Invalid mode. Choose: `off`, `track`, `queue`.")
        player.queue.mode = mode_map[mode.lower()]
        emoji = self.bot.e.loop_one if mode == "track" else self.bot.e.loop
        await ctx.success(f"{emoji} Loop mode: `{mode}`.")

    @commands.command(name="mautoplay", help="Toggle AutoPlay — automatically recommends tracks when the queue ends.")
    async def autoplay(self, ctx):
        player = self._get_player(ctx)
        if not player:
            return await ctx.error("Not playing anything.")
        if player.autoplay == wavelink.AutoPlayMode.disabled:
            player.autoplay = wavelink.AutoPlayMode.enabled
            await ctx.success(f"{self.bot.e.autoplay} AutoPlay **enabled**.")
        else:
            player.autoplay = wavelink.AutoPlayMode.disabled
            await ctx.success(f"{self.bot.e.autoplay} AutoPlay **disabled**.")

    @commands.command(name="mqueue", aliases=["q"], help="View the current track queue.")
    async def queue(self, ctx):
        player = self._get_player(ctx)
        if not player:
            return await ctx.error("Not playing anything.")
        if player.queue.is_empty:
            return await ctx.info(f"{self.bot.e.queue} The queue is empty.")
        tracks = list(player.queue)[:15]
        desc = "\n".join([f"`{i+1}.` **{t.title}** — `{t.author}`" for i, t in enumerate(tracks)])
        if len(player.queue) > 15:
            desc += f"\n*... and `{len(player.queue) - 15}` more*"
        embed = self.bot.embed_manager.generic(description=desc, title=f"{self.bot.e.queue} Queue — {len(player.queue)} tracks")
        await ctx.send(embed=embed)

    @commands.command(name="mremove", help="Remove a track from the queue by its position number.")
    async def remove(self, ctx, index: int):
        player = self._get_player(ctx)
        if not player or player.queue.is_empty:
            return await ctx.error("Queue is empty.")
        if index < 1 or index > len(player.queue):
            return await ctx.error(f"Index must be between 1 and `{len(player.queue)}`.")
        removed = player.queue[index - 1]
        del player.queue[index - 1]
        await ctx.success(f"{self.bot.e.stop} Removed **{removed.title}** from the queue.")

    @commands.command(name="mnowplaying", aliases=["np"], help="Show what is currently playing with a progress bar.")
    async def nowplaying(self, ctx):
        player = self._get_player(ctx)
        if not player or not player.current:
            return await ctx.error("Nothing is playing.")
        track = player.current
        pos = player.position
        dur = track.length or 1
        pct = min(pos / dur, 1.0)
        bar_len = 20
        bar = "█" * int(bar_len * pct) + "░" * (bar_len - int(bar_len * pct))
        embed = self.bot.embed_manager.generic(
            description=(
                f"**[{track.title}]({track.uri})**\n"
                f"by **{track.author}**\n\n"
                f"`{self._fmt_ms(pos)}` {bar} `{self._fmt_ms(dur)}`"
            ),
            title=f"{self.bot.e.now_playing} Now Playing"
        )
        if track.artwork:
            embed.set_thumbnail(url=track.artwork)
        await ctx.send(embed=embed)

    @commands.command(name="mshuffle", help="Shuffle the current queue.")
    async def shuffle(self, ctx):
        player = self._get_player(ctx)
        if not player or player.queue.is_empty:
            return await ctx.error("Queue is empty.")
        player.queue.shuffle()
        await ctx.success(f"{self.bot.e.shuffle} Queue shuffled.")

    @commands.command(name="msearch", help="Search for tracks and choose one interactively.")
    async def search(self, ctx, *, query: str):
        player = await self._ensure_player(ctx)
        if not player:
            return

        tracks = await wavelink.Playable.search(query)
        if not tracks:
            return await ctx.error("No results found.")

        results = tracks[:10] if isinstance(tracks, list) else tracks.tracks[:10]
        options = [
            discord.SelectOption(label=f"{i+1}. {t.title[:80]}", value=str(i), emoji=self.bot.e.music_note)
            for i, t in enumerate(results)
        ]

        class SearchView(discord.ui.View):
            def __init__(self_inner):
                super().__init__(timeout=30)
                self_inner.msg = None

            @discord.ui.select(options=options, placeholder="Choose a track...")
            async def sel(self_inner, interaction: discord.Interaction, select: discord.ui.Select):
                t = results[int(select.values[0])]
                t.extras = {"requester_id": interaction.user.id}
                if not player.playing:
                    await player.play(t)
                    await interaction.response.send_message(f"{self.bot.e.play} Playing **{t.title}**.", ephemeral=True)
                else:
                    player.queue.put(t)
                    await interaction.response.send_message(f"{self.bot.e.added_track} Added **{t.title}** to queue.", ephemeral=True)
                try:
                    await self_inner.msg.delete()
                except Exception:
                    pass

        v = SearchView()
        v.msg = await ctx.send(f"{self.bot.e.music_note} Search results:", view=v)

    @commands.command(name="m247", help="Toggle 24/7 mode — keeps the bot in VC even when the queue ends.")
    async def m247(self, ctx):
        player = self._get_player(ctx)
        if not player:
            return await ctx.error("Not connected.")
        player.is_247 = not player.is_247
        state = "enabled" if player.is_247 else "disabled"
        vc_id = player.channel.id if player.is_247 and player.channel else None
        txt_id = ctx.channel.id if player.is_247 else None
        await self._save_247_state(ctx.guild.id, player.is_247, vc_id, txt_id)
        await ctx.success(f"{self.bot.e.vc247} 24/7 mode **{state}**.")

    @commands.command(name="mjoin", help="Join your current voice channel.")
    async def join(self, ctx):
        player = await self._ensure_player(ctx)
        if player:
            await ctx.success(f"{self.bot.e.play} Joined {ctx.author.voice.channel.mention}.")

    @commands.command(name="mleave", help="Disconnect from the voice channel.")
    async def leave(self, ctx):
        player = self._get_player(ctx)
        if not player:
            return await ctx.error("Not connected.")
        player.is_247 = False
        await self._save_247_state(ctx.guild.id, False)
        await player.disconnect()
        await ctx.success(f"{self.bot.e.stop} Disconnected.")

    @commands.command(name="mfilter", help="Open the audio filter selector.")
    async def mfilter(self, ctx):
        player = self._get_player(ctx)
        if not player or not player.playing:
            return await ctx.error("Nothing is playing.")
        view = FilterMenuView(self.bot, player)
        await ctx.send(f"{self.bot.e.music_filter} Audio Filters:", view=view)

    @commands.group(name="mlofi", aliases=["lofi"], invoke_without_command=True, help="Lo-Fi radio management commands.")
    async def lofi_group(self, ctx):
        await ctx.send_help(ctx.command)

    @lofi_group.command(name="on", help="Start 24/7 Lo-Fi with station selection.")
    async def lofi_on(self, ctx):
        if not ctx.author.voice:
            return await ctx.error("Join a voice channel first.")
        config = await self.db.find_one('music_config', {'_id': ctx.guild.id}) or {}
        view = LofiSelectView(self.bot, ctx, custom_stations=config.get('custom_lofi', {}))
        await ctx.send(f"### {self.bot.e.lofi} Lo-Fi Radio\nSelect a station:", view=view)

    @lofi_group.command(name="off", help="Stop Lo-Fi and disconnect.")
    async def lofi_off(self, ctx):
        lofi = self._lofi_players.get(ctx.guild.id)
        if not lofi:
            vc = ctx.voice_client
            if vc:
                await vc.disconnect()
            await self._save_lofi_state(ctx.guild.id)
            return await ctx.success(f"{self.bot.e.stop} Disconnected.")
        await lofi.stop()
        self._lofi_players.pop(ctx.guild.id, None)
        await self._save_lofi_state(ctx.guild.id)
        await ctx.success(f"{self.bot.e.stop} Lo-Fi stopped.")

    @lofi_group.command(name="volume", help="Set the Lo-Fi stream volume (0–100).")
    async def lofi_volume(self, ctx, vol: int):
        lofi = self._lofi_players.get(ctx.guild.id)
        if not lofi or not lofi.voice_client.source:
            return await ctx.error("Lo-Fi is not playing.")
        vol = max(0, min(100, vol))
        lofi.voice_client.source.volume = vol / 100
        emoji = self.bot.e.volume_high if vol > 50 else self.bot.e.volume_low if vol > 0 else self.bot.e.volume_mute
        await ctx.success(f"{emoji} Lo-Fi volume set to `{vol}%`.")

    @lofi_group.command(name="add", help="Add a custom Lo-Fi station URL.")
    @commands.has_permissions(manage_guild=True)
    async def lofi_add(self, ctx, name: str, url: str):
        if len(name) > 20:
            return await ctx.error("Name must be under 20 characters.")
        if not url.startswith("http"):
            return await ctx.error("Invalid URL.")
        config = await self.db.find_one('music_config', {'_id': ctx.guild.id}) or {}
        custom = config.get('custom_lofi', {})
        custom[name] = url
        await self.db.update_one('music_config', {'_id': ctx.guild.id}, {'custom_lofi': custom}, upsert=True)
        await ctx.success(f"{self.bot.e.lofi} Added custom station: **{name}**.")

    @lofi_group.command(name="remove", help="Remove a custom Lo-Fi station.")
    @commands.has_permissions(manage_guild=True)
    async def lofi_remove(self, ctx, *, name: str):
        config = await self.db.find_one('music_config', {'_id': ctx.guild.id}) or {}
        custom = config.get('custom_lofi', {})
        if name not in custom:
            return await ctx.error(f"Station **{name}** not found.")
        del custom[name]
        await self.db.update_one('music_config', {'_id': ctx.guild.id}, {'custom_lofi': custom}, upsert=True)
        await ctx.success(f"{self.bot.e.lofi} Removed station: **{name}**.")

    @lofi_group.command(name="list", help="List all available Lo-Fi stations.")
    async def lofi_list(self, ctx):
        config = await self.db.find_one('music_config', {'_id': ctx.guild.id}) or {}
        custom = config.get('custom_lofi', {})
        desc = "**Default Stations:**\n" + "\n".join([f"• `{n}`" for n in self.bot.config.LOFI_STATIONS.keys()])
        if custom:
            desc += "\n\n**Custom Stations:**\n" + "\n".join([f"• `{n}`" for n in custom.keys()])
        embed = self.bot.embed_manager.generic(description=desc, title=f"{self.bot.e.lofi} Lo-Fi Stations")
        await ctx.send(embed=embed)

    @lofi_group.command(name="setchannel", help="Set a dedicated voice channel for Lo-Fi.")
    @commands.has_permissions(manage_guild=True)
    async def lofi_setchannel(self, ctx, channel: discord.VoiceChannel):
        await self.db.update_one('music_config', {'_id': ctx.guild.id}, {'lofi_channel': channel.id}, upsert=True)
        await ctx.success(f"{self.bot.e.lofi} Lo-Fi channel set to {channel.mention}.")

    @lofi_group.command(name="nowplaying", help="Show the currently playing Lo-Fi station.")
    async def lofi_nowplaying(self, ctx):
        lofi = self._lofi_players.get(ctx.guild.id)
        if not lofi or not lofi.is_playing():
            return await ctx.info(f"{self.bot.e.lofi} No Lo-Fi station is currently playing.")
        embed = self.bot.embed_manager.generic(
            description=f"**Station:** {lofi.station_name}\n**URL:** {lofi.url}",
            title=f"{self.bot.e.lofi} Lo-Fi Now Playing"
        )
        await ctx.send(embed=embed)


    @commands.group(name="mplaylist", aliases=["mpl", "playlist"], invoke_without_command=True, help="Personal playlist management commands.")
    async def playlist_group(self, ctx):
        await ctx.send_help(ctx.command)

    @playlist_group.command(name="create", help="Create a new personal playlist.")
    async def playlist_create(self, ctx, *, name: str):
        if len(name) > 30:
            return await ctx.error("Playlist name must be under 30 characters.")
        user_data = await self.db.find_one('user_playlists', {'_id': ctx.author.id}) or {'playlists': {}}
        if name in user_data.get('playlists', {}):
            return await ctx.error(f"Playlist **{name}** already exists.")
        user_data.setdefault('playlists', {})[name] = []
        await self.db.update_one('user_playlists', {'_id': ctx.author.id}, user_data, upsert=True)
        await ctx.success(f"{self.bot.e.playlist} Created playlist: **{name}**.")

    @playlist_group.command(name="add", help="Add the current song or a search query to a playlist.")
    async def playlist_add(self, ctx, playlist_name: str, *, query: str = None):
        user_data = await self.db.find_one('user_playlists', {'_id': ctx.author.id})
        if not user_data or playlist_name not in user_data.get('playlists', {}):
            return await ctx.error(f"Playlist **{playlist_name}** not found.")
        if not query:
            player = self._get_player(ctx)
            if not player or not player.current:
                return await ctx.error("Nothing is playing. Provide a search query.")
            track = player.current
        else:
            results = await wavelink.Playable.search(f"ytmsearch:{query}")
            if not results:
                return await ctx.error("No results found.")
            track = results[0] if isinstance(results, list) else results.tracks[0]
        track_data = {"title": track.title, "uri": track.uri, "author": track.author, "length": track.length}
        user_data['playlists'][playlist_name].append(track_data)
        await self.db.update_one('user_playlists', {'_id': ctx.author.id}, user_data, upsert=True)
        await ctx.success(f"{self.bot.e.added_track} Added **{track_data['title']}** to **{playlist_name}**.")

    @playlist_group.command(name="remove", help="Remove a track from a playlist by index.")
    async def playlist_remove(self, ctx, playlist_name: str, index: int):
        user_data = await self.db.find_one('user_playlists', {'_id': ctx.author.id})
        if not user_data or playlist_name not in user_data.get('playlists', {}):
            return await ctx.error(f"Playlist **{playlist_name}** not found.")
        playlist = user_data['playlists'][playlist_name]
        if index < 1 or index > len(playlist):
            return await ctx.error(f"Index must be between 1 and `{len(playlist)}`.")
        removed = playlist.pop(index - 1)
        await self.db.update_one('user_playlists', {'_id': ctx.author.id}, user_data, upsert=True)
        await ctx.success(f"{self.bot.e.stop} Removed **{removed['title']}** from **{playlist_name}**.")

    @playlist_group.command(name="delete", help="Delete an entire playlist.")
    async def playlist_delete(self, ctx, *, name: str):
        user_data = await self.db.find_one('user_playlists', {'_id': ctx.author.id})
        if not user_data or name not in user_data.get('playlists', {}):
            return await ctx.error(f"Playlist **{name}** not found.")
        del user_data['playlists'][name]
        await self.db.update_one('user_playlists', {'_id': ctx.author.id}, user_data, upsert=True)
        await ctx.success(f"{self.bot.e.playlist} Deleted playlist: **{name}**.")

    @playlist_group.command(name="list", help="List your playlists, or view tracks in a specific one.")
    async def playlist_list(self, ctx, *, name: str = None):
        user_data = await self.db.find_one('user_playlists', {'_id': ctx.author.id})
        if not user_data or not user_data.get('playlists'):
            return await ctx.info(f"{self.bot.e.playlist} You have no playlists.")
        if not name:
            desc = "\n".join([f"• **{n}** — `{len(p)}` tracks" for n, p in user_data['playlists'].items()])
            embed = self.bot.embed_manager.generic(description=desc, title=f"{self.bot.e.playlist} {ctx.author.name}'s Playlists")
            return await ctx.send(embed=embed)
        if name not in user_data['playlists']:
            return await ctx.error(f"Playlist **{name}** not found.")
        playlist = user_data['playlists'][name]
        if not playlist:
            return await ctx.info(f"Playlist **{name}** is empty.")
        desc = "\n".join([f"`{i+1}.` [{t['title']}]({t['uri']})" for i, t in enumerate(playlist[:20])])
        if len(playlist) > 20:
            desc += f"\n*... and `{len(playlist) - 20}` more*"
        embed = self.bot.embed_manager.generic(description=desc, title=f"{self.bot.e.playlist} {name}")
        await ctx.send(embed=embed)

    @playlist_group.command(name="load", aliases=["play"], help="Load and play a saved playlist.")
    async def playlist_load(self, ctx, *, name: str):
        player = await self._ensure_player(ctx)
        if not player:
            return
        user_data = await self.db.find_one('user_playlists', {'_id': ctx.author.id})
        if not user_data or name not in user_data.get('playlists', {}):
            return await ctx.error(f"Playlist **{name}** not found.")
        tracks_data = user_data['playlists'][name]
        if not tracks_data:
            return await ctx.error("Playlist is empty.")
        loading_msg = await ctx.info(f"{self.bot.e.playlist} Loading **{name}**...")
        count = 0
        first = True
        for data in tracks_data:
            try:
                results = await wavelink.Playable.search(data['uri'])
                if not results:
                    continue
                track = results[0] if isinstance(results, list) else results.tracks[0]
                track.extras = {"requester_id": ctx.author.id}
                if first and not player.playing:
                    await player.play(track)
                    first = False
                else:
                    player.queue.put(track)
                count += 1
            except Exception:
                continue
        try:
            await loading_msg.delete()
        except Exception:
            pass
        await ctx.success(f"{self.bot.e.playlist} Loaded `{count}` tracks from **{name}**.")


async def setup(bot):
    await bot.add_cog(Music(bot))
