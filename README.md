# Horizen

Horizen is an all-in-one Discord bot built with discord.py and asyncio. It provides comprehensive features including moderation, leveling, verification, utility tools, and more for managing and enhancing your Discord server.

## Features

- Moderation tools (kick, ban, mute, slowmode, snipe)
- Leveling system with rewards
- Verification and CAPTCHA system
- QR code generation tools
- Anonymous confession system
- Message scheduling
- Status rewards
- Custom prefix support
- Database integration
- Web dashboard
- Premium system

## Prerequisites

Before installing Horizen, make sure you have the following:

- Python 3.8 or higher
- pip (Python package manager)
- Git
- MongoDB (for database support)
- A Discord bot token (from Discord Developer Portal)

## Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/sinlt0/horizen.git
cd horizen
```

### Step 2: Create a Virtual Environment

```bash
python -m venv venv
```

Activate the virtual environment:

On Windows:
```bash
venv\Scripts\activate
```

On macOS/Linux:
```bash
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

Create a `.env` file in the root directory and add the following:

```
DISCORD_TOKEN=your_bot_token_here
MONGO_URI=your_mongodb_connection_string
OWNER_ID=your_discord_user_id
```

Replace the values with your actual credentials.

## Setup Guide

### Getting Your Bot Token

1. Visit the Discord Developer Portal: https://discord.com/developers/applications
2. Click "New Application" and give your bot a name
3. Navigate to the "Bot" tab and click "Add Bot"
4. Under the TOKEN section, click "Copy" to copy your token
5. Paste this token in your `.env` file as `DISCORD_TOKEN`

### Getting Your MongoDB URI

1. Create a MongoDB Atlas account or use a local MongoDB instance
2. For MongoDB Atlas, follow their connection guide
3. Copy your connection string
4. Paste this in your `.env` file as `MONGO_URI`

### Getting Your Owner ID

1. Enable Developer Mode in Discord (User Settings > Advanced > Developer Mode)
2. Right-click on your Discord profile and select "Copy User ID"
3. Paste this in your `.env` file as `OWNER_ID`

### Inviting the Bot to Your Server

1. Go to the Discord Developer Portal and select your application
2. Navigate to "OAuth2" tab, then "URL Generator"
3. Under Scopes, select `bot`
4. Under Permissions, select the permissions your bot needs:
   - Manage Messages
   - Manage Roles
   - Ban Members
   - Kick Members
   - Manage Channels
   - Send Messages
   - Embed Links
   - Attach Files
   - Add Reactions
5. Copy the generated URL and open it in your browser
6. Select the server you want to add the bot to and authorize

## Running the Bot

Once all configuration is complete, start the bot:

```bash
python main.py
```

The bot will connect to Discord and start responding to commands.

## Configuration

Each feature can be configured on a per-server basis using commands. Use the help command to see available commands:

```
h!help
```

(Replace `h!` with your configured prefix)

## Support

For issues, questions, or suggestions, please open an issue on GitHub: https://github.com/sinlt0/horizen/issues

## License

This project is licensed under the Apache License 2.0. See the LICENSE file for more information.

## Attribution

Horizen was created by Sinlt. If you use this code in your project, please provide appropriate credit to the original author.
