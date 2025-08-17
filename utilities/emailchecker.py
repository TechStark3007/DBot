import discord
from discord import app_commands
from discord.ext import commands
import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
guild_id = int(os.getenv('DISCORD_GUILD_ID'))

class EmailChecker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="emailchecker", description="Check if an email address is valid.")
    @app_commands.guilds(discord.Object(id=guild_id))
    async def emailchecker(self, interaction: discord.Interaction, email: str):
        # Defer the response to avoid timeout
        await interaction.response.defer()

        url = "https://email-validator28.p.rapidapi.com/email-validator/validate"
        querystring = {"email": email}

        headers = {
            "x-rapidapi-key": "ca6fbf8d52mshe1a4b1a3121027ap175b24jsne9d01fa31fa4",
            "x-rapidapi-host": "email-validator28.p.rapidapi.com"
        }

        # Send the request to the email validation API
        response = requests.get(url, headers=headers, params=querystring)
        result = response.json()

        #print(response.json())
        #print(f"Response status: {response.status_code}")
        #print(f"Response text: {response.text}")

        if response.status_code == 200:
            # Get the validation results from the API response
            is_disposable = result.get("isDisposable", False)
            is_valid = result.get("isValid", False)
            is_deliverable = result.get("isDeliverable", False)

            # Create an embed message
            embed = discord.Embed(title="Email Validation Result", color=discord.Color.blue())

            # Set the text for each field with check or cross mark
            disposable_text = "✅ Disposable" if is_disposable else "❌ Disposable"
            valid_text = "✅ Valid" if is_valid else "❌ Valid"
            deliverable_text = "✅ Deliverable" if is_deliverable else "❌ Deliverable"

            # Add fields to the embed
            embed.add_field(name=disposable_text, value="\u200b", inline=False)  # Using zero-width space for empty value
            embed.add_field(name=valid_text, value="\u200b", inline=False)
            embed.add_field(name=deliverable_text, value="\u200b", inline=False)

            await interaction.followup.send(embed=embed)
        else:
            # In case of failure, show the error
            await interaction.followup.send(f"Failed to validate email. Status code: {response.status_code}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(EmailChecker(bot))
