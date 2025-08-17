import discord
import random
import json
import os
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from emoji import lovely_reaction_emojis  # Ensure you have your emoji.py with the list
from permissions import role_only # Import the new functions

load_dotenv()
guild_id = int(os.getenv('DISCORD_GUILD_ID'))

channel_json_path = 'data/channels.json'

# Load command preferences from a JSON file
def load_command_preferences():
    PREFERENCES_FILE = channel_json_path
    if os.path.exists(PREFERENCES_FILE):
        with open(PREFERENCES_FILE, "r") as f:
            try:
                preferences = json.load(f)
                return preferences.get("auto_react_channels", {})
            except json.JSONDecodeError:
                print("JSON file is invalid or empty. Initializing with default values.")
                return {}
    return {}

# Save command preferences to a JSON file
def save_command_preferences(auto_react_channels):
    PREFERENCES_FILE = channel_json_path
    preferences = load_command_preferences()
    preferences["auto_react_channels"] = auto_react_channels

    with open(PREFERENCES_FILE, "w") as f:
        json.dump(preferences, f)

class AutoReactCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.auto_react_channels = load_command_preferences()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        # Check if auto-react is enabled for the current channel
        if str(message.channel.id) in self.bot.auto_react_channels:
            try:
                emoji_to_add = random.choice(lovely_reaction_emojis)
                await message.add_reaction(emoji_to_add)
            except discord.HTTPException:
                pass

    @app_commands.command(name="autoreact", description="Enable or disable auto-reaction in a channel.")
    @app_commands.describe(state="Enable or disable autoreact", channel="The channel to apply autoreact")
    @app_commands.guilds(discord.Object(id=guild_id))
    @role_only("Owner")  # Apply the role check
    async def autoreact(self, interaction: discord.Interaction, state: bool, channel: discord.TextChannel):
        channel_id = str(channel.id)
        if state:
            if channel_id not in self.bot.auto_react_channels:
                self.bot.auto_react_channels[channel_id] = True
                save_command_preferences(self.bot.auto_react_channels)
                await interaction.response.send_message(f"Auto-react enabled for {channel.mention}")
                print(f"Auto-react enabled for {channel_id}")
            else:
                await interaction.response.send_message(f"Auto-react is already enabled for {channel.mention}")
        else:
            if channel_id in self.bot.auto_react_channels:
                self.bot.auto_react_channels.pop(channel_id)
                save_command_preferences(self.bot.auto_react_channels)
                await interaction.response.send_message(f"Auto-react disabled for {channel.mention}")
                print(f"Auto-react disabled for {channel_id}")
            else:
                await interaction.response.send_message(f"Auto-react is not enabled for {channel.mention}")

    # @commands.Cog.listener()
    # async def on_app_command_error(self, interaction: discord.Interaction, error: Exception):
    #     await handle_command_error(interaction, error)  # Call the error handling function

async def setup_autoreact(bot):
    await bot.add_cog(AutoReactCog(bot))
    await sync_commands(bot)  # Call sync_commands directly after adding the cog

async def sync_commands(bot):
    await bot.wait_until_ready()
    await bot.tree.sync(guild=None)  # Sync commands for the guild
    print("Slash commands synced.")

# Define the setup function
async def setup(bot):
    await setup_autoreact(bot)
