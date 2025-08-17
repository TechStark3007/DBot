import discord
from discord import app_commands
from discord.ext import commands
import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
guild_id = int(os.getenv('DISCORD_GUILD_ID'))

class NsfwImage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="nsfwimg", description="Get an NSFW image of a specific type.")
    @app_commands.describe(type="The type of NSFW image to retrieve.")
    @app_commands.guilds(discord.Object(id=guild_id))
    async def nsfwimg(self, interaction: discord.Interaction, type: str):
        # Defer the response to avoid timeout
        await interaction.response.defer()

        # Prepare the API request
        url = "https://nsfw-image-stock-api.p.rapidapi.com/"
        payload = {"type": type}
        headers = {
            "x-rapidapi-key": os.getenv('RAPIDAPI_KEY'),  # Use your API key from environment variables
            "x-rapidapi-host": "nsfw-image-stock-api.p.rapidapi.com",
            "Content-Type": "application/json"
        }

        # Send the request to the NSFW image API
        response = requests.post(url, json=payload, headers=headers)

        # Debug: print the response status and text
       
        print(response.json())
        print(f"Response status: {response.status_code}")
        print(f"Response text: {response.text}")

        if response.status_code == 200:
            data = response.json()
            image_url = data.get('url')  # Adjust based on the actual response structure
            
            # Debug: Check the image_url
            print(f"Image URL: {image_url}")

            if image_url:
                await interaction.followup.send(image_url)
            else:
                await interaction.followup.send("Failed to retrieve image URL from the response.", ephemeral=True)
        else:
            await interaction.followup.send(f"Failed to retrieve image. Status code: {response.status_code}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(NsfwImage(bot))
