import discord
from discord import app_commands
from discord.ext import commands
from google import genai
import os
from utilities.cooldown import check_cooldown
from dotenv import load_dotenv

load_dotenv()
guild_id = int(os.getenv("DISCORD_GUILD_ID"))

# Initialize Gemini API Client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
cooldown_time = 300 # 5 mins

class Gemini(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ai", description="Ask AI a question.")
    @app_commands.guilds(discord.Object(id=guild_id))
    async def askai(self, interaction: discord.Interaction, prompt: str):
        if await check_cooldown(interaction, cooldown_time):
            return  # Stop execution if user is on cooldown

        await interaction.response.defer()

        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=prompt
            )
            ai_response = response.text
        except Exception as e:
            ai_response = f"Error: {e}"

        await interaction.followup.send(ai_response)

async def setup(bot):
    await bot.add_cog(Gemini(bot))
