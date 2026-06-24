from flask import Flask, redirect, render_template_string, abort, session, request, url_for
import json
import os
import markdown2
import discord
import base64
import asyncio
import urllib.parse
import urllib.request
from discord.ext import commands as discord_commands
from .engine import UIEngine
from .icons import Icons
from .webconfig import WebConfig

app = Flask(__name__)
app.secret_key = 'HORIZEN_WEB_SECRET_KEY'
bot_instance = None

def get_config():
    return bot_instance.config if bot_instance else None

def get_user():
    return session.get('user')

def get_bot_avatar():
    if bot_instance and bot_instance.user:
        try:
            return str(bot_instance.user.display_avatar.with_format('png').url)
        except:
            try:
                return str(bot_instance.user.display_avatar.url)
            except:
                pass
    return "https://cdn.discordapp.com/embed/avatars/0.png"

def run_async(coro):
    future = asyncio.run_coroutine_threadsafe(coro, bot_instance.loop)
    return future.result()

@app.route('/login')
def login():
    config = get_config()
    if not config: return "Bot not initialized"
    
    params = {
        'client_id': config.DISCORD_CLIENT_ID,
        'redirect_uri': config.DISCORD_REDIRECT_URI,
        'response_type': 'code',
        'scope': 'identify guilds'
    }
    url = f"https://discord.com/api/oauth2/authorize?{urllib.parse.urlencode(params)}"
    return redirect(url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code: return redirect('/')
    
    config = get_config()
    data = {
        'client_id': config.DISCORD_CLIENT_ID,
        'client_secret': config.DISCORD_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': config.DISCORD_REDIRECT_URI
    }
    config = get_config()
    ua = config.USER_AGENT if config else 'DiscordBot (https://horizen.systems, 1.0.0)'
    headers = {'Content-Type': 'application/x-www-form-urlencoded', 'User-Agent': ua}

    try:
        req = urllib.request.Request(
            'https://discord.com/api/v10/oauth2/token',
            data=urllib.parse.urlencode(data).encode(),
            headers=headers,
            method='POST'
        )
        with urllib.request.urlopen(req) as resp:
            token_data = json.loads(resp.read().decode())
            access_token = token_data['access_token']

        # Get User Info
        req = urllib.request.Request(
            'https://discord.com/api/v10/users/@me',
            headers={'Authorization': f"Bearer {access_token}", 'User-Agent': ua}
        )

        with urllib.request.urlopen(req) as resp:
            user_data = json.loads(resp.read().decode())
            
        session['user'] = {
            'id': user_data['id'],
            'username': user_data['username'],
            'avatar': f"https://cdn.discordapp.com/avatars/{user_data['id']}/{user_data['avatar']}.png" if user_data.get('avatar') else "https://cdn.discordapp.com/embed/avatars/0.png",
            'display_name': user_data.get('global_name') or user_data['username'],
            'token': access_token
        }
    except Exception as e:
        print(f"Auth Error: {e}")
        
    return redirect('/')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

def get_stats():
    if not bot_instance:
        return {'guilds': 0, 'users': 0, 'cmds': 0}
    return {
        'guilds': len(bot_instance.guilds),
        'users': sum(g.member_count for g in bot_instance.guilds),
        'cmds': len(bot_instance.commands)
    }

@app.route('/')
def home():
    stats = get_stats()
    content = UIEngine.hero_section("HORIZEN", stats)
    content += UIEngine.features_grid()
    return UIEngine.page_wrapper(content, active_page="home", user=get_user(), bot_avatar=get_bot_avatar())

@app.route('/commands')
def commands_page():
    if not bot_instance: return UIEngine.page_wrapper("<h2>Bot offline</h2>", active_page="commands", user=get_user(), bot_avatar=get_bot_avatar())

    hidden_cats = [c.lower() for c in bot_instance.config.HIDDEN_CATEGORIES]
    all_commands = []
    available_cats = {}

    icon_map = {
        'Config': Icons.CONFIG,
        'Info': Icons.INFO,
        'Moderation': Icons.MODERATION,
        'Security': Icons.SECURITY,
        'Antinuke': Icons.ANTINUKE,
        'Automod': Icons.AUTOMOD,
        'Voicemaster': Icons.VOICEMASTER,
        'General': Icons.GENERAL,
        'Social': Icons.SOCIAL,
        'Fun': Icons.FUN,
        'Leveling': Icons.ZAP,
        'Logging': Icons.LOGGING,
        'Nsfw': Icons.NSFW
    }

    for cmd in bot_instance.commands:
        if cmd.hidden: continue
        cog_cat = getattr(cmd.cog, 'category', 'General')
        if cog_cat.lower() in hidden_cats: continue

        cat_name = cog_cat.capitalize()
        cat_icon = icon_map.get(cat_name, Icons.FOLDER)
        available_cats[cat_name] = Icons.b64(cat_icon)

        perms = []
        for check in cmd.checks:
            try:
                if 'has_permissions' in str(check):
                    p_list = check.__closure__[0].cell_contents
                    perms.extend([p.replace('_', ' ').title() for p, v in p_list.items() if v])
            except: pass

        cd = "None"
        if cmd.cooldown:
            cd = f"{int(cmd.cooldown.per)}s"

        subs = []
        if isinstance(cmd, discord_commands.Group):
            for sub in cmd.commands:
                subs.append({
                    'name': sub.name,
                    'help': sub.help or 'No description',
                    'usage': f"!{cmd.name} {sub.name} {sub.signature}"
                })

        all_commands.append({
            'name': cmd.name,
            'category': cat_name,
            'icon_b64': Icons.b64(cat_icon),
            'help': cmd.help or 'No description provided.',
            'usage': f"!{cmd.name} {cmd.signature}",
            'permissions': perms if perms else ["Everyone"],
            'cooldown': cd,
            'subcommands': subs
        })

    commands_b64 = base64.b64encode(json.dumps(all_commands).encode()).decode()
    cat_icons_b64 = base64.b64encode(json.dumps(available_cats).encode()).decode()
    folder_icon_b64 = Icons.b64(Icons.FOLDER)

    categories_list = sorted(available_cats.keys())
    cat_buttons_html = ""
    for cat in categories_list:
        icon_svg = base64.b64decode(available_cats[cat]).decode()
        cat_buttons_html += f'<button class="filter-btn" :class="currentCat === \'{cat}\' ? \'active\' : \'\'" @click="currentCat = \'{cat}\'">{icon_svg} {cat}</button> '

    html = f"""
    <div style="max-width: 1200px; margin: 60px auto; padding: 20px; text-align: center;" 
         x-data=\'{{ 
            search: "", 
            currentCat: "All",
            openSub: null,
            commands: JSON.parse(atob("{commands_b64}")),
            catIcons: JSON.parse(atob("{cat_icons_b64}")),
            folderIcon: atob("{folder_icon_b64}"),
            get filteredCommands() {{
                return this.commands.filter(c => {{
                    const matchesSearch = c.name.toLowerCase().includes(this.search.toLowerCase()) || 
                                         c.help.toLowerCase().includes(this.search.toLowerCase());
                    const matchesCat = this.currentCat === "All" || c.category === this.currentCat;
                    return matchesSearch && matchesCat;
                }});
            }},
            get catCount() {{
                if (this.currentCat === "All") return this.commands.length;
                return this.commands.filter(c => c.category === this.currentCat).length;
            }},
            get currentIcon() {{
                if (this.currentCat === "All") return this.folderIcon;
                return atob(this.catIcons[this.currentCat]);
            }}
         }}\'>
        
        <div style="display: inline-flex; align-items: center; gap: 8px; background: rgba(138, 99, 255, 0.1); padding: 8px 16px; border-radius: 100px; border: 1px solid rgba(138, 99, 255, 0.2); margin-bottom: 20px;">
            <span style="color: var(--primary);">{Icons.CODE}</span>
            <span style="font-size: 0.8rem; font-weight: 800; color: white; text-transform: uppercase; letter-spacing: 1px;">Command Suite</span>
        </div>

        <h1 style="font-size: clamp(2.5rem, 8vw, 4rem); font-weight: 800; margin-bottom: 15px; color: white;">Explore Capabilities</h1>
        <p style="color: #a0a0b0; font-size: 1.1rem; max-width: 700px; margin: 0 auto 10px; line-height: 1.6;">
            Manage your server with ease using over {len(all_commands)} professional commands across {len(available_cats)} categories.
        </p>
        <div style="display: flex; justify-content: center; gap: 10px; margin-bottom: 40px; align-items: center; font-size: 0.9rem; color: #606070;">
            Supported prefix: <span style="background: rgba(138, 99, 255, 0.15); color: var(--primary); padding: 2px 8px; border-radius: 6px; font-weight: 800; border: 1px solid rgba(138, 99, 255, 0.3);">!</span>
        </div>
        
        <input type="text" x-model="search" placeholder="Search for a specific command..." class="search-bar">
        
        <div class="filter-container">
            <button class="filter-btn" :class="currentCat === 'All' ? 'active' : ''" @click="currentCat = 'All'">All</button>
            {cat_buttons_html}
        </div>

        <div style="text-align: left; margin-bottom: 30px; display: flex; align-items: center; justify-content: space-between;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <span style="color: var(--primary);" x-html="currentIcon"></span>
                <h2 style="font-size: 2rem; font-weight: 800; color: white;" x-text="currentCat"></h2>
            </div>
            <div style="background: rgba(255,255,255,0.05); padding: 6px 16px; border-radius: 100px; border: 1px solid rgba(255,255,255,0.1); font-size: 0.8rem; font-weight: 700; color: #a0a0b0;">
                <span x-text="catCount"></span> Commands
            </div>
        </div>

        <div class="grid-container" style="padding: 0; text-align: left;">
            <template x-for="cmd in filteredCommands" :key="cmd.name">
                <div class="glass" style="padding: 24px; border-radius: 20px; display: flex; flex-direction: column; gap: 15px;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span style="color: var(--primary);" x-html="atob(cmd.icon_b64)"></span>
                            <code style="background: var(--primary); color: white; padding: 4px 10px; border-radius: 8px; font-weight: 700; font-size: 0.9rem;" x-text="'!' + cmd.name"></code>
                        </div>
                        <div style="text-align: right;">
                            <span style="display: block; font-size: 0.7rem; text-transform: uppercase; color: var(--primary); font-weight: 800;" x-text="cmd.category"></span>
                            <span style="font-size: 0.65rem; color: #606070;">CD: <span x-text="cmd.cooldown"></span></span>
                        </div>
                    </div>

                    <p style="color: #a0a0b0; font-size: 0.9rem; line-height: 1.5; min-height: 40px;" x-text="cmd.help"></p>

                    <div style="display: flex; flex-wrap: wrap; gap: 5px;">
                        <template x-for="p in cmd.permissions">
                            <span style="font-size: 0.65rem; background: rgba(255,255,255,0.05); padding: 2px 6px; border-radius: 4px; color: #8a63ff; border: 1px solid rgba(138, 99, 255, 0.2);" x-text="p"></span>
                        </template>
                    </div>

                    <div style="margin-top: auto; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.05);">
                        <code style="color: #606070; font-size: 0.8rem; word-break: break-all;" x-text="cmd.usage"></code>
                    </div>

                    <div x-show="cmd.subcommands.length > 0">
                        <button @click="openSub = (openSub === cmd.name ? null : cmd.name)" 
                                style="width: 100%; padding: 8px; background: rgba(138, 99, 255, 0.1); border: none; border-radius: 8px; color: white; font-size: 0.8rem; cursor: pointer; font-weight: 600;">
                            <span x-text="openSub === cmd.name ? 'Hide Subcommands' : 'View ' + cmd.subcommands.length + ' Subcommands'"></span>
                        </button>

                        <div x-show="openSub === cmd.name" x-transition style="margin-top: 10px; display: flex; flex-direction: column; gap: 8px; padding-left: 10px; border-left: 2px solid var(--primary);">
                            <template x-for="sub in cmd.subcommands">
                                <div style="font-size: 0.8rem;">
                                    <div style="color: var(--primary); font-weight: 700;" x-text="'• ' + sub.name"></div>
                                    <div style="color: #606070; font-size: 0.75rem;" x-text="sub.help"></div>
                                    <code style="font-size: 0.7rem; color: #4a3f5f;" x-text="sub.usage"></code>
                                </div>
                            </template>
                        </div>
                    </div>
                </div>
            </template>
        </div>

        <div x-show="filteredCommands.length === 0" style="text-align: center; padding: 60px; color: #606070;">
            <p>No commands found matching your criteria.</p>
        </div>
    </div>
    """
    return UIEngine.page_wrapper(html, title=f"Commands - {WebConfig.NAME}", active_page="commands", user=get_user(), bot_avatar=get_bot_avatar())

@app.route('/team')
def team_page():
    team_path = os.path.join(os.path.dirname(__file__), 'team.json')
    if os.path.exists(team_path):
        with open(team_path, 'r') as f:
            data = json.load(f)
            
            html = '<div style="max-width: 1200px; margin: 60px auto; padding: 20px; text-align: center;">'
            html += '<h1 style="font-size: 3rem; font-weight: 800; margin-bottom: 60px;">The Team</h1>'
            
            for section, members in data.items():
                if not members: continue
                html += f'<h2 style="color: var(--primary); margin-bottom: 30px; font-size: 1.5rem;">{section}</h2>'
                html += '<div class="grid-container" style="justify-content: center; margin-bottom: 60px;">'
                for m in members:
                    avatar_url = m['avatarurl']
                    if bot_instance:
                        try:
                            user = bot_instance.get_user(int(m['id']))
                            if user: avatar_url = user.display_avatar.url
                            else:
                                user = run_async(bot_instance.fetch_user(int(m['id'])))
                                if user: avatar_url = user.display_avatar.url
                        except: pass

                    is_owner = section == "Owner"
                    crown_tag = f'<div style="position: absolute; top: -10px; right: -10px; background: #ffD700; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 10px rgba(255,215,0,0.5);">{Icons.CROWN}</div>' if is_owner else ""
                    html += f"""
                    <div class="glass" style="padding: 30px; text-align: center; border-radius: 20px; position: relative;">
                        <div style="position: relative; width: 80px; height: 80px; margin: 0 auto 15px;">
                            <img src="{avatar_url}" alt="{m['name']}" style="width: 100%; height: 100%; border-radius: 50%; display: block; object-fit: cover; border: 2px solid {'var(--primary)' if not is_owner else '#ffD700'};">
                            {crown_tag}
                        </div>
                        <div style="font-weight: 800; font-size: 1.2rem; color: white;">{m['name']}</div>
                        <div style="color: rgba(255,255,255,0.4); font-size: 0.75rem; font-weight: 600; margin-top: 2px;">@{m['username']}</div>
                        <div style="color: {'#ffD700' if is_owner else 'var(--primary)'}; font-size: 0.8rem; font-weight: 700; text-transform: uppercase; margin-top: 8px;">{m['role']}</div>
                    </div>
                    """
                html += '</div>'
            html += '</div>'
            return UIEngine.page_wrapper(html, title=f"Team - {WebConfig.NAME}", active_page="team", user=get_user(), bot_avatar=get_bot_avatar())
    
    return UIEngine.page_wrapper("<h2>Team page coming soon</h2>", active_page="team", user=get_user(), bot_avatar=get_bot_avatar())

@app.route('/docs')
@app.route('/docs/<path:path>')
def docs(path=None):
    docs_dir = os.path.join(os.path.dirname(__file__), 'docs')
    if not path:
        files = sorted([f[:-3] for f in os.listdir(docs_dir) if f.endswith('.md')])
        if 'getting-started' in files:
            files.insert(0, files.pop(files.index('getting-started')))
        doc_data = []
        for f in files:
            doc_data.append({'slug': f, 'title': f.replace("-", " ").capitalize()})
        docs_json = json.dumps(doc_data)
        html = f"""
        <div style="max-width: 800px; margin: 80px auto; padding: 20px;" 
             x-data=\'{{ search: "", docs: {docs_json}, get filteredDocs() {{ return this.docs.filter(d => d.title.toLowerCase().includes(this.search.toLowerCase())); }} }}\'>
            <h1 style="margin-bottom: 10px;">Documentation</h1>
            <p style="color: #606070; margin-bottom: 30px;">Find everything you need to master Horizen.</p>
            <input type="text" x-model="search" placeholder="Search guides (e.g. AntiNuke)..." class="search-bar" style="margin-bottom: 40px;">
            <div class="grid-container" style="grid-template-columns: 1fr; padding: 0;">
                <template x-for="doc in filteredDocs" :key="doc.slug">
                    <a :href="'/docs/' + doc.slug" class="glass" style="padding: 20px; text-decoration: none; color: white; display: flex; align-items: center; gap: 15px; margin-bottom: 15px;">
                        {Icons.BOOK} <span x-text="doc.title"></span>
                    </a>
                </template>
            </div>
        </div>
        """
        return UIEngine.page_wrapper(html, title="Docs - Horizen", active_page="docs", user=get_user(), bot_avatar=get_bot_avatar())
    
    file_path = os.path.join(docs_dir, f"{path}.md")
    if not os.path.exists(file_path): abort(404)
    with open(file_path, 'r') as f: md_content = f.read()
    converted = markdown2.markdown(md_content)
    html = f'<div style="max-width: 800px; margin: 80px auto; padding: 40px;" class="glass docs-content">{converted}</div>'
    return UIEngine.page_wrapper(html, active_page="docs", user=get_user(), bot_avatar=get_bot_avatar())

@app.route('/leaderboard/<int:guild_id>')
def leaderboard_page(guild_id):
    if not bot_instance: return UIEngine.page_wrapper("<h2>Bot offline</h2>", active_page="leaderboard", user=get_user(), bot_avatar=get_bot_avatar())
    guild = bot_instance.get_guild(guild_id)
    if not guild: abort(404)
    entries = run_async(bot_instance.db_manager.find('users_xp', {'guild_id': guild_id}, sort=[('xp', -1)], limit=100))
    leaderboard_data = []
    for entry in entries:
        user = guild.get_member(entry['user_id'])
        name = user.display_name if user else f"User {entry['user_id']}"
        avatar = user.display_avatar.url if user else "https://cdn.discordapp.com/embed/avatars/0.png"
        leaderboard_data.append({'name': name, 'id': entry['user_id'], 'avatar': avatar, 'level': entry['level'], 'xp': entry['xp']})
    content = UIEngine.leaderboard_page(guild.name, leaderboard_data)
    return UIEngine.page_wrapper(content, title=f"Leaderboard - {guild.name}", active_page="leaderboard", user=get_user(), bot_avatar=get_bot_avatar())

@app.route('/tos')
def tos():
    legal_dir = os.path.join(os.path.dirname(__file__), 'legal')
    file_path = os.path.join(legal_dir, 'terms-of-service.md')
    if not os.path.exists(file_path): abort(404)
    with open(file_path, 'r') as f: md_content = f.read()
    converted = markdown2.markdown(md_content)
    html = f'<div style="max-width: 800px; margin: 80px auto; padding: 40px;" class="glass docs-content">{converted}</div>'
    return UIEngine.page_wrapper(html, title="ToS - Horizen", active_page="tos", user=get_user(), bot_avatar=get_bot_avatar())

@app.route('/privacy')
def privacy():
    legal_dir = os.path.join(os.path.dirname(__file__), 'legal')
    file_path = os.path.join(legal_dir, 'privacy-policy.md')
    if not os.path.exists(file_path): abort(404)
    with open(file_path, 'r') as f: md_content = f.read()
    converted = markdown2.markdown(md_content)
    html = f'<div style="max-width: 800px; margin: 80px auto; padding: 40px;" class="glass docs-content">{converted}</div>'
    return UIEngine.page_wrapper(html, title="Privacy - Horizen", active_page="privacy", user=get_user(), bot_avatar=get_bot_avatar())

@app.route('/embed')
def embed_builder():
    bot_av = get_bot_avatar()
    html = f"""
    <div class="builder-container" x-data=\'{{
        webhook_url: "",
        content: "Hello from Horizen!",
        username: "{WebConfig.NAME}",
        avatar_url: "",
        bot_av: "{bot_av}",
        embeds: [{{
            title: "Professional Embed",
            description: "Customize this embed using the editor on the left!",
            color: "#8a63ff",
            author_name: "", author_icon: "",
            footer_text: "Horizen Systems", footer_icon: "",
            image: "", thumbnail: "",
            fields: []
        }}],
        async sendWebhook() {{
            if (!this.webhook_url) return alert("Please enter a Webhook URL");
            try {{
                const payload = {{
                    content: this.content, username: this.username, avatar_url: this.avatar_url || this.bot_av,
                    embeds: this.embeds.map(e => ({{
                        title: e.title || null, description: e.description || null,
                        color: parseInt(e.color.replace("#", ""), 16),
                        author: e.author_name ? {{ name: e.author_name, icon_url: e.author_icon || null }} : null,
                        footer: e.footer_text ? {{ text: e.footer_text, icon_url: e.footer_icon || null }} : null,
                        image: e.image ? {{ url: e.image }} : null,
                        thumbnail: e.thumbnail ? {{ url: e.thumbnail }} : null,
                        fields: e.fields.length > 0 ? e.fields : null
                    }}))
                }};
                const res = await fetch(this.webhook_url, {{
                    method: "POST", headers: {{ "Content-Type": "application/json" }}, body: JSON.stringify(payload)
                }});
                if (res.ok) alert("Message sent successfully!");
                else alert("Failed to send: " + await res.text());
            }} catch (e) {{ alert("Error: " + e.message); }}
        }},
        addEmbed() {{
            if (this.embeds.length >= 10) return alert("Maximum 10 embeds allowed");
            this.embeds.push({{ title: "New Embed", description: "", color: "#8a63ff", author_name: "", author_icon: "", footer_text: "", footer_icon: "", image: "", thumbnail: "", fields: [] }});
        }},
        removeEmbed(index) {{
            this.embeds.splice(index, 1);
        }},
        addField(index) {{ this.embeds[index].fields.push({{ name: "New Field", value: "Field Value", inline: true }}); }},
        removeField(eIdx, fIndex) {{ this.embeds[eIdx].fields.splice(fIndex, 1); }}
    }}\'>
        <div class="editor-section">
            <h1 style="font-size: 2.5rem; font-weight: 800; margin-bottom: 10px;">Embed Builder</h1>
            <p style="color: #606070; margin-bottom: 30px;">Design and send beautiful Discord webhooks instantly.</p>

            <div class="glass" style="padding: 24px; border-radius: 20px;">
                <h3 style="margin-bottom: 20px; font-size: 1rem; color: var(--primary);">WEBHOOK CONFIG</h3>
                <div class="input-group">
                    <label>Webhook URL</label>
                    <input type="text" x-model="webhook_url" class="builder-input" placeholder="https://discord.com/api/webhooks/...">
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                    <div class="input-group">
                        <label>Webhook Name</label>
                        <input type="text" x-model="username" class="builder-input">
                    </div>
                    <div class="input-group">
                        <label>Avatar URL</label>
                        <input type="text" x-model="avatar_url" class="builder-input" :placeholder="bot_av">
                    </div>
                </div>
            </div>

            <div class="glass" style="padding: 24px; border-radius: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h3 style="font-size: 1rem; color: var(--primary);">EMBEDS</h3>
                    <button @click="addEmbed()" class="btn glass" style="padding: 6px 12px; font-size: 0.75rem; border-color: var(--primary); color: var(--primary);">+ ADD EMBED</button>
                </div>
                <textarea x-model="content" class="builder-input" style="min-height: 80px; resize: vertical; margin-bottom: 20px;" placeholder="Message content..."></textarea>
            </div>

            <template x-for="(embed, index) in embeds" :key="index">
                <div class="glass" style="padding: 24px; border-radius: 20px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                        <h3 style="font-size: 1rem; color: var(--primary);" x-text="'EMBED ' + (index + 1)"></h3>
                        <button x-show="embeds.length > 1" @click="removeEmbed(index)" style="background: rgba(255,71,87,0.1); border: none; padding: 6px 12px; border-radius: 8px; color: #ff4757; font-size: 0.7rem; cursor: pointer; font-weight: 800;">REMOVE</button>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: 1fr 100px; gap: 15px;">
                        <div class="input-group">
                            <label>Title</label>
                            <input type="text" x-model="embed.title" class="builder-input">
                        </div>
                        <div class="input-group">
                            <label>Color</label>
                            <input type="color" x-model="embed.color" style="height: 45px; cursor: pointer;" class="builder-input">
                        </div>
                    </div>
                    <div class="input-group"><label>Description</label><textarea x-model="embed.description" class="builder-input" style="min-height: 80px;"></textarea></div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                        <div class="input-group"><label>Author Name</label><input type="text" x-model="embed.author_name" class="builder-input"></div>
                        <div class="input-group"><label>Author Icon</label><input type="text" x-model="embed.author_icon" class="builder-input"></div>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                        <div class="input-group"><label>Image URL</label><input type="text" x-model="embed.image" class="builder-input"></div>
                        <div class="input-group"><label>Thumbnail</label><input type="text" x-model="embed.thumbnail" class="builder-input"></div>
                    </div>
                    <div class="input-group"><label>Footer Text</label><input type="text" x-model="embed.footer_text" class="builder-input"></div>

                    <div style="margin-top: 20px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                            <h4 style="font-size: 0.8rem; font-weight: 800; color: #606070; text-transform: uppercase;">Fields</h4>
                            <button @click="addField(index)" style="background: var(--primary); border: none; padding: 4px 12px; border-radius: 6px; color: white; cursor: pointer; font-size: 0.7rem; font-weight: 800;">+ ADD FIELD</button>
                        </div>
                        <div style="display: flex; flex-direction: column; gap: 10px;">
                            <template x-for="(field, fIdx) in embed.fields" :key="fIdx">
                                <div style="display: flex; gap: 10px; align-items: flex-start; background: rgba(0,0,0,0.2); padding: 10px; border-radius: 8px;">
                                    <input type="text" x-model="field.name" class="builder-input" style="padding: 8px;">
                                    <input type="text" x-model="field.value" class="builder-input" style="padding: 8px;">
                                    <button @click="removeField(index, fIdx)" style="background: #ff4757; border: none; padding: 8px; border-radius: 6px; color: white; cursor: pointer;">{Icons.SHIELD}</button>
                                </div>
                            </template>
                        </div>
                    </div>
                </div>
            </template>
            <button @click="sendWebhook()" class="btn btn-primary" style="width: 100%; justify-content: center; padding: 16px;">{Icons.ZAP} SEND WEBHOOK</button>
        </div>

        <div class="preview-section">
            <h3 style="font-size: 0.75rem; font-weight: 800; color: #606070; text-transform: uppercase; margin-bottom: 15px; letter-spacing: 1px;">Live Discord Preview</h3>
            <div class="discord-view">
                <div class="discord-msg">
                    <img :src="avatar_url || bot_av" class="discord-avatar">
                    <div class="discord-content">
                        <div class="discord-header">
                            <span class="discord-name" x-text="username"></span>
                            <span class="discord-bot-tag">BOT</span>
                            <span class="discord-time">Today at 12:00 PM</span>
                        </div>
                        <div x-text="content" style="margin-bottom: 8px; white-space: pre-wrap;"></div>
                        <template x-for="embed in embeds">
                            <div class="discord-embed" :style="'border-left-color: ' + embed.color" style="position: relative; margin-bottom: 8px;">
                                <div x-show="embed.author_name" class="discord-embed-author">
                                    <img x-show="embed.author_icon" :src="embed.author_icon" @error="$el.style.display='none'">
                                    <span x-text="embed.author_name"></span>
                                </div>
                                <div x-show="embed.title" class="discord-embed-title" x-text="embed.title"></div>
                                <div x-show="embed.description" class="discord-embed-description" x-text="embed.description"></div>
                                <div x-show="embed.fields.length > 0" class="discord-embed-fields">
                                    <template x-for="field in embed.fields">
                                        <div class="discord-field" :class="field.inline ? 'inline' : ''">
                                            <div class="discord-field-name" x-text="field.name"></div>
                                            <div class="discord-field-value" x-text="field.value"></div>
                                        </div>
                                    </template>
                                </div>
                                <img x-show="embed.thumbnail" :src="embed.thumbnail" class="discord-embed-thumbnail" @error="$el.style.display='none'">
                                <img x-show="embed.image" :src="embed.image" class="discord-embed-image" @error="$el.style.display='none'">
                                <div x-show="embed.footer_text" class="discord-embed-footer">
                                    <img x-show="embed.footer_icon" :src="embed.footer_icon" @error="$el.style.display='none'">
                                    <span x-text="embed.footer_text"></span>
                                </div>
                            </div>
                        </template>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """
    return UIEngine.page_wrapper(html, title=f"Embed Builder - {WebConfig.NAME}", active_page="embed", user=get_user(), bot_avatar=get_bot_avatar())

@app.route('/invite')
def invite(): return redirect(bot_instance.config.INVITE_LINK if bot_instance else "/")
@app.route('/support')
def support(): return redirect(bot_instance.config.SUPPORT_SERVER if bot_instance else "/")

def run_server(bot, port=WebConfig.PORT):
    global bot_instance
    bot_instance = bot
    
    from .dash.router import init_dash_routes
    init_dash_routes(app, bot)

    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    print(f"Website starting on port: {port}")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
