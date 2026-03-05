# Vouch HQ Discord Bot

A multi-server reputation bot for communities that trade, middleman, or provide services.

This version is built to be **shared across many servers** and connected to a central **Support / HQ server** where users can:
- verify trust using cross-server vouches,
- report suspicious users,
- check scam risk before dealing.

## Why this is better

- ✅ Slash-command first UX (easy for non-technical server owners)
- ✅ Cross-server reputation lookups
- ✅ Scam reporting workflow with report IDs
- ✅ Trusted-voucher system (admins control who can submit vouches)
- ✅ Invite + support server command for growth (`/botinfo`)
- ✅ SQLite persistence out of the box

## Commands

### Reputation
- `/vouch user message rating`  
  Create a vouch (trusted vouchers or admins only).
- `/vouches [user]`  
  View recent vouches for a user in the current server.
- `/allvouches [user]`  
  View cross-server vouches for a user.
- `/scammercheck user`  
  See total vouches, average rating, and open scam reports.

### Safety / Moderation
- `/reportscammer user reason [evidence]`  
  Submit a scam report to HQ database (returns report ID).
- `/trusted user action(add/remove)` *(admin only)*  
  Control who can issue official vouches in your server.

### Utility
- `/botinfo`  
  Shows bot invite + support/HQ invite links.
- `/restart` *(owner only)*

## Setup

1. Clone repository and install deps:
   ```bash
   pip install -r requirements.txt
   ```

2. Create `.env`:
   ```env
   DISCORD_TOKEN=your_bot_token
   OWNER_ID=your_discord_user_id
   BOT_INVITE_URL=https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=274878024704&integration_type=0&scope=bot+applications.commands
   SUPPORT_SERVER_INVITE=https://discord.gg/your-support-server
   DATABASE_PATH=vouches.db
   ```

3. Run bot:
   ```bash
   python bot.py
   ```

## Recommended HQ server structure

For your support/HQ Discord server, create:
- `#start-here` (how to use bot + rules)
- `#vouch-lookup` (where users run `/scammercheck`)
- `#report-a-scammer` (guide to `/reportscammer` + evidence rules)
- `#resolved-cases` (public trust transparency)
- `#bot-support` (technical support)

## Required Discord intents

Enable in Discord Developer Portal:
- **Server Members Intent**
- **Message Content Intent**

## Notes

- By default, only trusted vouchers and admins can submit vouches.
- Keep evidence links permanent (Imgur, Drive with public read, etc.) for moderation reviews.
- For production scale, migrate from SQLite to Postgres.
