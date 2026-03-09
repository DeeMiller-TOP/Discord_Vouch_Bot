import datetime
import os
import sys
from typing import Optional

import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

DATABASE_PATH = os.getenv("DATABASE_PATH", "vouches.db")
SUPPORT_SERVER_INVITE = os.getenv("SUPPORT_SERVER_INVITE", "https://discord.gg/your-support-server")
BOT_INVITE_URL = os.getenv(
    "BOT_INVITE_URL",
    "https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=274878024704&integration_type=0&scope=bot+applications.commands",
)
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
HQ_REPORT_CHANNEL_ID = int(os.getenv("HQ_REPORT_CHANNEL_ID", "0"))


class VouchBot(commands.Bot):
    async def setup_hook(self) -> None:
        await setup_database()
        await self.tree.sync()

    async def is_owner(self, user: discord.User) -> bool:
        return OWNER_ID != 0 and user.id == OWNER_ID


intents = discord.Intents.default()
intents.guilds = True
intents.members = True
bot = VouchBot(command_prefix="!", intents=intents)


async def setup_database() -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS vouches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                vouched_by_id TEXT NOT NULL,
                server_id TEXT NOT NULL,
                message TEXT NOT NULL,
                rating INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, vouched_by_id, server_id)
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS scam_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reported_user_id TEXT NOT NULL,
                reporter_user_id TEXT NOT NULL,
                server_id TEXT NOT NULL,
                reason TEXT NOT NULL,
                evidence TEXT,
                status TEXT NOT NULL DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS trusted_vouchers (
                guild_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                PRIMARY KEY (guild_id, user_id)
            )
            """
        )
        await db.execute("CREATE INDEX IF NOT EXISTS idx_vouches_target ON vouches(user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_reports_target ON scam_reports(reported_user_id, status)")

        cursor = await db.execute("PRAGMA table_info(vouches)")
        columns = await cursor.fetchall()
        if "rating" not in [column[1] for column in columns]:
            await db.execute("ALTER TABLE vouches ADD COLUMN rating INTEGER DEFAULT 5")

        await db.commit()


async def is_trusted(guild_id: int, user_id: int) -> bool:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM trusted_vouchers WHERE guild_id = ? AND user_id = ?",
            (str(guild_id), str(user_id)),
        ) as cursor:
            return await cursor.fetchone() is not None


def stars(rating: int) -> str:
    return "⭐" * max(1, min(5, rating))


def report_embed(report_id: int, reporter: discord.abc.User, reported: discord.abc.User, reason: str, evidence: str, guild_name: str) -> discord.Embed:
    embed = discord.Embed(title=f"🚨 New Scam Report #{report_id}", color=discord.Color.red(), timestamp=datetime.datetime.utcnow())
    embed.add_field(name="Reported User", value=f"{reported} (`{reported.id}`)", inline=False)
    embed.add_field(name="Reporter", value=f"{reporter} (`{reporter.id}`)", inline=False)
    embed.add_field(name="Source Server", value=guild_name, inline=False)
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.add_field(name="Evidence", value=evidence or "No evidence link provided", inline=False)
    return embed


def stats_embed(title: str, member: discord.abc.User, count: int, avg_rating: float) -> discord.Embed:
    embed = discord.Embed(title=title, color=discord.Color.blurple())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Total Vouches", value=str(count), inline=True)
    embed.add_field(name="Average Rating", value=f"{avg_rating:.2f}/5", inline=True)
    embed.add_field(name="Visual", value=stars(round(avg_rating)) if count else "No ratings yet", inline=False)
    return embed


@bot.event
async def on_ready() -> None:
    print(f"{bot.user} is online and synced.")


@bot.tree.command(name="botinfo", description="Get bot invite + support server links.")
async def botinfo(interaction: discord.Interaction) -> None:
    embed = discord.Embed(
        title="Vouch HQ",
        description="Add this bot to your server, then join support HQ to verify traders and report scammers.",
        color=discord.Color.green(),
    )
    embed.add_field(name="Add Bot", value=f"[Click to invite]({BOT_INVITE_URL})", inline=False)
    embed.add_field(name="Support / HQ Server", value=f"[Join HQ]({SUPPORT_SERVER_INVITE})", inline=False)
    embed.set_footer(text="Commands: /vouch /vouches /allvouches /scammercheck /reportscammer")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="vouch", description="Create or update your vouch for a member.")
@app_commands.guild_only()
@app_commands.describe(user="User to vouch", message="Why you vouch for them", rating="1 to 5")
@app_commands.choices(
    rating=[
        app_commands.Choice(name="1 ⭐", value=1),
        app_commands.Choice(name="2 ⭐⭐", value=2),
        app_commands.Choice(name="3 ⭐⭐⭐", value=3),
        app_commands.Choice(name="4 ⭐⭐⭐⭐", value=4),
        app_commands.Choice(name="5 ⭐⭐⭐⭐⭐", value=5),
    ]
)
async def vouch(interaction: discord.Interaction, user: discord.Member, message: str, rating: int) -> None:
    if user.bot:
        await interaction.response.send_message("You cannot vouch bot accounts.", ephemeral=True)
        return
    if user.id == interaction.user.id:
        await interaction.response.send_message("You cannot vouch for yourself.", ephemeral=True)
        return

    trusted = await is_trusted(interaction.guild_id, interaction.user.id)
    if not trusted and not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "Only trusted vouchers (or admins) can create vouches. Ask staff to run `/trusted add`.",
            ephemeral=True,
        )
        return

    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            INSERT INTO vouches (user_id, vouched_by_id, server_id, message, rating)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, vouched_by_id, server_id)
            DO UPDATE SET message = excluded.message, rating = excluded.rating, created_at = CURRENT_TIMESTAMP
            """,
            (str(user.id), str(interaction.user.id), str(interaction.guild_id), message[:500], rating),
        )
        await db.commit()

        async with db.execute(
            "SELECT id FROM vouches WHERE user_id = ? AND vouched_by_id = ? AND server_id = ?",
            (str(user.id), str(interaction.user.id), str(interaction.guild_id)),
        ) as cursor:
            vouch_id = (await cursor.fetchone())[0]

    embed = discord.Embed(title="✅ Vouch Saved", color=discord.Color.blue(), timestamp=datetime.datetime.utcnow())
    embed.add_field(name="Target", value=user.mention, inline=True)
    embed.add_field(name="By", value=interaction.user.mention, inline=True)
    embed.add_field(name="Rating", value=stars(rating), inline=True)
    embed.add_field(name="Message", value=message[:500], inline=False)
    embed.set_footer(text=f"Vouch ID #{vouch_id}")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="vouches", description="See server-only vouches for a user.")
@app_commands.guild_only()
@app_commands.describe(user="User to inspect")
async def vouches(interaction: discord.Interaction, user: Optional[discord.Member] = None) -> None:
    target = user or interaction.user

    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            """
            SELECT vouched_by_id, message, rating, created_at
            FROM vouches
            WHERE user_id = ? AND server_id = ?
            ORDER BY created_at DESC
            LIMIT 10
            """,
            (str(target.id), str(interaction.guild_id)),
        ) as cursor:
            rows = await cursor.fetchall()

    if not rows:
        await interaction.response.send_message(f"No vouches found for {target.mention} in this server.", ephemeral=True)
        return

    avg = sum(r[2] for r in rows) / len(rows)
    embed = stats_embed(f"Vouches for {target.display_name} (This Server)", target, len(rows), avg)
    for vouched_by_id, message, rating, created_at in rows:
        embed.add_field(name=f"{stars(rating)} by <@{vouched_by_id}> • {created_at}", value=message, inline=False)

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="allvouches", description="See all vouches for a user across servers.")
@app_commands.describe(user="User to inspect")
async def allvouches(interaction: discord.Interaction, user: Optional[discord.User] = None) -> None:
    target = user or interaction.user

    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            """
            SELECT vouched_by_id, server_id, message, rating, created_at
            FROM vouches
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 20
            """,
            (str(target.id),),
        ) as cursor:
            rows = await cursor.fetchall()

    if not rows:
        await interaction.response.send_message(f"No cross-server vouches found for <@{target.id}>.", ephemeral=True)
        return

    avg = sum(r[3] for r in rows) / len(rows)
    embed = stats_embed(f"Global Vouches for {target.display_name}", target, len(rows), avg)
    for vouched_by_id, server_id, message, rating, created_at in rows[:10]:
        guild = bot.get_guild(int(server_id))
        server_name = guild.name if guild else f"Server {server_id}"
        embed.add_field(name=f"{stars(rating)} by <@{vouched_by_id}> in {server_name} • {created_at}", value=message, inline=False)

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="reportscammer", description="Report a suspected scammer to HQ moderation.")
@app_commands.guild_only()
@app_commands.describe(user="Reported user", reason="What happened", evidence="Proof link")
async def reportscammer(interaction: discord.Interaction, user: discord.User, reason: str, evidence: Optional[str] = None) -> None:
    if user.bot:
        await interaction.response.send_message("You cannot report a bot account.", ephemeral=True)
        return
    if user.id == interaction.user.id:
        await interaction.response.send_message("You cannot report yourself.", ephemeral=True)
        return

    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT INTO scam_reports (reported_user_id, reporter_user_id, server_id, reason, evidence) VALUES (?, ?, ?, ?, ?)",
            (str(user.id), str(interaction.user.id), str(interaction.guild_id), reason[:400], (evidence or "")[:500]),
        )
        await db.commit()
        async with db.execute("SELECT last_insert_rowid()") as cursor:
            report_id = (await cursor.fetchone())[0]

    if HQ_REPORT_CHANNEL_ID:
        channel = bot.get_channel(HQ_REPORT_CHANNEL_ID)
        if isinstance(channel, discord.TextChannel):
            await channel.send(
                embed=report_embed(
                    report_id,
                    interaction.user,
                    user,
                    reason[:400],
                    (evidence or "")[:500],
                    interaction.guild.name,
                )
            )

    await interaction.response.send_message(
        f"🚨 Report submitted. ID: **#{report_id}**. HQ moderators will review it.",
        ephemeral=True,
    )


@bot.tree.command(name="scammercheck", description="Check vouch reputation + open scam reports.")
@app_commands.describe(user="User to check")
async def scammercheck(interaction: discord.Interaction, user: discord.User) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT COUNT(*), COALESCE(AVG(rating), 0) FROM vouches WHERE user_id = ?", (str(user.id),)) as cursor:
            vouch_count, avg_rating = await cursor.fetchone()

        async with db.execute(
            "SELECT COUNT(*) FROM scam_reports WHERE reported_user_id = ? AND status = 'open'",
            (str(user.id),),
        ) as cursor:
            open_reports = (await cursor.fetchone())[0]

    color = discord.Color.red() if open_reports > 0 else discord.Color.green()
    embed = discord.Embed(title=f"Reputation Check: {user}", color=color)
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="Total Vouches", value=str(vouch_count), inline=True)
    embed.add_field(name="Average Rating", value=f"{float(avg_rating):.2f}/5", inline=True)
    embed.add_field(name="Open Scam Reports", value=str(open_reports), inline=True)
    embed.description = (
        "⚠️ This user has active scam reports. Request proof and trade carefully."
        if open_reports > 0
        else "✅ No open scam reports found in HQ database."
    )
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="reports", description="See latest scam reports for a user.")
@app_commands.describe(user="User to inspect")
async def reports(interaction: discord.Interaction, user: discord.User) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            """
            SELECT id, reporter_user_id, reason, status, created_at
            FROM scam_reports
            WHERE reported_user_id = ?
            ORDER BY created_at DESC
            LIMIT 5
            """,
            (str(user.id),),
        ) as cursor:
            rows = await cursor.fetchall()

    if not rows:
        await interaction.response.send_message("No scam reports found for this user.", ephemeral=True)
        return

    embed = discord.Embed(title=f"Latest Scam Reports: {user}", color=discord.Color.orange())
    for report_id, reporter_id, reason, status, created_at in rows:
        embed.add_field(
            name=f"Report #{report_id} • {status.upper()} • by <@{reporter_id}>",
            value=f"{reason}\n`{created_at}`",
            inline=False,
        )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="trusted", description="Add/remove trusted voucher status (Admin only).")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
@app_commands.describe(user="User to update", action="add or remove")
@app_commands.choices(
    action=[
        app_commands.Choice(name="add", value="add"),
        app_commands.Choice(name="remove", value="remove"),
    ]
)
async def trusted(interaction: discord.Interaction, user: discord.Member, action: str) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        if action == "add":
            await db.execute(
                "INSERT OR IGNORE INTO trusted_vouchers (guild_id, user_id) VALUES (?, ?)",
                (str(interaction.guild_id), str(user.id)),
            )
            msg = f"✅ {user.mention} is now marked as a trusted voucher in this server."
        else:
            await db.execute(
                "DELETE FROM trusted_vouchers WHERE guild_id = ? AND user_id = ?",
                (str(interaction.guild_id), str(user.id)),
            )
            msg = f"🗑️ Removed trusted voucher flag from {user.mention}."
        await db.commit()

    await interaction.response.send_message(msg, ephemeral=True)


@bot.tree.command(name="setreportstatus", description="Update scam report status (Owner only).")
@app_commands.describe(report_id="Report ID", status="open, under_review, resolved, rejected")
@app_commands.choices(
    status=[
        app_commands.Choice(name="open", value="open"),
        app_commands.Choice(name="under_review", value="under_review"),
        app_commands.Choice(name="resolved", value="resolved"),
        app_commands.Choice(name="rejected", value="rejected"),
    ]
)
async def setreportstatus(interaction: discord.Interaction, report_id: int, status: str) -> None:
    if not await bot.is_owner(interaction.user):
        await interaction.response.send_message("Only the bot owner can update report status.", ephemeral=True)
        return

    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("UPDATE scam_reports SET status = ? WHERE id = ?", (status, report_id))
        await db.commit()

    if cursor.rowcount == 0:
        await interaction.response.send_message("Report ID not found.", ephemeral=True)
        return

    await interaction.response.send_message(f"✅ Report #{report_id} set to `{status}`.", ephemeral=True)


@bot.tree.command(name="restart", description="Restart the bot (Owner only).")
async def restart(interaction: discord.Interaction) -> None:
    if not await bot.is_owner(interaction.user):
        await interaction.response.send_message("You do not have permission.", ephemeral=True)
        return

    await interaction.response.send_message("Restarting...", ephemeral=True)
    python = sys.executable
    os.execl(python, python, *sys.argv)


token = os.getenv("DISCORD_TOKEN")
if not token:
    raise RuntimeError("DISCORD_TOKEN is not configured in environment variables.")

bot.run(token)
