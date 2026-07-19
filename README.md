# Horizen - All-in-One Discord Bot

A powerful, feature-rich Discord bot built with **discord.py** and **asyncio**. Horizen provides comprehensive tools for server management, moderation, leveling, verification, and much more.

---

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Bot](#running-the-bot)
- [Commands & Features](#commands--features)
- [Support](#support)
- [License](#license)
- [Attribution](#attribution)

---

## Features

### Core Features
- **Moderation Tools** - Kick, ban, mute, slowmode, message snipe, and edit snipe
- **Leveling System** - XP-based progression with customizable rewards and role assignments
- **Verification System** - CAPTCHA-based verification with join-gate delays
- **QR Code Tools** - Generate QR codes for text, WiFi, and vCard contact sharing
- **Anonymous Confessions** - Moderated anonymous message system
- **Message Scheduling** - Schedule messages to send at specific times with repeat options
- **Status Rewards** - Automatic role rewards based on user status
- **Custom Prefix Support** - Per-server custom command prefixes
- **Database Integration** - MongoDB support with caching
- **Web Dashboard** - Full web interface for server configuration (built with Flask)
- **Premium System** - Premium features for enhanced functionality
- **Developer Tools** - Jishaku integration for advanced debugging

### Database Support
- **MongoDB** - Primary database with multi-cluster support
- **MariaDB** - Alternative SQL database option
- **SQLite** - Local database for lightweight deployments

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/sinlt0/horizen.git
cd horizen

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file and add your Discord token
echo DISCORD_TOKEN=your_bot_token_here > .env

# Run the bot
python main.py
```

---

## Prerequisites

### System Requirements
- **Python** 3.8 or higher
- **pip** (Python package manager)
- **Git**
- **4GB+ RAM** (recommended)

### Required Accounts
- **Discord Bot Token** - From Discord Developer Portal (required)
- **MongoDB** (optional) - For production deployments

---

## Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/sinlt0/horizen.git
cd horizen
```

### Step 2: Create Virtual Environment

Create an isolated Python environment to avoid dependency conflicts:

```bash
python -m venv venv
```

Activate the virtual environment:

**On Windows:**
```bash
venv\Scripts\activate
```

**On macOS/Linux:**
```bash
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs all required packages including:
- `discord.py` - Discord bot framework
- `python-dotenv` - Environment variable management
- `pymongo` - MongoDB driver
- `flask` - Web dashboard
- `pillow` - Image processing
- And more...

### Step 4: Configure Environment

Create a `.env` file in the root directory:

```bash
touch .env
```

Add the following to your `.env` file:

```
DISCORD_TOKEN=your_bot_token_here
```

That's it! All other configurations are handled automatically by:
- `utils/config.py` - Default bot configuration
- `website/app.py` - Web dashboard configuration

---

## Configuration

### Getting Your Discord Bot Token

1. Visit the **Discord Developer Portal**: https://discord.com/developers/applications
2. Click **"New Application"** and give your bot a name
3. Go to the **"Bot"** tab on the left sidebar
4. Click **"Add Bot"**
5. Under the **TOKEN** section, click **"Copy"** to copy your bot token
6. Paste the token in your `.env` file:
   ```
   DISCORD_TOKEN=your_copied_token_here
   ```

### Inviting the Bot to Your Server

1. In the Developer Portal, go to **"OAuth2"** tab
2. Click **"URL Generator"** in the left menu
3. Under **Scopes**, select:
   - `bot`
4. Under **Permissions**, select all permissions your bot needs:
   - Manage Messages
   - Manage Roles
   - Ban Members
   - Kick Members
   - Manage Channels
   - Manage Webhooks
   - Send Messages
   - Embed Links
   - Attach Files
   - Add Reactions
   - Read Message History

5. Copy the generated **URL** at the bottom
6. Paste it in your browser and select your server
7. Authorize the bot

### Default Configuration

The bot comes pre-configured with sensible defaults:

| Setting | Default Value | File |
|---------|---------------|------|
| **Command Prefix** | `!` | `utils/config.py` |
| **Database** | SQLite (data/sqlite.db) | `utils/config.py` |
| **Embed Color** | `#4A3F5F` (Purple) | `utils/config.py` |
| **Debug Mode** | Disabled | `utils/config.py` |

### Advanced Configuration (Optional)

If you want to customize further, you can modify `utils/config.py`:

**MongoDB Setup** (for production):
```python
MONGODB_CLUSTERS = {
    "primary": "your_mongodb_connection_string"
}
MONGODB_DB_NAME = "discord_bot"
```

**Custom Prefix**:
```python
DEFAULT_PREFIX = "!"
```

**Web Dashboard** (Optional):
- The bot includes a Flask web dashboard at `http://127.0.0.1:30449`
- Configure web authentication in `utils/config.py` if needed

---

## Running the Bot

### Start the Bot

```bash
python main.py
```

The bot will:
1. Initialize the database connection
2. Load all cogs (commands)
3. Connect to Discord
4. Display online status
5. Start listening for commands

### Expected Output

```
[INFO] Connecting to Discord...
[INFO] Logged in as Horizen#1234
[INFO] Database initialized
[INFO] Loaded 15 cogs
[INFO] Bot is ready!
```

### Testing the Bot

Once online, test in your Discord server:

```
!help
```

This displays all available command categories.

### Stopping the Bot

Press **Ctrl+C** in the terminal to gracefully shut down the bot.

---

## Commands & Features

### Default Prefix: `!`

### Command Categories

**Moderation**
```
!snipe - View last deleted message
!editsnipe - View last edited message
!slowmode [seconds] - Set channel slowmode
!nuke - Nuke (recreate) the channel
```

**Leveling**
```
!profile - View your level and rank
!leaderboard - View server leaderboard
!rank [user] - Check user's rank
```

**Utility**
```
!qrcode [text] - Generate QR code
!qrwifi [ssid] [password] - Generate WiFi QR
!confession [message] - Send anonymous confession
!schedule send [channel] [delay] [message] - Schedule a message
```

**Verification**
```
!verify - Start verification process
!verification setup [channel] [role] - Configure verification
```

For complete command list:
```
!help
```

---

## Troubleshooting

### Bot Won't Start

1. **Check Token**: Ensure `DISCORD_TOKEN` is correct in `.env`
2. **Check Python**: Verify `python --version` shows 3.8+
3. **Install Dependencies**: Run `pip install -r requirements.txt` again
4. **Check Firewall**: Ensure Discord API isn't blocked

### Commands Not Working

1. **Check Prefix**: Default is `!` (can be changed per-server)
2. **Check Permissions**: Bot must have proper server permissions
3. **Check Channel**: Some commands only work in specific channels
4. **Enable Intents**: Ensure all Discord intents are enabled in Developer Portal

### Database Issues

1. **SQLite (Default)**: Check `data/sqlite.db` file exists
2. **MongoDB**: Verify connection string in `utils/config.py`
3. **Permissions**: Ensure database user has proper permissions

---

## Support

- **GitHub Issues**: https://github.com/sinlt0/horizen/issues
- **Discord Support Server**: https://discord.gg/KdnAKcHupW

---

## Development

### Project Structure

```
horizen/
├── main.py                 # Bot entry point
├── cogs/                   # Command modules
│   ├── moderation.py
│   ├── leveling.py
│   ├── verification.py
│   └── ...
├── utils/                  # Utility modules
│   ├── config.py          # Configuration
│   ├── database.py        # Database manager
│   └── ...
├── website/               # Web dashboard
│   ├── app.py
│   └── ...
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables
└── README.md
```

### Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## License

This project is licensed under the **Apache License 2.0**. See the [LICENSE](LICENSE) file for details.

---

## Attribution

**Horizen** was created by **Sinlt**

If you use this code in your project, please provide appropriate credit to the original author in a visible location within your application or documentation.

---

## Changelog

### v1.0.0 - Initial Release
- Core moderation tools
- Leveling system
- Verification system
- Utility commands
- Web dashboard
- Premium system

---

**Made with love by the Horizen Team**
