# Greetings & Custom Embeds

Make a lasting first impression with Horizen's interactive **Greetings** engine. Supports custom variables, delayed messages, and a live embed editor.

## Welcome, Leave & Boost
You can set up unique actions for when a member joins, leaves, or boosts your server.

### Basic Setup
- **Set Message:** `!greet message Welcome {user} to {server_name}!`
- **Set Channel:** `!greet channel #welcome`
- **Test:** `!greet test`

Replace `!greet` with `!leave` or `!boost` for other events.

## Live Embed Editor
Horizen features a "Mimu-style" live editor for creating professional embeds without leaving Discord.

1. **Create a template:** `!embed create my_welcome`
2. **Open the editor:** `!embed editor my_welcome`
3. **Customize:** Use the buttons to change Title, Description, Color, Images, and more.
4. **Usage:** Link it to your greet message using `{embed:my_welcome}`.

## Dynamic Variables
Use these placeholders in your messages or embeds to display real-time data:

- `{user}` - Mentions the user
- `{user_name}` - The user's name
- `{server_name}` - Name of your server
- `{member_count}` - Total members (e.g., 100)
- `{member_count_ordinal}` - Ordinal count (e.g., 100th)
- `{account_age}` - Days since account creation
- `{join_date}` - Relative join time (e.g., 2 minutes ago)
- `{boost_count}` - Total server boosts

## Features
- **Auto-Delete:** Set messages to disappear after a certain time.
- **DM Greetings:** Send welcome messages directly to a user's DMs.
- **Variable Parsing:** Every field in the embed editor supports full variable parsing.
