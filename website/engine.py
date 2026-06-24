import random
from .styles import Styles
from .icons import Icons
from .webconfig import WebConfig

class UIEngine:
    @staticmethod
    def generate_stars(count=WebConfig.STAR_COUNT):
        stars = ""
        for _ in range(count):
            top = random.randint(0, 100)
            left = random.randint(0, 100)
            duration = random.uniform(2, 5)
            size = random.uniform(1, 3)
            stars += f'<div class="star" style="top: {top}%; left: {left}%; width: {size}px; height: {size}px; --duration: {duration}s"></div>'
        return stars

    @staticmethod
    def generate_comets(count=10):
        comets = ""
        for i in range(count):
            duration = random.randint(10, 20)
            delay = random.randint(0, 30)
            top = random.randint(-50, 50)
            left = random.randint(50, 150)
            comets += f'<div class="comet" style="--duration: {duration}s; --delay: {delay}s; --top: {top}%; --left: {left}%"></div>'
        return comets

    @staticmethod
    def page_wrapper(content, title=f"{WebConfig.NAME} Bot", active_page="home", user=None, bot_avatar=None):
        profile_html = ""
        if user:
            profile_html = f"""
            <div class="user-profile-container" x-data="{{ open: false }}">
                <div @click="open = !open" class="user-pfp-wrapper">
                    <img src="{user['avatar']}" class="user-avatar-nav" alt="{user['username']}">
                    <div class="online-indicator"></div>
                </div>
                <div x-show="open" @click.outside="open = false" x-transition class="glass user-dropdown">
                    <div class="dropdown-header">
                        <div class="dropdown-user-name">{user['display_name']}</div>
                        <div class="dropdown-user-handle">@{user['username']}</div>
                    </div>
                    <div class="dropdown-divider"></div>
                    <a href="/dashboard" class="dropdown-item">
                        {Icons.CONFIG} Dashboard
                    </a>
                    <a href="/logout" class="dropdown-item logout-btn">
                        {Icons.SHIELD} Logout
                    </a>
                </div>
            </div>
            """
        else:
            profile_html = f"""
            <div class="user-profile-container">
                <a href="/login" class="btn glass login-btn" style="padding: 8px 20px; font-size: 0.85rem;">
                    {Icons.USER} Login
                </a>
            </div>
            """

        logo_placeholder = f'<div style="background: var(--primary); width: 32px; height: 32px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 0.8rem; font-weight: 800;">H</div>'
        
        if bot_avatar:
            logo_html = f"""
            <div style="position: relative; width: 32px; height: 32px;">
                <img src="{bot_avatar}" 
                     style="width: 32px; height: 32px; border-radius: 8px; object-fit: cover;" 
                     @error="$el.style.display='none'; $nextTick(() => {{ $el.nextElementSibling.style.display='flex' }})">
                <div style="display: none; background: var(--primary); width: 32px; height: 32px; border-radius: 8px; align-items: center; justify-content: center; font-size: 0.8rem; font-weight: 800;">H</div>
            </div>
            """
        else:
            logo_html = logo_placeholder

        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title}</title>
            <style>{Styles.GLOBAL}</style>
            <script defer src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js"></script>
        </head>
        <body>
            <div class="star-container">
                {UIEngine.generate_stars()}
                {UIEngine.generate_comets()}
            </div>
            
            <header class="main-header">
                <div style="flex: 1; display: flex; align-items: center;">
                    <a href="/" style="text-decoration: none; color: white; font-weight: 800; font-size: 1.2rem; display: flex; align-items: center; gap: 10px;">
                        {logo_html}
                        <span class="desktop-only">HORIZEN</span>
                    </a>
                </div>

                <nav class="glass nav-bar">
                    <a href="/" class="nav-btn {'active' if active_page == 'home' else ''}" title="Home">{Icons.HOME}</a>
                    <a href="/commands" class="nav-btn {'active' if active_page == 'commands' else ''}" title="Commands">{Icons.LIST}</a>
                    <a href="/embed" class="nav-btn {'active' if active_page == 'embed' else ''}" title="Embed Builder">{Icons.WAND}</a>
                    <a href="/team" class="nav-btn {'active' if active_page == 'team' else ''}" title="Team">{Icons.USERS}</a>
                    <a href="/docs" class="nav-btn {'active' if active_page == 'docs' else ''}" title="Documentation">{Icons.BOOK}</a>
                </nav>

                <div style="flex: 1; display: flex; justify-content: flex-end; align-items: center;">
                    {profile_html}
                </div>
            </header>

            <main>
                {content}
            </main>

            <footer class="footer">
                <div style="color: var(--primary); font-weight: 800; margin-bottom: 20px;">{WebConfig.NAME} SYSTEMS</div>
                <div style="display: flex; justify-content: center; gap: 20px; margin-bottom: 20px;">
                    <a href="/tos" style="color: #a0a0b0; text-decoration: none; font-size: 0.9rem;">ToS</a>
                    <a href="/privacy" style="color: #a0a0b0; text-decoration: none; font-size: 0.9rem;">Privacy</a>
                </div>
                <p style="color: #606070; font-size: 0.8rem;">&copy; 2026 {WebConfig.NAME} Bot. Built with pure Python.</p>
            </footer>
        </body>
        </html>
        """

    @staticmethod
    def hero_section(bot_name, stats):
        return f"""
        <div class="container">
            <div class="hero">
                <h1>{bot_name}</h1>
                <p>{WebConfig.DESCRIPTION}</p>
                <div style="display: flex; gap: 16px; flex-wrap: wrap; justify-content: center;">
                    <a href="/invite" class="btn btn-primary">{Icons.ZAP} Invite Bot</a>
                    <a href="/dashboard" class="btn glass" style="color: white;">{Icons.CONFIG} Dashboard</a>
                </div>
                
                <div style="margin-top: 80px; display: flex; gap: clamp(20px, 8vw, 80px); flex-wrap: wrap; justify-content: center;">
                    <div style="text-align: center;">
                        <div style="font-size: 2.5rem; font-weight: 900; color: white;">{stats['guilds']}</div>
                        <div style="color: var(--primary); font-size: 0.75rem; font-weight: 800; text-transform: uppercase; letter-spacing: 2px;">Servers</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 2.5rem; font-weight: 900; color: white;">{stats['users']}</div>
                        <div style="color: var(--primary); font-size: 0.75rem; font-weight: 800; text-transform: uppercase; letter-spacing: 2px;">Users</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 2.5rem; font-weight: 900; color: white;">{stats['cmds']}</div>
                        <div style="color: var(--primary); font-size: 0.75rem; font-weight: 800; text-transform: uppercase; letter-spacing: 2px;">Commands</div>
                    </div>
                </div>
            </div>
        </div>
        """

    @staticmethod
    def features_grid():
        features = [
            (Icons.SHIELD, "AntiNuke", "Wick-level protection. Stops mass bans, kicks, and channel deletions from rogue admins before they happen."),
            (Icons.AUTOMOD, "AutoMod", "Advanced Heat algorithm detects raids and spam. Smart link and invite filtering with custom whitelists."),
            (Icons.LOGGING, "Logging", "High-performance event tracking. Log message edits, deletions, and every moderator action instantly."),
            (Icons.USER, "Greetings", "Mimu-style welcome, leave, and boost messages with live visual simulators and image card generation."),
            (Icons.ZAP, "Leveling", "Engage your community with a robust XP system, custom rank cards, and automated role rewards."),
            (Icons.TICKET, "Tickets", "Enterprise-grade support system with multi-panel creation, transcripts, and private staff threads."),
            (Icons.GIFT, "Giveaways", "Host professional giveaways with requirements, persistent task loops, and automated winner selection."),
            (Icons.TERMINAL, "VoiceMaster", "Temporary voice channels with a persistent interface. Users can lock, hide, and name their own rooms."),
            (Icons.WAND, "Embeds", "The industry's fastest web-based embed builder. Create, save, and manage templates with a live preview.")
        ]
        
        cards = ""
        for icon, title, desc in features:
            cards += f"""
            <div class="glass feature-card">
                <div class="feature-icon-wrapper">{icon}</div>
                <h3>{title}</h3>
                <p>{desc}</p>
            </div>
            """
            
        return f"""
        <div class="container" style="margin-top: 100px;">
            <div style="text-align: center; margin-bottom: 60px;">
                <h2 style="font-size: 2.5rem; font-weight: 900; margin-bottom: 15px;">Built for Performance</h2>
                <p style="color: #606070;">Every module is engineered for speed and reliability at scale.</p>
            </div>
            <div class="grid-container">
                {cards}
            </div>
        </div>
        """

    @staticmethod
    def commands_section(categories, commands_b64, cat_icons_b64):
        return f"""
        <div class="container" style="max-width: 1200px; margin: 80px auto; padding: 20px;">
            <div style="text-align: center; margin-bottom: 60px;">
                <h1 style="font-size: 3.5rem; margin-bottom: 20px;">Command Suite</h1>
                <p style="color: #a0a0b0; max-width: 600px; margin: 0 auto;">Comprehensive list of all available commands to manage your server efficiently.</p>
            </div>
            <!-- Interactive Command Grid provided by app.py via alpine.js -->
        </div>
        """

    @staticmethod
    def team_section(data):
        return "" # Logic is already in app.py for team

    @staticmethod
    def docs_section(content, files, current):
        sidebar = ""
        for f in files:
            active = "active" if f['path'] == current else ""
            sidebar += f'<a href="/docs/{f["path"]}" class="docs-nav-item {active}">{f["name"]}</a>'
            
        return f"""
        <div class="container">
            <div class="docs-container">
                <aside class="docs-sidebar glass">
                    <h3 style="margin-bottom: 20px; font-size: 0.9rem; color: var(--primary); text-transform: uppercase; letter-spacing: 1px;">Guides</h3>
                    {sidebar}
                </aside>
                <main class="docs-content glass">
                    {content}
                </main>
            </div>
        </div>
        """

    @staticmethod
    def leaderboard_page(guild_name, data):
        rows = ""
        for i, user in enumerate(data):
            rank = i + 1
            rank_class = "rank-gold" if rank == 1 else "rank-silver" if rank == 2 else "rank-bronze" if rank == 3 else ""
            rows += f"""
            <div class="glass leaderboard-row">
                <div class="rank-badge {rank_class}">{rank}</div>
                <img src="{user['avatar']}" class="user-avatar-small">
                <div class="user-info">
                    <div class="user-name">{user['name']}</div>
                    <div class="user-id">ID: {user['id']}</div>
                </div>
                <div class="stats-group">
                    <div class="stat-item">
                        <span class="stat-label">LEVEL</span>
                        <span class="stat-value">{user['level']}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">TOTAL XP</span>
                        <span class="stat-value">{user['xp']}</span>
                    </div>
                </div>
            </div>
            """
        
        return f"""
        <div class="container" style="margin-top: 80px;">
            <div style="text-align: center; margin-bottom: 60px;">
                <h1 style="font-size: clamp(2.5rem, 8vw, 4rem); font-weight: 900; margin-bottom: 10px;">Leaderboard</h1>
                <p style="color: var(--primary); font-weight: 800; text-transform: uppercase; letter-spacing: 2px;">{guild_name}</p>
            </div>

            <div class="leaderboard-container">
                {rows if rows else '<div class="glass" style="text-align: center; padding: 60px; color: #606070; font-weight: 600;">No XP data found for this server.</div>'}
            </div>
        </div>
        """
