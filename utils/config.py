import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

                                   
                                                       
    MONGODB_CLUSTERS = {
        "primary": "mongodb+srv://CodeX:CodeX@codex-in1.ito65ix.mongodb.net/?appName=CodeX-in1",
        "asia_in_2": "mongodb+srv://CodeX:CodeX@codex-in2.4cnbbw7.mongodb.net/?appName=CodeX-in2",
        "us_east_1": "mongodb+srv://CodeX:CodeX@codex-in3.evr1nui.mongodb.net/?appName=CodeX-in3",
    }
    MONGODB_DB_NAME = os.getenv('MONGODB_DB_NAME', 'discord_bot')

                      
    MARIADB_HOST = os.getenv('MARIADB_HOST', 'localhost')
    MARIADB_PORT = int(os.getenv('MARIADB_PORT', '3306'))
    MARIADB_USER = os.getenv('MARIADB_USER', 'root')
    MARIADB_PASSWORD = os.getenv('MARIADB_PASSWORD', '')
    MARIADB_DB_NAME = os.getenv('MARIADB_DB_NAME', 'discord_bot')

                     
    SQLITE_DB_PATH = os.getenv('SQLITE_DB_PATH', './data/sqlite.db')

                                                     
    DEFAULT_PREFIX = os.getenv('DEFAULT_PREFIX', '!')

                                                   
    MARIADB_CLUSTER = os.getenv('MARIADB_CLUSTER', '').split(',') if os.getenv('MARIADB_CLUSTER') else []
    SQLITE_CLUSTER = os.getenv('SQLITE_CLUSTER', '').split(',') if os.getenv('SQLITE_CLUSTER') else []

                    
    DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 't')
    AUTO_HYDRATE_SQLITE = os.getenv('AUTO_HYDRATE_SQLITE', 'True').lower() in ('true', '1', 't')
    AUTO_REVERSE_SYNC = os.getenv('AUTO_REVERSE_SYNC', 'True').lower() in ('true', '1', 't')
    EMBED_COLOR = 0x4A3F5F
    HIDDEN_CATEGORIES = ['dev', 'premium', 'owner', 'collection']
    
    SUPPORT_SERVER = 'https://discord.gg/KdnAKcHupW'
    INVITE_LINK = 'https://discord.com/oauth2/authorize?client_id=1167721021323870258&permissions=8&scope=bot'
    WEBSITE = 'http://127.0.0.1:30449'

    # Website Authentication (Discord OAuth2)
    # Placeholder values - Please replace these with your actual credentials
    DISCORD_CLIENT_ID = '1167721021323870258' 
    DISCORD_CLIENT_SECRET = 'SUxurPH2PAqCDSkciGiw4nJ5fw1cT7we' 
    DISCORD_REDIRECT_URI = f'{WEBSITE}/callback'
    SECRET_KEY = '737389Sgcktek27bQiehlohpwg3jghswoXxx'
    USER_AGENT = 'DiscordBot (https://horizen.systems, 1.0.0)'

    # Social Media API Keys (Optional)
    TWITCH_CLIENT_ID = os.getenv('TWITCH_CLIENT_ID')
    TWITCH_CLIENT_SECRET = os.getenv('TWITCH_CLIENT_SECRET')

    # Advanced Music System (Lavalink)
    # Automatically load-balances and fails over between these nodes
    LAVALINK_NODES = [
        {
            "identifier": "Jirayu-Proxy",
            "host": "lavalink.jirayu.net",
            "port": 13592,
            "password": "youshallnotpass",
            "secure": False,
            "region": "asia"
        },
        {
            "identifier": "Serenetia-V4",
            "host": "lavalinkv4.serenetia.com",
            "port": 80,
            "password": "https://seretia.link/discord",
            "secure": False,
            "region": "us"
        }
    ]

    LOFI_STATIONS = {
        "Groove Salad (Ambient/Downtempo)": "https://ice.somafm.com/groovesalad-128-mp3",
        "Drone Zone (Atmospheric/Ambient)": "https://ice.somafm.com/dronezone-128-mp3",
        "Lush (Sensuous Ambient)": "https://ice.somafm.com/lush-128-mp3",
        "Digitalis (Ambient/Electronica)": "https://ice.somafm.com/digitalis-128-mp3",
        "Fluid (Downtempo/Liquid)": "https://ice.somafm.com/fluid-128-mp3",
        "Groove Salad Classic (Early Chill)": "https://ice.somafm.com/gsclassic-128-mp3",
        "Deep Space One (Deep Ambient)": "https://ice.somafm.com/deepspaceone-128-mp3",
        "DEF CON Radio (Hacker/Electronic)": "https://ice.somafm.com/defcon-128-mp3",
        "Space Station Soma (Spaced-out Ambient)": "https://ice.somafm.com/spacestation-128-mp3",
        "Beat Blender (Deep House/Chill)": "https://ice.somafm.com/beatblender-128-mp3",
        "Suburbs of Goa (Desi-Chilled Beats)": "https://ice.somafm.com/suburbsofgoa-128-mp3",
        "Secret Agent (Mellow Cinematic Lounge)": "https://ice.somafm.com/secretagent-128-mp3",
        "Chillsky (Lofi Hip-Hop Main)": "https://lfhh.radioca.st/stream",
        "Chillsky Lite (Mellow Study Beats)": "https://lfhh.radioca.st/stream2",
        "HearMe Lofi (Vinyl Crackle/Relax)": "http://radio.hearme.fm:8366/stream",
        "Radio Paradise (Mellow Mix)": "https://stream.radioparadise.com/mellow-128",
        "Radio Paradise (Chill Mix)": "https://stream.radioparadise.com/chill-128",
    }
    
