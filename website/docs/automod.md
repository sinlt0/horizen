# AutoMod Configuration

Keep your community safe and clean with Horizen's advanced **AutoMod** suite. Unlike standard filters, Horizen uses intelligent algorithms to detect patterns of abuse.

## The Heat Algorithm
The **Heat Algorithm** is our premier protection feature. It assigns "heat" to users for every message they send.
- Mentions and Links add more heat.
- Heat decays over time.
- If a user reaches **100% Heat**, they are automatically muted for 30 minutes to prevent a raid.

**Enable Heat:** `!automod heat true`

## Modular Filters
You can toggle specific protections on or off. Most filters support an `action` parameter (`delete`, `warn`, `mute`).

| Command | Description |
|---------|-------------|
| `!automod links` | Block unauthorized links |
| `!automod invites` | Block Discord server invites |
| `!automod spam` | Detect rapid repeated messages |
| `!automod caps` | Limit excessive uppercase usage |
| `!automod images` | Set a limit for attachments per message |
| `!automod mentions` | Limit the number of mentions per message |
| `!automod stickers` | Block sticker spam |
| `!automod zalgo` | Block distorted "zalgo" text |

## Bad Words System
Create a custom list of prohibited words or phrases.
- **View words:** `!automod badwords`
- **Add/Remove:** `!automod badwords <word1, word2>`

## Native Integration
Horizen can also configure Discord's built-in AutoMod for you, which works even when the bot is offline.
- `!automod native spam`
- `!automod native keyword <word1, word2>`

## Whitelisting
To allow certain users or channels to bypass AutoMod:
- `!whitelist add <user/channel/role>`
- Use `!whitelist automod add <user>` for specific AutoMod-only immunity.
