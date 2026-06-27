import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

                                   
                                                       
    MONGODB_CLUSTERS = {
        "primary": "mongodb+srv://codex:codex@cdx-in-1.0idu7ol.mongodb.net/?appName=cdx-in-1",
        "asia_in_2": "mongodb+srv://codex:codex@cdx-in-2.nvi4kep.mongodb.net/?appName=cdx-in-2",
        "us_east_1": "mongodb+srv://codex:codex@cdx-us-1.zunskft.mongodb.net/?appName=cdx-us-1",
        "asia_mumbai": "mongodb+srv://AeroX:AeroX@aerox.rv3nxmb.mongodb.net/?retryWrites=true&w=majority&appName=AeroX",
        "europe_frankfurt": "mongodb+srv://AeroX:AeroX@aerox.hae9rfp.mongodb.net/?retryWrites=true&w=majority&appName=AeroX",
        "asia_singapore": "mongodb+srv://AeroX:AeroX@aerox.cgfxn4x.mongodb.net/?retryWrites=true&w=majority&appName=AeroX",
        "asia_tokyo": "mongodb+srv://AeroX:AeroX@aerox.cgvmit4.mongodb.net/?retryWrites=true&w=majority&appName=AeroX",

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
            "Groove Salad (Ambient/Downtempo)": "https://ice.somafm.com/groovesalad",
            "Drone Zone (Atmospheric)": "https://ice.somafm.com/dronezone",
            "Groove Salad Classic (2000s Chill)": "https://ice.somafm.com/gsclassic",
            "Space Station Soma (Ambient Electronic)": "https://ice.somafm.com/spacestation",
            "Deep Space One (Experimental)": "https://ice.somafm.com/deepspaceone",
            "Beat Blender (Deep House/Downtempo)": "https://ice.somafm.com/beatblender",
            "Chillhop (Lofi Hip-Hop)": "http://streams.fluxfm.de/Chillhop/mp3-128/streams.fluxfm.de/",
            "FluxLounge (Chillout)": "http://streams.fluxfm.de/lounge/mp3-128"
     }       
