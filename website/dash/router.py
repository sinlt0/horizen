from flask import render_template_string, abort, session, request, redirect
import json
import urllib.request
import asyncio
import base64
from ..engine import UIEngine
from ..icons import Icons
from .engine import DashEngine
from ..webconfig import WebConfig

def init_dash_routes(app, bot_instance):
    
    def run_async(coro, timeout=10):
        try:
            future = asyncio.run_coroutine_threadsafe(coro, bot_instance.loop)
            return future.result(timeout=timeout)
        except asyncio.TimeoutError:
            print("Dashboard Async Timeout")
            return None
        except Exception as e:
            print(f"Dashboard Async Error: {e}")
            return None

    def to_b64_json(data):
        return base64.b64encode(json.dumps(data).encode()).decode()

    def get_user_guilds(token):
        ua = bot_instance.config.USER_AGENT if bot_instance else 'DiscordBot (https://horizen.systems, 1.0.0)'
        req = urllib.request.Request(
            'https://discord.com/api/v10/users/@me/guilds',
            headers={'Authorization': f"Bearer {token}", 'User-Agent': ua}
        )
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read().decode())
        except: return []

    @app.route('/dashboard')
    def dashboard_home():
        user = session.get('user')
        if not user or 'token' not in user: return redirect('/login')
        all_guilds = get_user_guilds(user['token'])
        manageable = []
        for g in all_guilds:
            perms = int(g['permissions'])
            if (perms & 0x20) == 0x20:
                guild_obj = bot_instance.get_guild(int(g['id']))
                if guild_obj: manageable.append(g)
        content = DashEngine.guild_selector(manageable)
        return DashEngine.dash_wrapper(content, user=user, bot_avatar=bot_instance.user.display_avatar.url if bot_instance.user else None)

    @app.route('/dashboard/<int:guild_id>')
    def guild_dash(guild_id):
        user = session.get('user')
        if not user: return redirect('/login')
        guild = bot_instance.get_guild(guild_id)
        if not guild: return abort(404)
        member = guild.get_member(int(user['id']))
        if not member or not member.guild_permissions.manage_guild: return abort(403)
        
        content = f"""
        <div class="glass module-card">
            <h2 style="margin-bottom: 20px;">Welcome to {guild.name}</h2>
            <p style="color: #a0a0b0;">Select a module from the sidebar to begin configuration.</p>
        </div>
        
        <div class="grid-container" style="padding: 0; margin-top: 30px;">
            <div class="glass module-card" style="text-align: center;">
                <div style="font-size: 2.5rem; font-weight: 800; color: var(--primary);">{guild.member_count}</div>
                <div style="font-size: 0.75rem; font-weight: 800; text-transform: uppercase; color: #606070;">Total Members</div>
            </div>
            <div class="glass module-card" style="text-align: center;">
                <div style="font-size: 2.5rem; font-weight: 800; color: #ffD700;">{guild.premium_subscription_count}</div>
                <div style="font-size: 0.75rem; font-weight: 800; text-transform: uppercase; color: #606070;">Server Boosts</div>
            </div>
            <div class="glass module-card" style="text-align: center;">
                <div style="font-size: 2.5rem; font-weight: 800; color: #00ff88;">{len(guild.roles)}</div>
                <div style="font-size: 0.75rem; font-weight: 800; text-transform: uppercase; color: #606070;">Total Roles</div>
            </div>
        </div>

        <div class="glass module-card" style="margin-top: 30px;">
            <h3 style="margin-bottom: 20px; display: flex; align-items: center; gap: 10px;">{Icons.INFO} System Health</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px;">
                <div style="background: rgba(0,0,0,0.2); padding: 20px; border-radius: 12px; border: 1px solid rgba(0,255,136,0.1);">
                    <div style="font-size: 0.7rem; color: #606070; font-weight: 800; text-transform: uppercase;">Sharding</div>
                    <div style="color: #00ff88; font-weight: 800;">ACTIVE</div>
                </div>
                <div style="background: rgba(0,0,0,0.2); padding: 20px; border-radius: 12px; border: 1px solid rgba(138, 99, 255, 0.1);">
                    <div style="font-size: 0.7rem; color: #606070; font-weight: 800; text-transform: uppercase;">Latency</div>
                    <div style="color: var(--primary); font-weight: 800;">{round(bot_instance.latency * 1000)}ms</div>
                </div>
            </div>
        </div>

        <div class="glass module-card" style="margin-top: 30px;">
            <h3 style="margin-bottom: 30px;">{Icons.ZAP} Server Growth</h3>
            <canvas id="growthChart" style="max-height: 300px;"></canvas>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script>
        document.addEventListener('DOMContentLoaded', function() {{
            const ctx = document.getElementById('growthChart').getContext('2d');
            new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                    datasets: [{{
                        label: 'Member Joins',
                        data: [12, 19, 3, 5, 2, 3, 9],
                        borderColor: '#8a63ff',
                        backgroundColor: 'rgba(138, 99, 255, 0.1)',
                        tension: 0.4,
                        fill: true
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{ legend: {{ display: false }} }},
                    scales: {{
                        y: {{ grid: {{ color: 'rgba(255,255,255,0.05)' }}, ticks: {{ color: '#606070' }} }},
                        x: {{ grid: {{ display: false }}, ticks: {{ color: '#606070' }} }}
                    }}
                }}
            }});
        }});
        </script>
        """
        return DashEngine.dash_wrapper(content, guild=guild, active_tab="home", user=user, bot_avatar=bot_instance.user.display_avatar.url if bot_instance.user else None)

    @app.route('/dashboard/<int:guild_id>/general')
    def guild_general(guild_id):
        user = session.get('user')
        if not user: return redirect('/login')
        guild = bot_instance.get_guild(guild_id)
        if not guild: return abort(404)
        prefix = run_async(bot_instance.prefix_manager.get_prefix(guild_id))
        initial_data = to_b64_json({'prefix': prefix})
        content = f"""
        <input type="hidden" id="initial-data" value="{initial_data}">
        <div class="glass module-card">
            <h2 style="margin-bottom: 30px; display: flex; align-items: center; gap: 15px;">{Icons.CONFIG} General Settings</h2>
            <div class="input-group">
                <label class="input-label">Server Prefix</label>
                <input type="text" class="dash-input" x-model="currentSettings.prefix" maxlength="5">
                <p style="font-size: 0.7rem; color: #606070; margin-top: 10px;">Max 5 characters. Used to trigger bot commands.</p>
            </div>
        </div>
        """
        return DashEngine.dash_wrapper(content, guild=guild, active_tab="home", user=user, bot_avatar=bot_instance.user.display_avatar.url if bot_instance.user else None)

    @app.route('/dashboard/<int:guild_id>/general/save', methods=['POST'])
    def save_general(guild_id):
        user = session.get('user')
        if not user: return abort(401)
        data = request.json
        run_async(bot_instance.prefix_manager.set_prefix(guild_id, data['prefix']))
        return {"status": "success"}

    @app.route('/dashboard/<int:guild_id>/embeds')
    def guild_embeds(guild_id):
        user = session.get('user')
        if not user: return redirect('/login')
        guild = bot_instance.get_guild(guild_id)
        if not guild: return abort(404)
        member = guild.get_member(int(user['id']))
        if not member or not member.guild_permissions.manage_guild: return abort(403)
        config = run_async(bot_instance.db_manager.find_one('greetings_config', {'_id': guild_id})) or {}
        embeds = config.get('custom_embeds', {})
        initial_data = to_b64_json({'embeds': embeds})
        embed_cards = ""
        for name, data in embeds.items():
            embed_cards += f"""
            <div class="glass module-card" style="padding: 20px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="font-weight: 800; color: var(--primary);">{{{{embed:{name}}}}}</div>
                    <div style="font-size: 0.75rem; color: #606070;">{data.get('title', 'No Title')}</div>
                </div>
                <div style="display: flex; gap: 10px;">
                    <a href="/dashboard/{guild_id}/embeds/{name}" class="btn glass" style="padding: 8px 15px; font-size: 0.7rem;">EDIT</a>
                    <button @click="deleteEmbed('{name}')" class="btn glass" style="padding: 8px 15px; font-size: 0.7rem; color: #ff4757; border-color: rgba(255,71,87,0.2);">DELETE</button>
                </div>
            </div>
            """
        content = f"""
        <input type="hidden" id="initial-data" value="{initial_data}">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <h2 style="display: flex; align-items: center; gap: 15px;">{Icons.WAND} Embed Templates</h2>
            <button onclick="document.getElementById('new-embed-modal').style.display='flex'" class="btn btn-primary" style="padding: 10px 20px; font-size: 0.8rem;">+ CREATE NEW</button>
        </div>
        <div style="display: flex; flex-direction: column; gap: 15px;">
            {embed_cards if embed_cards else '<div style="text-align: center; padding: 40px; color: #444;">No templates found. Create one to get started!</div>'}
        </div>
        <div id="new-embed-modal" style="display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.8); backdrop-filter: blur(10px); z-index: 9999; align-items: center; justify-content: center;">
            <div class="glass module-card" style="max-width: 400px; width: 90%;">
                <h3 style="margin-bottom: 20px;">New Template</h3>
                <div class="input-group">
                    <label class="input-label">Template Name</label>
                    <input type="text" id="new-embed-name" class="dash-input" placeholder="e.g. welcome_embed">
                </div>
                <div style="display: flex; gap: 10px; justify-content: flex-end;">
                    <button onclick="document.getElementById('new-embed-modal').style.display='none'" class="btn glass">Cancel</button>
                    <button onclick="createEmbed()" class="btn btn-primary">Create</button>
                </div>
            </div>
        </div>
        <script>
        async function createEmbed() {{
            const name = document.getElementById('new-embed-name').value.trim();
            if(!name) return;
            const resp = await fetch(`/dashboard/{guild_id}/embeds/create`, {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ name }})
            }});
            if(resp.ok) window.location.href = `/dashboard/{guild_id}/embeds/` + name;
        }}
        async function deleteEmbed(name) {{
            if(!confirm('Are you sure you want to delete the template "' + name + '"?')) return;
            const resp = await fetch(`/dashboard/{guild_id}/embeds/delete`, {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ name }})
            }});
            if(resp.ok) window.location.reload();
        }}
        </script>
        """
        return DashEngine.dash_wrapper(content, guild=guild, active_tab="embeds", user=user, bot_avatar=bot_instance.user.display_avatar.url if bot_instance.user else None)

    @app.route('/dashboard/<int:guild_id>/embeds/delete', methods=['POST'])
    def delete_embed_route(guild_id):
        user = session.get('user')
        if not user: return abort(401)
        name = request.json.get('name')
        if not name: return abort(400)
        config = run_async(bot_instance.db_manager.find_one('greetings_config', {'_id': guild_id})) or {}
        if 'custom_embeds' in config and name in config['custom_embeds']:
            del config['custom_embeds'][name]
            config.pop('_id', None)
            run_async(bot_instance.db_manager.update_one('greetings_config', {'_id': guild_id}, config, upsert=True))
        return {"status": "success"}

    @app.route('/dashboard/<int:guild_id>/embeds/<name>')
    def edit_embed(guild_id, name):
        user = session.get('user')
        if not user: return redirect('/login')
        guild = bot_instance.get_guild(guild_id)
        if not guild: return abort(404)
        config = run_async(bot_instance.db_manager.find_one('greetings_config', {'_id': guild_id})) or {}
        embed_data = config.get('custom_embeds', {}).get(name)
        if not embed_data: return redirect(f"/dashboard/{guild_id}/embeds")
        initial_data = to_b64_json(embed_data)
        content = f"""
        <input type="hidden" id="initial-data" value="{initial_data}">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px;">
            <div style="display: flex; align-items: center; gap: 15px;">
                <a href="/dashboard/{guild_id}/embeds" style="color: #606070;">{Icons.LIST}</a>
                <h2 style="margin: 0;">Editing: <span style="color: var(--primary);">{{{{embed:{name}}}}}</span></h2>
            </div>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 450px; gap: 40px;">
            <div>
                <div class="glass module-card">
                    <div class="input-group">
                        <label class="input-label">Title</label>
                        <input type="text" class="dash-input" x-model="currentSettings.title">
                    </div>
                    <div class="input-group">
                        <label class="input-label">Description</label>
                        <textarea class="dash-input" style="min-height: 150px;" x-model="currentSettings.description"></textarea>
                    </div>
                    <div class="dash-grid">
                        <div class="input-group">
                            <label class="input-label">Color (Hex)</label>
                            <input type="color" class="dash-input" style="padding: 5px; height: 45px;" x-model="currentSettings.color">
                        </div>
                        <div class="input-group">
                            <label class="input-label">Footer Text</label>
                            <input type="text" class="dash-input" x-model="currentSettings.footer">
                        </div>
                    </div>
                </div>
                <div class="glass module-card">
                    <h3 style="margin-bottom: 20px; font-size: 0.9rem;">Author & Images</h3>
                    <div class="dash-grid">
                        <div class="input-group">
                            <label class="input-label">Author Name</label>
                            <input type="text" class="dash-input" x-model="currentSettings.author_name">
                        </div>
                        <div class="input-group">
                            <label class="input-label">Author Icon URL</label>
                            <input type="text" class="dash-input" x-model="currentSettings.author_icon">
                        </div>
                    </div>
                    <div class="input-group">
                        <label class="input-label">Main Image URL</label>
                        <input type="text" class="dash-input" x-model="currentSettings.image">
                    </div>
                    <div class="input-group">
                        <label class="input-label">Thumbnail URL</label>
                        <input type="text" class="dash-input" x-model="currentSettings.thumbnail">
                    </div>
                </div>
            </div>
            <div style="position: sticky; top: 30px; height: fit-content;">
                <div style="font-size: 0.75rem; font-weight: 800; color: #606070; text-transform: uppercase; margin-bottom: 15px;">Visual Preview</div>
                <div class="discord-view">
                    <div class="discord-msg">
                        <div class="discord-avatar" style="background: var(--primary); display: flex; align-items: center; justify-content: center; font-weight: 800; color: white;">H</div>
                        <div class="discord-content">
                            <div class="discord-header">
                                <span class="discord-name">{WebConfig.NAME}</span>
                                <span class="discord-bot-tag">BOT</span>
                            </div>
                            <div class="discord-embed" :style="'border-left-color: ' + currentSettings.color">
                                <div class="discord-embed-author" x-show="currentSettings.author_name">
                                    <img :src="currentSettings.author_icon" x-show="currentSettings.author_icon" style="width: 24px; height: 24px; border-radius: 50%; margin-right: 8px;">
                                    <span x-text="currentSettings.author_name"></span>
                                </div>
                                <div class="discord-embed-title" x-text="currentSettings.title" x-show="currentSettings.title"></div>
                                <div class="discord-embed-description" x-text="currentSettings.description || 'No description provided.'" style="white-space: pre-wrap;"></div>
                                <img :src="currentSettings.image" x-show="currentSettings.image" style="max-width: 100%; border-radius: 4px; margin-top: 10px;">
                                <div class="discord-embed-footer" x-show="currentSettings.footer" x-text="currentSettings.footer"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        """
        return DashEngine.dash_wrapper(content, guild=guild, active_tab="embeds", user=user, bot_avatar=bot_instance.user.display_avatar.url if bot_instance.user else None)

    @app.route('/dashboard/<int:guild_id>/embeds/create', methods=['POST'])
    def create_embed_route(guild_id):
        user = session.get('user')
        if not user: return abort(401)
        name = request.json.get('name', '').lower().replace(' ', '_')
        if not name: return abort(400)
        config = run_async(bot_instance.db_manager.find_one('greetings_config', {'_id': guild_id})) or {}
        if 'custom_embeds' not in config: config['custom_embeds'] = {}
        config['custom_embeds'][name] = {'title': 'New Embed', 'description': 'Edit this template on the web!'}
        config.pop('_id', None)
        run_async(bot_instance.db_manager.update_one('greetings_config', {'_id': guild_id}, config, upsert=True))
        return {"status": "success"}

    @app.route('/dashboard/<int:guild_id>/embeds/<name>/save', methods=['POST'])
    def save_embed_route(guild_id, name):
        user = session.get('user')
        if not user: return abort(401)
        data = request.json
        config = run_async(bot_instance.db_manager.find_one('greetings_config', {'_id': guild_id})) or {}
        if 'custom_embeds' not in config: config['custom_embeds'] = {}
        config['custom_embeds'][name] = data
        config.pop('_id', None)
        run_async(bot_instance.db_manager.update_one('greetings_config', {'_id': guild_id}, config, upsert=True))
        return {"status": "success"}

    @app.route('/dashboard/<int:guild_id>/greetings')
    def guild_greetings(guild_id):
        user = session.get('user')
        if not user: return redirect('/login')
        guild = bot_instance.get_guild(guild_id)
        if not guild: return abort(404)
        member = guild.get_member(int(user['id']))
        if not member or not member.guild_permissions.manage_guild: return abort(403)
        config = run_async(bot_instance.db_manager.find_one('greetings_config', {'_id': guild_id})) or {}
        data_obj = {
            'join_msg': config.get('join_actions', [{}])[0].get('message', '') if config.get('join_actions') else '',
            'join_channel': str(config.get('join_actions', [{}])[0].get('channel_id', '')) if config.get('join_actions') else '',
            'join_dm': config.get('join_actions', [{}])[0].get('dm', False) if config.get('join_actions') else False,
            'join_delay': config.get('join_actions', [{}])[0].get('delay', 0) if config.get('join_actions') else 0,
            'join_delete': config.get('join_actions', [{}])[0].get('delete_after', 0) if config.get('join_actions') else 0,
            'leave_msg': config.get('leave_actions', [{}])[0].get('message', '') if config.get('leave_actions') else '',
            'leave_channel': str(config.get('leave_actions', [{}])[0].get('channel_id', '')) if config.get('leave_actions') else '',
            'leave_delay': config.get('leave_actions', [{}])[0].get('delay', 0) if config.get('leave_actions') else 0,
            'leave_delete': config.get('leave_actions', [{}])[0].get('delete_after', 0) if config.get('leave_actions') else 0,
            'boost_msg': config.get('boost_actions', [{}])[0].get('message', '') if config.get('boost_actions') else '',
            'boost_channel': str(config.get('boost_actions', [{}])[0].get('channel_id', '')) if config.get('boost_actions') else '',
            'boost_dm': config.get('boost_actions', [{}])[0].get('dm', False) if config.get('boost_actions') else False,
            'boost_delay': config.get('boost_actions', [{}])[0].get('delay', 0) if config.get('boost_actions') else 0,
            'boost_delete': config.get('boost_actions', [{}])[0].get('delete_after', 0) if config.get('boost_actions') else 0,
            'img_enabled': config.get('image_settings', {}).get('enabled', False),
            'img_bg': config.get('image_settings', {}).get('background_url', ''),
            'img_color': config.get('image_settings', {}).get('text_color', '#FFFFFF'),
            'custom_embeds': config.get('custom_embeds', {})
        }
        channels_html = "".join([f'<option value="{c.id}">{c.name}</option>' for c in guild.text_channels])
        content = f"""
        <input type="hidden" id="initial-data" value="{to_b64_json(data_obj)}">
        <div style="display: grid; grid-template-columns: 1fr 400px; gap: 30px;">
            <div>
                <div class="glass module-card">
                    <h3 style="margin-bottom: 20px; color: var(--primary);">Welcome Messages</h3>
                    <div style="display: grid; grid-template-columns: 1fr 100px; gap: 15px;">
                        <div class="input-group">
                            <label class="input-label">Channel</label>
                            <select class="dash-input" x-model="currentSettings.join_channel"><option value="">Disabled</option>{channels_html}</select>
                        </div>
                        <div class="input-group">
                            <label class="input-label">Direct Msg</label>
                            <div style="height: 45px; display: flex; align-items: center; justify-content: center;"><label class="switch"><input type="checkbox" x-model="currentSettings.join_dm"><span class="slider"></span></label></div>
                        </div>
                    </div>
                    <div class="input-group"><label class="input-label">Message Content</label><textarea class="dash-input" style="min-height: 100px;" x-model="currentSettings.join_msg" placeholder="Welcome {{user}}!"></textarea></div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                        <div class="input-group"><label class="input-label">Delay (seconds)</label><input type="number" class="dash-input" x-model="currentSettings.join_delay" min="0" max="3600"></div>
                        <div class="input-group"><label class="input-label">Auto-Delete (sec)</label><input type="number" class="dash-input" x-model="currentSettings.join_delete" min="0" max="3600"></div>
                    </div>
                </div>
                <div class="glass module-card">
                    <h3 style="margin-bottom: 20px; color: #ff4757;">Leave Messages</h3>
                    <div class="input-group">
                        <label class="input-label">Channel</label>
                        <select class="dash-input" x-model="currentSettings.leave_channel"><option value="">Disabled</option>{channels_html}</select>
                    </div>
                    <div class="input-group"><label class="input-label">Message Content</label><textarea class="dash-input" style="min-height: 100px;" x-model="currentSettings.leave_msg" placeholder="{{user_name}} has left."></textarea></div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                        <div class="input-group"><label class="input-label">Delay (seconds)</label><input type="number" class="dash-input" x-model="currentSettings.leave_delay" min="0" max="3600"></div>
                        <div class="input-group"><label class="input-label">Auto-Delete (sec)</label><input type="number" class="dash-input" x-model="currentSettings.leave_delete" min="0" max="3600"></div>
                    </div>
                </div>
                <div class="glass module-card">
                    <h3 style="margin-bottom: 20px; color: #f472b6;">Booster Messages</h3>
                    <div style="display: grid; grid-template-columns: 1fr 100px; gap: 15px;">
                        <div class="input-group">
                            <label class="input-label">Channel</label>
                            <select class="dash-input" x-model="currentSettings.boost_channel"><option value="">Disabled</option>{channels_html}</select>
                        </div>
                        <div class="input-group">
                            <label class="input-label">Direct Msg</label>
                            <div style="height: 45px; display: flex; align-items: center; justify-content: center;"><label class="switch"><input type="checkbox" x-model="currentSettings.boost_dm"><span class="slider"></span></label></div>
                        </div>
                    </div>
                    <div class="input-group"><label class="input-label">Message Content</label><textarea class="dash-input" style="min-height: 100px;" x-model="currentSettings.boost_msg" placeholder="Thanks for boosting {{user}}!"></textarea></div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                        <div class="input-group"><label class="input-label">Delay (seconds)</label><input type="number" class="dash-input" x-model="currentSettings.boost_delay" min="0" max="3600"></div>
                        <div class="input-group"><label class="input-label">Auto-Delete (sec)</label><input type="number" class="dash-input" x-model="currentSettings.boost_delete" min="0" max="3600"></div>
                    </div>
                </div>
                <div class="glass module-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                        <h3 style="color: #00ff88;">Image Greeting Card</h3>
                        <label class="switch"><input type="checkbox" x-model="currentSettings.img_enabled"><span class="slider"></span></label>
                    </div>
                    <div class="input-group"><label class="input-label">Background URL</label><input type="text" class="dash-input" x-model="currentSettings.img_bg" placeholder="https://..."></div>
                    <div class="input-group"><label class="input-label">Text Color (Hex)</label><input type="color" class="dash-input" style="padding: 5px; height: 45px;" x-model="currentSettings.img_color"></div>
                </div>
            </div>
            <div style="position: sticky; top: 30px; height: fit-content;">
                <div style="font-size: 0.75rem; font-weight: 800; color: #606070; text-transform: uppercase; margin-bottom: 15px;">Live Preview</div>
                <div class="discord-view" style="margin-bottom: 30px;">
                    <div class="discord-msg">
                        <div class="discord-avatar" style="background: var(--primary); display: flex; align-items: center; justify-content: center; font-weight: 800; color: white;">H</div>
                        <div class="discord-content">
                            <div class="discord-header"><span class="discord-name">{WebConfig.NAME}</span><span class="discord-bot-tag">BOT</span></div>
                            <div x-text="currentSettings.join_msg || 'Welcome to the server!'" style="white-space: pre-wrap; font-size: 0.9rem;"></div>
                            <div x-show="currentSettings.img_enabled" class="glass" style="width: 100%; aspect-ratio: 700/250; margin-top: 10px; border-radius: 8px; overflow: hidden; background-size: cover; background-position: center;" :style="'background-image: url(' + (currentSettings.img_bg || 'https://i.imgur.com/8m5ZpX5.png') + ')'">
                                <div style="width: 100%; height: 100%; background: rgba(0,0,0,0.3); display: flex; align-items: center; padding-left: 20px; gap: 20px;">
                                    <div style="width: 60px; height: 60px; border-radius: 50%; background: #333; border: 2px solid white;"></div>
                                    <div :style="'color: ' + currentSettings.img_color">
                                        <div style="font-size: 0.7rem; font-weight: 700; opacity: 0.8;">WELCOME TO {guild.name.upper()}</div>
                                        <div style="font-size: 1.1rem; font-weight: 800;">{user['username']}</div>
                                        <div style="font-size: 0.6rem; opacity: 0.6;">Member #{guild.member_count + 1}</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="glass module-card">
                    <h3 style="margin-bottom: 15px; font-size: 1rem;">Custom Embeds</h3>
                    <div style="display: flex; flex-direction: column; gap: 8px;">
                        <template x-for="(data, name) in currentSettings.custom_embeds" :key="name">
                            <div class="glass" style="padding: 10px 15px; display: flex; justify-content: space-between; align-items: center; background: rgba(255,255,255,0.03);">
                                <span style="font-family: monospace; font-weight: 700; color: var(--primary);" x-text="'{{embed:' + name + '}}'"></span>
                            </div>
                        </template>
                    </div>
                </div>
            </div>
        </div>
        """
        return DashEngine.dash_wrapper(content, guild=guild, active_tab="greetings", user=user, bot_avatar=bot_instance.user.display_avatar.url if bot_instance.user else None)

    @app.route('/dashboard/<int:guild_id>/greetings/save', methods=['POST'])
    def save_greetings(guild_id):
        user = session.get('user')
        if not user: return abort(401)
        guild = bot_instance.get_guild(guild_id)
        if not guild: return abort(404)
        data = request.json
        config = run_async(bot_instance.db_manager.find_one('greetings_config', {'_id': guild_id})) or {}
        if data['join_channel'] or data['join_dm']:
            if 'join_actions' not in config or not config['join_actions']: config['join_actions'] = [{}]
            config['join_actions'][0].update({'message': data['join_msg'], 'channel_id': int(data['join_channel']) if data['join_channel'] else None, 'dm': data['join_dm'], 'delay': int(data['join_delay'] or 0), 'delete_after': int(data['join_delete'] or 0)})
        else: config['join_actions'] = []
        if data['leave_channel']:
            if 'leave_actions' not in config or not config['leave_actions']: config['leave_actions'] = [{}]
            config['leave_actions'][0].update({'message': data['leave_msg'], 'channel_id': int(data['leave_channel']), 'delay': int(data['leave_delay'] or 0), 'delete_after': int(data['leave_delete'] or 0)})
        else: config['leave_actions'] = []
        if data['boost_channel'] or data['boost_dm']:
            if 'boost_actions' not in config or not config['boost_actions']: config['boost_actions'] = [{}]
            config['boost_actions'][0].update({'message': data['boost_msg'], 'channel_id': int(data['boost_channel']) if data['boost_channel'] else None, 'dm': data['boost_dm'], 'delay': int(data['boost_delay'] or 0), 'delete_after': int(data['boost_delete'] or 0)})
        else: config['boost_actions'] = []
        config['image_settings'] = {'enabled': data['img_enabled'], 'background_url': data['img_bg'], 'text_color': data['img_color']}
        config.pop('_id', None)
        run_async(bot_instance.db_manager.update_one('greetings_config', {'_id': guild_id}, config, upsert=True))
        return {"status": "success"}

    @app.route('/dashboard/<int:guild_id>/security')
    def guild_security(guild_id):
        user = session.get('user')
        if not user: return redirect('/login')
        guild = bot_instance.get_guild(guild_id)
        if not guild: return abort(404)
        config = run_async(bot_instance.db_manager.find_one('antinuke_config', {'_id': guild_id})) or {}
        data_obj = {'enabled': config.get('antinuke_enabled', False), 'ban_limit': config.get('ban_limit', 3), 'kick_limit': config.get('kick_limit', 3), 'channel_limit': config.get('channel_delete_limit', 3)}
        content = f'<input type="hidden" id="initial-data" value="{to_b64_json(data_obj)}"><div class="glass module-card"><div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px;"><h2 style="display: flex; align-items: center; gap: 15px;">{Icons.SHIELD} Anti-Nuke</h2><label class="switch"><input type="checkbox" x-model="currentSettings.enabled"><span class="slider"></span></label></div><div class="input-group"><label class="input-label">Mass Ban Threshold (<span x-text="currentSettings.ban_limit"></span>)</label><input type="range" min="1" max="20" class="dash-input" x-model="currentSettings.ban_limit" style="padding: 0; height: 10px;"></div><div class="input-group"><label class="input-label">Mass Kick Threshold (<span x-text="currentSettings.kick_limit"></span>)</label><input type="range" min="1" max="20" class="dash-input" x-model="currentSettings.kick_limit" style="padding: 0; height: 10px;"></div><div class="input-group"><label class="input-label">Channel Delete Limit (<span x-text="currentSettings.channel_limit"></span>)</label><input type="range" min="1" max="10" class="dash-input" x-model="currentSettings.channel_limit" style="padding: 0; height: 10px;"></div></div>'
        return DashEngine.dash_wrapper(content, guild=guild, active_tab="security", user=user, bot_avatar=bot_instance.user.display_avatar.url if bot_instance.user else None)

    @app.route('/dashboard/<int:guild_id>/security/save', methods=['POST'])
    def save_security(guild_id):
        user = session.get('user')
        if not user: return abort(401)
        data = request.json
        update = {'antinuke_enabled': data['enabled'], 'ban_limit': int(data['ban_limit']), 'kick_limit': int(data['kick_limit']), 'channel_delete_limit': int(data['channel_limit'])}
        run_async(bot_instance.db_manager.update_one('antinuke_config', {'_id': guild_id}, update, upsert=True))
        return {"status": "success"}

    @app.route('/dashboard/<int:guild_id>/automod')
    def guild_automod(guild_id):
        user = session.get('user')
        if not user: return redirect('/login')
        guild = bot_instance.get_guild(guild_id)
        if not guild: return abort(404)
        config = run_async(bot_instance.db_manager.find_one('automod_config', {'_id': guild_id})) or {}
        data_obj = {'links': config.get('links_enabled', False), 'links_action': config.get('links_action', 'delete'), 'invites': config.get('invites_enabled', False), 'invites_action': config.get('invites_action', 'delete'), 'caps': config.get('caps_enabled', False), 'caps_action': config.get('caps_action', 'delete'), 'spam': config.get('spam_enabled', False), 'badwords': config.get('badwords_enabled', False), 'badwords_list': ", ".join(config.get('badwords', [])), 'stickers': config.get('stickers_enabled', False), 'stickers_action': config.get('stickers_action', 'delete'), 'zalgo': config.get('zalgo_enabled', False), 'zalgo_action': config.get('zalgo_action', 'delete'), 'ghostping': config.get('ghostping_enabled', False), 'newaccount': config.get('newaccount_enabled', False), 'newaccount_days': config.get('newaccount_days', 7), 'images': config.get('images_enabled', False), 'images_limit': config.get('images_limit', 5), 'mentions': config.get('mentions_enabled', False), 'mentions_limit': config.get('mentions_limit', 5), 'mentions_action': config.get('mentions_action', 'delete'), 'duplicate': config.get('duplicate_enabled', False), 'duplicate_action': config.get('duplicate_action', 'delete'), 'heat': config.get('heat_enabled', False)}
        actions_html = "".join([f'<option value="{a}">{a.capitalize()}</option>' for a in ['delete', 'warn', 'mute', 'kick', 'ban']])
        content = f"""<input type="hidden" id="initial-data" value="{to_b64_json(data_obj)}"><div class="glass module-card"><div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px;"><h2 style="display: flex; align-items: center; gap: 15px;">{Icons.AUTOMOD} Auto-Moderation</h2><div style="display: flex; align-items: center; gap: 10px; background: rgba(138, 99, 255, 0.1); padding: 8px 15px; border-radius: 10px;"><span style="font-size: 0.75rem; font-weight: 800; color: var(--primary);">HEAT ALGORITHM</span><label class="switch"><input type="checkbox" x-model="currentSettings.heat"><span class="slider"></span></label></div></div><div class="dash-grid"><div class="glass module-card" style="padding: 20px;"><h3 style="font-size: 0.9rem; margin-bottom: 20px; color: var(--primary);">Content Filtering</h3><div style="display: flex; flex-direction: column; gap: 15px;"><div style="display: flex; justify-content: space-between; align-items: center;"><span style="font-size: 0.85rem;">Anti-Links</span><div style="display: flex; gap: 10px; align-items: center;"><select class="dash-input" style="width: 100px; padding: 5px 10px; font-size: 0.7rem;" x-model="currentSettings.links_action">{actions_html}</select><label class="switch"><input type="checkbox" x-model="currentSettings.links"><span class="slider"></span></label></div></div><div style="display: flex; justify-content: space-between; align-items: center;"><span style="font-size: 0.85rem;">Anti-Invites</span><div style="display: flex; gap: 10px; align-items: center;"><select class="dash-input" style="width: 100px; padding: 5px 10px; font-size: 0.7rem;" x-model="currentSettings.invites_action">{actions_html}</select><label class="switch"><input type="checkbox" x-model="currentSettings.invites"><span class="slider"></span></label></div></div><div style="display: flex; justify-content: space-between; align-items: center;"><span style="font-size: 0.85rem;">Bad Words</span><label class="switch"><input type="checkbox" x-model="currentSettings.badwords"><span class="slider"></span></label></div><input type="text" class="dash-input" style="font-size: 0.75rem;" x-model="currentSettings.badwords_list"></div></div><div class="glass module-card" style="padding: 20px;"><h3 style="font-size: 0.9rem; margin-bottom: 20px; color: #00ff88;">Behavior</h3><div style="display: flex; flex-direction: column; gap: 15px;"><div style="display: flex; justify-content: space-between; align-items: center;"><span>Anti-Spam</span><label class="switch"><input type="checkbox" x-model="currentSettings.spam"><span class="slider"></span></label></div><div style="display: flex; justify-content: space-between; align-items: center;"><span>Duplicate</span><label class="switch"><input type="checkbox" x-model="currentSettings.duplicate"><span class="slider"></span></label></div><div style="display: flex; justify-content: space-between; align-items: center;"><span>Ghost Ping</span><label class="switch"><input type="checkbox" x-model="currentSettings.ghostping"><span class="slider"></span></label></div></div></div></div></div>"""
        return DashEngine.dash_wrapper(content, guild=guild, active_tab="automod", user=user, bot_avatar=bot_instance.user.display_avatar.url if bot_instance.user else None)

    @app.route('/dashboard/<int:guild_id>/automod/save', methods=['POST'])
    def save_automod(guild_id):
        user = session.get('user')
        if not user: return abort(401)
        data = request.json
        badwords = [w.strip().lower() for w in data['badwords_list'].split(',') if w.strip()]
        update = {'links_enabled': data['links'], 'links_action': data['links_action'], 'invites_enabled': data['invites'], 'invites_action': data['invites_action'], 'caps_enabled': data['caps'], 'caps_action': data['caps_action'], 'spam_enabled': data['spam'], 'badwords_enabled': data['badwords'], 'badwords': badwords, 'stickers_enabled': data['stickers'], 'stickers_action': data['stickers_action'], 'zalgo_enabled': data['zalgo'], 'zalgo_action': data['zalgo_action'], 'ghostping_enabled': data['ghostping'], 'newaccount_enabled': data['newaccount'], 'newaccount_days': int(data['newaccount_days']), 'images_enabled': data['images'], 'images_limit': int(data['images_limit']), 'mentions_enabled': data['mentions'], 'mentions_limit': int(data['mentions_limit']), 'mentions_action': data['mentions_action'], 'duplicate_enabled': data['duplicate'], 'duplicate_action': data['duplicate_action'], 'heat_enabled': data['heat']}
        run_async(bot_instance.db_manager.update_one('automod_config', {'_id': guild_id}, update, upsert=True))
        return {"status": "success"}

    @app.route('/dashboard/<int:guild_id>/leveling')
    def guild_leveling(guild_id):
        user = session.get('user')
        if not user: return redirect('/login')
        guild = bot_instance.get_guild(guild_id)
        if not guild: return abort(404)
        config = run_async(bot_instance.db_manager.find_one('leveling_config', {'_id': guild_id})) or {}
        data_obj = {'enabled': config.get('enabled', True), 'difficulty': config.get('difficulty', 1.0), 'reward_mode': config.get('reward_mode', 'stacking'), 'rewards': config.get('rewards', {}), 'notify_type': config.get('notify_type', 'channel'), 'notify_msg': config.get('notify_msg', "GG {user}, you just leveled up to **Level {level}**!"), 'notify_embed': config.get('notify_embed', {'title': 'Level Up!', 'description': '', 'color': '#4A3F5F', 'footer': 'Horizen'}), 'notify_channel': str(config.get('notify_channel', '')), 'multi_roles': config.get('multi_roles', {}), 'multi_channels': config.get('multi_channels', {}), 'multi_users': config.get('multi_users', {}), 'blacklist_roles': [str(r) for r in config.get('blacklist_roles', [])], 'blacklist_channels': [str(c) for c in config.get('blacklist_channels', [])]}
        channels_html = "".join([f'<option value="{c.id}">{c.name}</option>' for c in guild.text_channels])
        roles_html = "".join([f'<option value="{r.id}">{r.name}</option>' for r in sorted(guild.roles, key=lambda x: x.position, reverse=True) if not r.is_default()])
        content = f"""<input type="hidden" id="initial-data" value="{to_b64_json(data_obj)}"><div class="glass module-card"><div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px;"><h2 style="display: flex; align-items: center; gap: 15px;">{Icons.ZAP} Leveling</h2><label class="switch"><input type="checkbox" x-model="currentSettings.enabled"><span class="slider"></span></label></div><div class="dash-grid"><div class="input-group"><label class="input-label">Difficulty</label><input type="range" min="0.5" max="5.0" step="0.1" class="dash-input" x-model="currentSettings.difficulty"></div><div class="input-group"><label class="input-label">Reward Mode</label><select class="dash-input" x-model="currentSettings.reward_mode"><option value="stacking">Stacking</option><option value="single">Single</option></select></div></div></div><div class="dash-grid"><div class="glass module-card"><h3 style="color: var(--primary);">Notifications</h3><div class="input-group"><label class="input-label">Type</label><select class="dash-input" x-model="currentSettings.notify_type"><option value="channel">Channel</option><option value="dedicated">Dedicated</option><option value="dm">DM</option><option value="disabled">Disabled</option></select></div><div class="input-group" x-show="currentSettings.notify_type === 'dedicated'"><select class="dash-input" x-model="currentSettings.notify_channel">{channels_html}</select></div><textarea class="dash-input" style="min-height: 80px;" x-model="currentSettings.notify_msg"></textarea><div style="margin-top: 15px; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 15px;"><input type="text" class="dash-input" x-model="currentSettings.notify_embed.title" placeholder="Embed Title"><textarea class="dash-input" style="min-height: 80px; margin-top: 10px;" x-model="currentSettings.notify_embed.description" placeholder="Embed Description"></textarea></div></div><div class="glass module-card"><h3 style="color: #00ff88;">Rewards</h3><div style="max-height: 200px; overflow-y: auto;"><template x-for="(roles, level) in currentSettings.rewards"><div>Level <span x-text="level"></span></div></template></div></div></div>"""
        return DashEngine.dash_wrapper(content, guild=guild, active_tab="leveling", user=user, bot_avatar=bot_instance.user.display_avatar.url if bot_instance.user else None)

    @app.route('/dashboard/<int:guild_id>/leveling/save', methods=['POST'])
    def save_leveling(guild_id):
        user = session.get('user')
        if not user: return abort(401)
        data = request.json
        update = {'enabled': data['enabled'], 'difficulty': float(data['difficulty']), 'reward_mode': data['reward_mode'], 'rewards': data['rewards'], 'notify_type': data['notify_type'], 'notify_msg': data['notify_msg'], 'notify_embed': data['notify_embed'], 'notify_channel': int(data['notify_channel']) if data['notify_channel'] else None, 'multi_roles': data['multi_roles'], 'multi_channels': data['multi_channels'], 'multi_users': data['multi_users'], 'blacklist_roles': [int(r) for r in data['blacklist_roles']], 'blacklist_channels': [int(c) for c in data['blacklist_channels']]}
        run_async(bot_instance.db_manager.update_one('leveling_config', {'_id': guild_id}, update, upsert=True))
        return {"status": "success"}

    @app.route('/dashboard/<int:guild_id>/logging')
    def guild_logging(guild_id):
        user = session.get('user')
        if not user: return redirect('/login')
        guild = bot_instance.get_guild(guild_id)
        if not guild: return abort(404)
        config = run_async(bot_instance.db_manager.find_one('logging_config', {'_id': guild_id})) or {}
        events = config.get('events', {})
        data_obj = {'msg_channel': str(events.get('messages', {}).get('channel_id', '')), 'member_channel': str(events.get('members', {}).get('channel_id', '')), 'server_channel': str(events.get('server', {}).get('channel_id', '')), 'voice_channel': str(events.get('voice', {}).get('channel_id', '')), 'mod_channel': str(events.get('mod', {}).get('channel_id', '')), 'antinuke_channel': str(events.get('antinuke', {}).get('channel_id', '')), 'automod_channel': str(events.get('automod', {}).get('channel_id', '')), 'ticket_channel': str(events.get('tickets', {}).get('channel_id', '')), 'app_channel': str(events.get('apps', {}).get('channel_id', '')), 'giveaway_channel': str(events.get('giveaways', {}).get('channel_id', '')), 'suggestion_channel': str(events.get('suggestions', {}).get('channel_id', '')), 'verify_channel': str(events.get('verification', {}).get('channel_id', '')), 'invite_channel': str(events.get('invites', {}).get('channel_id', '')), 'thread_channel': str(events.get('threads', {}).get('channel_id', '')), 'webhook_channel': str(events.get('webhooks', {}).get('channel_id', '')), 'emoji_channel': str(events.get('emojis', {}).get('channel_id', '')), 'boost_channel': str(events.get('boosts', {}).get('channel_id', ''))}
        channels_html = "".join([f'<option value="{c.id}">{c.name}</option>' for c in guild.text_channels])
        content = f"""<input type="hidden" id="initial-data" value="{to_b64_json(data_obj)}"><div class="glass module-card"><h2 style="margin-bottom: 30px; display: flex; align-items: center; gap: 15px;">{Icons.LOGGING} Audit Logging</h2><div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 30px;"><div class="input-group"><label class="input-label">Messages</label><select class="dash-input" x-model="currentSettings.msg_channel"><option value="">Disabled</option>{channels_html}</select></div><div class="input-group"><label class="input-label">Members</label><select class="dash-input" x-model="currentSettings.member_channel"><option value="">Disabled</option>{channels_html}</select></div><div class="input-group"><label class="input-label">Moderation</label><select class="dash-input" x-model="currentSettings.mod_channel"><option value="">Disabled</option>{channels_html}</select></div><div class="input-group"><label class="input-label">Server</label><select class="dash-input" x-model="currentSettings.server_channel"><option value="">Disabled</option>{channels_html}</select></div><div class="input-group"><label class="input-label">Voice</label><select class="dash-input" x-model="currentSettings.voice_channel"><option value="">Disabled</option>{channels_html}</select></div><div class="input-group"><label class="input-label">Anti-Nuke</label><select class="dash-input" x-model="currentSettings.antinuke_channel"><option value="">Disabled</option>{channels_html}</select></div><div class="input-group"><label class="input-label">AutoMod</label><select class="dash-input" x-model="currentSettings.automod_channel"><option value="">Disabled</option>{channels_html}</select></div><div class="input-group"><label class="input-label">Tickets</label><select class="dash-input" x-model="currentSettings.ticket_channel"><option value="">Disabled</option>{channels_html}</select></div><div class="input-group"><label class="input-label">Applications</label><select class="dash-input" x-model="currentSettings.app_channel"><option value="">Disabled</option>{channels_html}</select></div><div class="input-group"><label class="input-label">Giveaways</label><select class="dash-input" x-model="currentSettings.giveaway_channel"><option value="">Disabled</option>{channels_html}</select></div><div class="input-group"><label class="input-label">Suggestions</label><select class="dash-input" x-model="currentSettings.suggestion_channel"><option value="">Disabled</option>{channels_html}</select></div><div class="input-group"><label class="input-label">Verification</label><select class="dash-input" x-model="currentSettings.verify_channel"><option value="">Disabled</option>{channels_html}</select></div><div class="input-group"><label class="input-label">Invites</label><select class="dash-input" x-model="currentSettings.invite_channel"><option value="">Disabled</option>{channels_html}</select></div><div class="input-group"><label class="input-label">Threads</label><select class="dash-input" x-model="currentSettings.thread_channel"><option value="">Disabled</option>{channels_html}</select></div><div class="input-group"><label class="input-label">Webhooks</label><select class="dash-input" x-model="currentSettings.webhook_channel"><option value="">Disabled</option>{channels_html}</select></div><div class="input-group"><label class="input-label">Emojis</label><select class="dash-input" x-model="currentSettings.emoji_channel"><option value="">Disabled</option>{channels_html}</select></div><div class="input-group"><label class="input-label">Boosts</label><select class="dash-input" x-model="currentSettings.boost_channel"><option value="">Disabled</option>{channels_html}</select></div></div></div>"""
        return DashEngine.dash_wrapper(content, guild=guild, active_tab="logging", user=user, bot_avatar=bot_instance.user.display_avatar.url if bot_instance.user else None)

    @app.route('/dashboard/<int:guild_id>/logging/save', methods=['POST'])
    def save_logging(guild_id):
        user = session.get('user')
        if not user: return abort(401)
        guild = bot_instance.get_guild(guild_id)
        if not guild: return abort(404)
        data = request.json
        config = run_async(bot_instance.db_manager.find_one('logging_config', {'_id': guild_id})) or {"events": {}}
        mapping = {'messages': data['msg_channel'], 'members': data['member_channel'], 'server': data['server_channel'], 'voice': data['voice_channel'], 'mod': data['mod_channel'], 'antinuke': data['antinuke_channel'], 'automod': data['automod_channel'], 'tickets': data['ticket_channel'], 'apps': data['app_channel'], 'giveaways': data['giveaway_channel'], 'suggestions': data['suggestion_channel'], 'verification': data['verify_channel'], 'invites': data['invite_channel'], 'threads': data['thread_channel'], 'webhooks': data['webhook_channel'], 'emojis': data['emoji_channel'], 'boosts': data['boost_channel']}
        for event_type, channel_id in mapping.items():
            if channel_id:
                cid = int(channel_id)
                if event_type not in config['events'] or config['events'][event_type].get('channel_id') != cid:
                    channel = guild.get_channel(cid)
                    if channel:
                        try:
                            webhook = run_async(channel.create_webhook(name="Horizen Logs"))
                            config['events'][event_type] = {'channel_id': cid, 'webhook_url': webhook.url, 'enabled': True}
                        except: pass
            else:
                if event_type in config['events']: config['events'][event_type]['enabled'] = False
        config.pop('_id', None)
        run_async(bot_instance.db_manager.update_one('logging_config', {'_id': guild_id}, config, upsert=True))
        return {"status": "success"}
