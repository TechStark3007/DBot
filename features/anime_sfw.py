import discord
from discord import app_commands
from discord.ext import commands
import requests
import os
from dotenv import load_dotenv

load_dotenv()
guild_id = int(os.getenv('DISCORD_GUILD_ID'))

class AnimeSFW(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="anime", description="Get a random anime image.")
    @app_commands.guilds(discord.Object(id=guild_id))
    async def anime(self, interaction: discord.Interaction):
        # Fetch image from the API
        resp = requests.get("https://nekos.best/api/v2/neko")
        data = resp.json()
        image_url = data["results"][0]["url"]

        # Create an embed with the image
        embed = discord.Embed(title="Here's a cute anime image for you!", color=discord.Color.purple())
        embed.set_image(url=image_url)

        # Send the embed in response
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(AnimeSFW(bot))
