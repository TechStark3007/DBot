import discord
import os
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from permissions import role_only

load_dotenv()
guild_id = int(os.getenv('DISCORD_GUILD_ID'))

class Announcement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="announce", description="Announce a message to a specific channel with role ping")
    @app_commands.describe(
        message="The message you want to announce (supports role pings)",
        channel="The channel where the announcement will be posted"
    )
    @role_only("Owner")   # Apply the role check  
    @app_commands.guilds(discord.Object(id=guild_id))
    async def announce(self, interaction: discord.Interaction, message: str, channel: discord.TextChannel):
        try:
            # Use the channel's ID directly for clarity
            await channel.send(message)
            await interaction.response.send_message(f"Announcement posted successfully in {channel.mention}!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Failed to post the announcement: {e}", ephemeral=True)

# Function to add the cog
async def setup(bot):
    await bot.add_cog(Announcement(bot))