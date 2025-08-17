import discord
from discord import app_commands
from discord.ext import commands
import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
guild_id = int(os.getenv('DISCORD_GUILD_ID'))

class AnimeGIF(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="animegif", description="Get an anime GIF (e.g., hug, kiss, pat)")
    @app_commands.describe(gif_name="The name of the GIF category (e.g., hug, kiss, pat)")
    @app_commands.guilds(discord.Object(id=guild_id))
    async def animegif(self, interaction: discord.Interaction, gif_name: str):
        # List of NSFW GIF categories
        nsfw_gifs = [
            "anal", "blowjob", "cum", "fuck", "neko", "pussylick", "solo",
            "solo_male", "threesome_fff", "threesome_ffm", "threesome_mmf",
            "yaoi", "yuri"
        ]
        
        # Determine the correct endpoint based on the GIF category
        if gif_name in nsfw_gifs:
            response = requests.get(f"https://purrbot.site/api/img/nsfw/{gif_name}/gif")
        else:
            response = requests.get(f"https://purrbot.site/api/img/sfw/{gif_name}/gif")

        # Debug: print the response text
        print(f"Response text: {response.text}")

        try:
            data = response.json()
            if not data['error']:  # Check for error = false
                gif_url = data['link']
                await interaction.response.send_message(gif_url)
            else:
                await interaction.response.send_message("Sorry, I couldn't find that GIF.")
        except ValueError:
            await interaction.response.send_message("Received an invalid response from the API.")

    @app_commands.command(name="animegif_help", description="List all available GIF names.")
    @app_commands.guilds(discord.Object(id=guild_id))  # Use the guild ID from the environment variable
    async def animegif_help(self, interaction: discord.Interaction):
        # List of available GIF names
        available_gifs = [
            "angry", "background", "bite", "blush", "comfy", "cry", "cuddle",
            "dance", "eevee", "fluff", "holo", "hug", "icon", "kiss", "kitsune",
            "lay", "lick", "neko", "okami", "pat", "poke", "pout", "senko",
            "shiro", "slap", "smile", "tail", "tickle",
            # NSFW GIFs
            "anal", "blowjob", "cum", "fuck", "neko", "pussylick", "solo",
            "solo_male", "threesome_fff", "threesome_ffm", "threesome_mmf",
            "yaoi", "yuri"
        ]
        help_message = "Available GIF names:\n" + "\n".join(available_gifs)
        await interaction.response.send_message(help_message)

async def setup(bot):
    await bot.add_cog(AnimeGIF(bot))
