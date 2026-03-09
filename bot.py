import os
import discord
from discord.ext import commands
import aiosqlite
from dotenv import load_dotenv
import datetime
from discord import app_commands
import sys
import asyncio

# Load environment variables
load_dotenv()

# Bot setup with all required intents
intents = discord.Intents.all()  # This enables all intents

class VouchBot(commands.Bot):
    async def setup_hook(self):
        await self.tree.sync()

    async def is_owner(self, user: discord.User) -> bool:
        """Check if the user is the bot owner"""
       return user.id == 706877545693446389

bot = VouchBot(command_prefix='!', intents=intents)

# Database setup
async def setup_database():
    async with aiosqlite.connect('vouches.db') as db:
        # First create the table if it doesn't exist
        await db.execute('''
            CREATE TABLE IF NOT EXISTS vouches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                vouched_by_id TEXT NOT NULL,
                server_id TEXT NOT NULL,
                message TEXT NOT NULL,
                rating INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Check if rating column exists
        cursor = await db.execute("PRAGMA table_info(vouches)")
        columns = await cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        # Add rating column if it doesn't exist
        if 'rating' not in column_names:
            try:
                await db.execute('ALTER TABLE vouches ADD COLUMN rating INTEGER DEFAULT 5')
                print("Added rating column to vouches table")
            except Exception as e:
                print(f"Error adding rating column: {e}")
        
        await db.commit()

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    await setup_database()

def get_star_rating(rating):
    """Convert numeric rating to star emojis"""
    stars = {
        1: "⭐",
        2: "⭐⭐",
        3: "⭐⭐⭐",
        4: "⭐⭐⭐⭐",
        5: "⭐⭐⭐⭐⭐"
    }
    return stars.get(rating, "No rating")

@bot.tree.command(name="vouch", description="Vouch for a user with a message and rating.")
@app_commands.describe(
    user="The user you want to vouch for",
    message="Your vouch message",
    rating="Rating from 1 to 5 stars"
)
@app_commands.choices(rating=[
    app_commands.Choice(name="⭐", value=1),
    app_commands.Choice(name="⭐⭐", value=2),
    app_commands.Choice(name="⭐⭐⭐", value=3),
    app_commands.Choice(name="⭐⭐⭐⭐", value=4),
    app_commands.Choice(name="⭐⭐⭐⭐⭐", value=5),
])
async def vouch_slash(interaction: discord.Interaction, user: discord.Member, message: str, rating: int):
    if user.id == interaction.user.id:
        await interaction.response.send_message("You cannot vouch for yourself!", ephemeral=True)
        return

    await interaction.response.defer()

    try:
        async with aiosqlite.connect('vouches.db') as db:
            await db.execute(
                'INSERT INTO vouches (user_id, vouched_by_id, server_id, message, rating) VALUES (?, ?, ?, ?, ?)',
                (str(user.id), str(interaction.user.id), str(interaction.guild.id), message, rating)
            )
            await db.commit()
            # Get the last vouch ID
            async with db.execute('SELECT last_insert_rowid()') as cursor:
                vouch_id = (await cursor.fetchone())[0]

        # Format date/time
        now = datetime.datetime.now()
        vouched_at = now.strftime('%Y-%m-%d %H:%M:%S')
        footer_time = now.strftime('%m/%d/%y, %I:%M %p')

        embed = discord.Embed(
            title="New vouch created!",
            color=discord.Color.blue()
        )
        embed.add_field(name="", value=get_star_rating(rating), inline=False)
        embed.add_field(name="Vouch:", value=message, inline=False)
        embed.add_field(name="Vouch N°-", value=str(vouch_id), inline=True)
        embed.add_field(name="Vouched by:", value=interaction.user.mention, inline=True)
        embed.add_field(name="Vouched at:", value=vouched_at, inline=True)
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=f"Service provided by DADA G • {footer_time}")
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)

@bot.command(name='vouches')
async def view_vouches(ctx, member: discord.Member = None):
    """View vouches for a user"""
    if member is None:
        member = ctx.author

    async with aiosqlite.connect('vouches.db') as db:
        async with db.execute(
            'SELECT * FROM vouches WHERE user_id = ? AND server_id = ?',
            (str(member.id), str(ctx.guild.id))
        ) as cursor:
            vouches = await cursor.fetchall()

    if not vouches:
        await ctx.send(f"No vouches found for {member.mention}")
        return

    embed = discord.Embed(
        title=f"Vouches for {member.name}",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=member.display_avatar.url)

    total_rating = 0
    for vouch in vouches:
        vouched_by = await bot.fetch_user(int(vouch[2]))
        rating = vouch[5]  # Get rating from database
        total_rating += rating
        
        embed.add_field(
            name=f"Vouch by {vouched_by.name} {get_star_rating(rating)}",
            value=vouch[4],  # Message
            inline=False
        )

    # Calculate average rating
    avg_rating = total_rating / len(vouches) if vouches else 0
    embed.add_field(
        name="Average Rating",
        value=f"{get_star_rating(round(avg_rating))} ({avg_rating:.1f}/5.0)",
        inline=False
    )

    await ctx.send(embed=embed)

@bot.command(name='allvouches')
async def all_vouches(ctx, member: discord.Member = None):
    """View all vouches for a user across all servers"""
    if member is None:
        member = ctx.author

    async with aiosqlite.connect('vouches.db') as db:
        async with db.execute(
            'SELECT * FROM vouches WHERE user_id = ?',
            (str(member.id),)
        ) as cursor:
            vouches = await cursor.fetchall()

    if not vouches:
        await ctx.send(f"No vouches found for {member.mention} across all servers")
        return

    embed = discord.Embed(
        title=f"All Vouches for {member.name}",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=member.display_avatar.url)

    total_rating = 0
    for vouch in vouches:
        vouched_by = await bot.fetch_user(int(vouch[2]))
        server = bot.get_guild(int(vouch[3]))
        server_name = server.name if server else "Unknown Server"
        rating = vouch[5]  # Get rating from database
        total_rating += rating
        
        embed.add_field(
            name=f"Vouch by {vouched_by.name} in {server_name} {get_star_rating(rating)}",
            value=vouch[4],  # Message
            inline=False
        )

    # Calculate average rating
    avg_rating = total_rating / len(vouches) if vouches else 0
    embed.add_field(
        name="Average Rating",
        value=f"{get_star_rating(round(avg_rating))} ({avg_rating:.1f}/5.0)",
        inline=False
    )

    await ctx.send(embed=embed)

@bot.tree.command(name="restart", description="Restart the bot (Owner only)")
async def restart(interaction: discord.Interaction):
    """Restart the bot"""
    if not await bot.is_owner(interaction.user):
        await interaction.response.send_message("You don't have permission to use this command!", ephemeral=True)
        return

    await interaction.response.send_message("Restarting bot...", ephemeral=True)
    
    # Close database connections
    async with aiosqlite.connect('vouches.db') as db:
        await db.close()
    
    # Restart the bot
    python = sys.executable
    os.execl(python, python, *sys.argv)

@bot.tree.command(name="restore", description="Send all vouches for all members in this server.")
async def restore(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    count = 0
    for member in interaction.guild.members:
        async with aiosqlite.connect('vouches.db') as db:
            async with db.execute('SELECT * FROM vouches WHERE user_id = ?', (str(member.id),)) as cursor:
                vouches = await cursor.fetchall()
                for vouch in vouches:
                    vouched_by_id = int(vouch[2])
                    vouched_by = await interaction.client.fetch_user(vouched_by_id)
                    message = vouch[4]
                    rating = vouch[5]
                    vouch_id = vouch[0]
                    created_at = vouch[6]
                    # Format date/time
                    try:
                        dt = datetime.datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
                        vouched_at = dt.strftime('%Y-%m-%d %H:%M:%S')
                        footer_time = dt.strftime('%m/%d/%y, %I:%M %p')
                    except Exception:
                        vouched_at = created_at
                        footer_time = created_at
                    embed = discord.Embed(
                        title="New vouch created!",
                        color=discord.Color.blue()
                    )
                    embed.add_field(name="", value=get_star_rating(rating), inline=False)
                    embed.add_field(name="Vouch:", value=message, inline=False)
                    embed.add_field(name="Vouch N°-", value=str(vouch_id), inline=True)
                    embed.add_field(name="Vouched by:", value=vouched_by.mention if vouched_by else str(vouched_by_id), inline=True)
                    embed.add_field(name="Vouched at:", value=vouched_at, inline=True)
                    embed.set_thumbnail(url=member.display_avatar.url)
                    embed.set_footer(text=f"Service provided by DADA G • {footer_time}")
                    await interaction.channel.send(embed=embed)
                    count += 1
    await interaction.followup.send(f"Restored {count} vouches to this server!", ephemeral=True)

# Run the bot
bot.run(os.getenv('DISCORD_TOKEN')) 
