import discord
from discord import app_commands
from discord.ext import commands
import requests
import os
import random
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
guild_id = int(os.getenv('DISCORD_GUILD_ID'))

class Giphy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="giphy", description="Search for a GIF.")
    @app_commands.describe(search="The search term for the GIF.")
    @app_commands.guilds(discord.Object(id=guild_id))
    async def giphy(self, interaction: discord.Interaction, search: str):
        # Use the Giphy API to search for a GIF
        api_key = os.getenv('GIPHY_API_KEY')  # Make sure to set your Giphy API key in the .env file
        
        # Randomize the offset to get different results for the same search
        response = requests.get(f"https://api.giphy.com/v1/gifs/search?api_key={api_key}&q={search}&limit=1&offset={random.randint(0, 50)}")

        # Debug: print the response text
        #print(f"Response text: {response.text}")

        try:
            data = response.json()
            gif_url = data['data'][0]['images']['original']['url']  # Get the original GIF URL

            # Remove unnecessary query parameters after giphy.gif
            if 'giphy.gif' in gif_url:
                gif_url = gif_url.split('?')[0]  # Keep only the part before the '?'

            await interaction.response.send_message(gif_url)
        except (IndexError, KeyError):
            await interaction.response.send_message("Sorry, I couldn't find a GIF for that search term.")
        except ValueError:
            await interaction.response.send_message("Received an invalid response from the API.")

async def setup(bot):
    await bot.add_cog(Giphy(bot))
