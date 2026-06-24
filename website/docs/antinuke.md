# AntiNuke Protection

Horizen features **Wick-level AntiNuke** protection, designed to stop rogue administrators and compromised accounts from destroying your server.

## How it Works
The AntiNuke system monitors administrative actions in real-time. If a user exceeds a pre-defined threshold of actions (e.g., deleting 3 channels in 10 seconds), Horizen instantly strips their permissions and applies a punishment.

## Configuration Commands

### Toggle Protection
Enable or disable the entire AntiNuke suite.
- `!antinuke toggle <true/false>`

### Set Punishment
Choose how Horizen handles offenders.
- `!antinuke punishment quarantine` (Recommended: Strips all roles and gives a restricted role)
- `!antinuke punishment ban` (Permanently removes the user from the server)

### Adjusting Limits
You can customize how sensitive the system is for different actions.
- `!antinuke limit <action> <number>`

**Valid Actions:**
`ban`, `kick`, `role_delete`, `role_create`, `channel_delete`, `channel_create`, `webhook`, `emoji_delete`, `bot_add`, `dangerous_perms`

## Advanced Features

### Panic Mode
Instantly lock down your server by stripping all permissions from the `@everyone` role.
- `!antinuke panic <true/false>`

### Vanity Protection
Automatically restores your server's Vanity URL if an unauthorized user attempts to change or remove it.
- `!antinuke vanity <true/false>`

### Dangerous Perms Monitoring
Detects when a user is granted high-risk permissions (like Administrator) and reverts the change if the moderator isn't whitelisted.

## Whitelisting
To prevent AntiNuke from triggering on your trusted co-owners:
- Use `!whitelist add <user>` to grant immunity.
- Extra Owners (set via `!extraowner add`) are automatically immune to all AntiNuke checks.
