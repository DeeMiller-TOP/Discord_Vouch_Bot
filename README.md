# Vouch HQ Discord Bot

A production-ready Discord reputation bot built for **multi-server adoption** with a central **HQ/support server** for scam checks, moderation, and dispute handling.

## What’s improved

- Slash command UX for easier setup by server owners
- Cross-server vouch checks (`/allvouches`)
- Scam reporting pipeline with report IDs (`/reportscammer`)
- Optional live forwarding of scam reports to your HQ channel (`HQ_REPORT_CHANNEL_ID`)
- Trusted voucher gate per server (`/trusted`) so not everyone can issue official vouches
- Duplicate-vouch prevention by upserting one vouch per voucher/target/server
- Owner review workflow: reports are sent to owner DMs, with `/approvereport` and `/denyreport`

## Commands

### Reputation
- `/vouch user message rating` — create/update your official vouch
- `/vouches [user]` — show recent vouches in current server
- `/allvouches [user]` — show cross-server reputation
- `/scammercheck user` — summary: vouches + average + open reports
- `/reports user` — view latest 5 reports for a user

### Safety / Moderation
- `/reportscammer user reason [evidence]` — submit scam report
- `/trusted user action(add/remove)` *(admin only)* — manage who can vouch
- `/approvereport report_id` *(owner only)* — approve report (marks `resolved`)
- `/denyreport report_id` *(owner only)* — deny report (marks `rejected`)

### Utility
- `/botinfo` — bot invite and support/HQ invite
- `/restart` *(owner only)*

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure `.env`:
   ```env
   DISCORD_TOKEN=your_bot_token
   OWNER_ID=your_discord_user_id
   BOT_INVITE_URL=https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=274878024704&integration_type=0&scope=bot+applications.commands
   SUPPORT_SERVER_INVITE=https://discord.gg/your-support-server
   HQ_REPORT_CHANNEL_ID=123456789012345678  # optional public HQ feed (owner DMs are always used)
   DATABASE_PATH=vouches.db
   ```

3. Run:
   ```bash
   python bot.py
   ```

## Recommended HQ server channels

- `#start-here` — how to use commands
- `#check-reputation` — users run `/scammercheck`
- `#scam-reports` — channel ID used in `HQ_REPORT_CHANNEL_ID`
- `#case-updates` — resolved/rejected report transparency
- `#bot-support` — setup help for server owners

## Intents

Enable in Discord Developer Portal:
- **Server Members Intent**

## Notes

- This bot is designed for server owners to add and immediately use with slash commands.
- For large scale, move persistence from SQLite to Postgres.
