# Getting Started with Horizen

Welcome to **Horizen**, the next generation of Discord security and management. This guide will help you set up the essentials and secure your server in under 5 minutes.

## 1. Invite & Permissions
First, ensure Horizen is in your server with the correct permissions.
- **Invite Link:** [Click here to invite Horizen](https://discord.com/oauth2/authorize?client_id=1167721021323870258&permissions=8&scope=bot)
- **Role Hierarchy:** For Horizen to protect your server effectively, its role must be **as high as possible** in your role list. This allows it to manage other roles and handle rogue administrators.

## 2. Basic Configuration
Horizen uses a standard prefix (`!`) by default, but you can also mention the bot.

- **Set a custom prefix:** `!setprefix <new_prefix>`
- **Check bot status:** `!botinfo`

## 3. Core Security Setup
We recommend setting up these three modules immediately:

### A. AntiNuke (The Shield)
Protect your server from mass bans, kicks, and channel deletions.
1. Run `!antinuke toggle true` to enable protection.
2. Set your punishment type with `!antinuke punishment quarantine`.
3. Review your limits with `!antinuke`.

### B. AutoMod (The Filter)
Keep your chat clean from spam, raids, and malicious links.
1. Enable the Heat algorithm: `!automod heat true`.
2. Toggle specific filters like `!automod links true` or `!automod spam true`.

### C. Verification (The Gatekeeper)
Stop self-bot raids before they start.
1. Run `!verify setup` to create a professional verification portal.
2. Ensure new members can't see your main channels until they verify.

## 4. Need Help?
If you run into any issues or need advanced configuration assistance:
- Join our [Support Server](https://discord.gg/KdnAKcHupW)
- Explore the specific module docs for **AntiNuke** and **AutoMod**.
