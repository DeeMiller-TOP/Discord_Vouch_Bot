# Discord Vouch Bot

A Discord bot that allows users to create and manage vouches for other users across multiple servers.

## Features

- Create vouches for users with custom messages
- View vouches for specific users in the current server
- View all vouches for a user across all servers
- Persistent storage using SQLite database
- Beautiful embed messages for vouch display

## Setup

1. Clone this repository
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the root directory and add your Discord bot token:
   ```
   DISCORD_TOKEN=your_bot_token_here
   ```
4. Run the bot:
   ```bash
   python bot.py
   ```

## Commands

- `!vouch @user message` - Create a vouch for a user
- `!vouches [@user]` - View vouches for a user in the current server (defaults to yourself if no user is specified)
- `!allvouches [@user]` - View all vouches for a user across all servers (defaults to yourself if no user is specified)

## Requirements

- Python 3.8 or higher
- discord.py
- python-dotenv
- aiosqlite

## Note

Make sure to enable the following intents in your Discord Developer Portal:
- Message Content Intent
- Server Members Intent 