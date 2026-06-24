from ..engine import UIEngine
from ..icons import Icons
from .styles import DashStyles
import json

class DashEngine:
    @staticmethod
    def dash_wrapper(content, guild=None, active_tab="home", user=None, bot_avatar=None):
        sidebar = ""
        tabs = []
        if guild:
            tabs = [
                ('home', Icons.GENERAL, f"/dashboard/{guild.id}"),
                ('embeds', Icons.WAND, f"/dashboard/{guild.id}/embeds"),
                ('greetings', Icons.USER, f"/dashboard/{guild.id}/greetings"),
                ('security', Icons.SHIELD, f"/dashboard/{guild.id}/security"),
                ('automod', Icons.AUTOMOD, f"/dashboard/{guild.id}/automod"),
                ('leveling', Icons.ZAP, f"/dashboard/{guild.id}/leveling"),
                ('logging', Icons.LOGGING, f"/dashboard/{guild.id}/logging"),
            ]
            
            sidebar_items = ""
            for tab_id, icon, url in tabs:
                active_class = "active" if active_tab == tab_id else ""
                sidebar_items += f"""
                <a href="{url}" class="dash-nav-item {active_class}">
                    {icon} {tab_id.capitalize()}
                </a>
                """
            
            sidebar = f"""
            <aside class="dash-sidebar">
                <div style="display: flex; align-items: center; gap: 12px; padding: 0 10px 20px; margin-bottom: 20px; border-bottom: 1px solid var(--glass-border);">
                    <img src="{guild.icon.url if guild.icon else 'https://cdn.discordapp.com/embed/avatars/0.png'}" style="width: 40px; height: 40px; border-radius: 12px;">
                    <div style="overflow: hidden;">
                        <div style="font-weight: 800; font-size: 0.9rem; white-space: nowrap; text-overflow: ellipsis;">{guild.name}</div>
                        <div style="font-size: 0.7rem; color: #606070; font-weight: 600;">Server Dashboard</div>
                    </div>
                </div>
                {sidebar_items}
                <div style="margin-top: auto;">
                    <a href="/dashboard" class="dash-nav-item">
                        {Icons.LIST} Back to Servers
                    </a>
                </div>
            </aside>
            """

        save_bar = f"""
        <div class="glass save-bar" :class="isDirty ? 'visible' : ''">
            <div style="display: flex; align-items: center; gap: 15px;">
                <div style="background: rgba(138, 99, 255, 0.1); width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; color: var(--primary);">
                    {Icons.WAND}
                </div>
                <div>
                    <div style="font-weight: 800; font-size: 0.9rem;">Unsaved Changes</div>
                    <div style="font-size: 0.75rem; color: #a0a0b0;">Careful - you have modified some settings.</div>
                </div>
            </div>
            <div style="display: flex; gap: 12px;">
                <button @click="resetSettings()" class="btn glass" style="padding: 10px 20px; font-size: 0.8rem;">Reset</button>
                <button @click="saveSettings()" class="btn btn-primary" style="padding: 10px 25px; font-size: 0.8rem;">
                    <span x-show="!saving">Save Changes</span>
                    <span x-show="saving" style="display: flex; align-items: center; gap: 8px;">
                        <svg class="animate-spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>
                        Saving...
                    </span>
                </button>
            </div>
        </div>
        """

        full_content = f"""
        <style>{DashStyles.DASHBOARD}</style>
        <div class="dash-container" x-data="dashHandler()">
            {sidebar}
            
            <div class="dash-mobile-nav">
                {"".join([f'<a href="{url}" class="mobile-nav-item {"active" if active_tab == tab_id else ""}">{icon} {tab_id.capitalize()}</a>' for tab_id, icon, url in tabs]) if guild else ""}
            </div>

            <main class="dash-content">
                {content}
            </main>
            {save_bar if guild else ""}
        </div>
        <script>
        function dashHandler() {{
            return {{
                originalSettings: {{}},
                currentSettings: {{}},
                saving: false,
                get isDirty() {{
                    return JSON.stringify(this.originalSettings) !== JSON.stringify(this.currentSettings);
                }},
                init() {{
                    if (document.getElementById('initial-data')) {{
                        try {{
                            const b64Data = document.getElementById('initial-data').value;
                            const decoded = atob(b64Data);
                            const data = JSON.parse(decoded);
                            this.originalSettings = JSON.parse(JSON.stringify(data));
                            this.currentSettings = JSON.parse(JSON.stringify(data));
                        }} catch (e) {{
                            console.error('State Init Error:', e);
                        }}
                    }}
                }},
                resetSettings() {{
                    this.currentSettings = JSON.parse(JSON.stringify(this.originalSettings));
                }},
                async saveSettings() {{
                    this.saving = true;
                    try {{
                        const resp = await fetch(window.location.pathname + '/save', {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify(this.currentSettings)
                        }});
                        if (resp.ok) {{
                            this.originalSettings = JSON.parse(JSON.stringify(this.currentSettings));
                        }} else {{
                            alert('Failed to save settings: ' + await resp.text());
                        }}
                    }} catch (e) {{
                        alert('Error saving: ' + e.message);
                    }}
                    this.saving = false;
                }}
            }}
        }}
        </script>
        """
        return UIEngine.page_wrapper(full_content, title="Dashboard - Horizen", active_page="dashboard", user=user, bot_avatar=bot_avatar)

    @staticmethod
    def guild_selector(guilds):
        cards = ""
        for g in guilds:
            name = g['name']
            icon_html = ""
            if g['icon']:
                icon_url = f"https://cdn.discordapp.com/icons/{g['id']}/{g['icon']}.png"
                icon_html = f'<img src="{icon_url}" class="guild-icon-lg" onerror="this.style.display=\'none\'; this.nextElementSibling.style.display=\'flex\';">'
                # Fallback for broken links
                icon_html += f'<div class="guild-icon-placeholder" style="display: none;">{name[0].upper()}</div>'
            else:
                icon_html = f'<div class="guild-icon-placeholder">{name[0].upper()}</div>'

            cards += f"""
            <a href="/dashboard/{g['id']}" class="glass guild-card">
                <div style="position: relative; margin-bottom: 5px;">
                    {icon_html}
                </div>
                <div class="guild-name-text" title="{name}">{name}</div>
                <div class="btn-manage-small">MANAGE</div>
            </a>
            """
        
        return f"""
        <div style="max-width: 1200px; margin: 60px auto; padding: 0 20px;">
            <div style="text-align: center; margin-bottom: 50px;">
                <h1 style="font-size: 3rem; font-weight: 800; margin-bottom: 15px; background: linear-gradient(to right, #fff, #8a63ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">Select a Server</h1>
                <p style="color: #606070; font-size: 1.1rem;">Manage your communities and systems from one dashboard.</p>
            </div>
            
            <div class="guild-grid">
                {cards if cards else '<div style="grid-column: 1/-1; text-align: center; padding: 60px; color: #444;">No manageable servers found. Make sure you have Manage Server permission!</div>'}
            </div>
        </div>
        """
