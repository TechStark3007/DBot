import discord
from discord.ext import commands
import autoreact  # Autoreact functionality
import fact  # Fact functionality
import os
import firebase_admin
from dotenv import load_dotenv
from utilities import extensions
from firebase_admin import credentials, firestore
from keep_alive import keep_alive


#keep_alive()


# Load environment variables from .env file
load_dotenv()
# Fetch bot token from environment variable
bot_token = os.getenv('DISCORD_BOT_TOKEN')

# Initialize Firebase
# cred = credentials.Certificate('firebase_key.json')
# firebase_admin.initialize_app(cred)

# Initialize Firestore (or Realtime Database if you prefer)
#db = firestore.client()

# Initialize Realtime Database
#realtime_db = db.reference()

# Initialize bot
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True  # Required to read message content

bot = commands.Bot(command_prefix="/", intents=intents)

# Add the ping command
@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")

@bot.command(name="clearcommand")
async def clear_command(ctx, command_name: str):
    # Fetch all the registered global commands
    commands = await bot.tree.fetch_commands()

    # Find the command to delete
    command_to_delete = next((cmd for cmd in commands if cmd.name == command_name), None)

    if command_to_delete:
        # Remove the command
        await bot.tree.remove_command(command_to_delete.name, type=discord.AppCommandType.chat_input)
        await bot.tree.sync()  # Sync to apply changes
        await ctx.send(f"Slash command `/ {command_name}` has been deleted.")
    else:
        await ctx.send(f"Slash command `/ {command_name}` not found.")
   

guild_id = discord.Object(id=1215008007344103575) 
# Setup functionalities
@bot.event
async def on_ready():
    # Setup functionse
    await autoreact.setup(bot)
    await fact.setup_facts(bot)

    # Load extensions from utilities/extensions.py
    await extensions.load_extensions(bot)

    await bot.tree.sync(guild=guild_id)  
    async def on_ready():
        await bot.tree.sync(guild=discord.Object(id=guild_id))
        print(f"Synced commands for {bot.user} in guild {guild_id}")
    print(f'Logged in as {bot.user}!')

# Run the bot
bot.run(bot_token, reconnect=True)
