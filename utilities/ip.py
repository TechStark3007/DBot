import discord
from discord import app_commands
from discord.ext import commands
import requests
import os 
from dotenv import load_dotenv

load_dotenv()
guild_id = int(os.getenv('DISCORD_GUILD_ID'))


class IPCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @app_commands.command(name="ipsearch", description="Get geolocation info for a specific IP address.")
    @app_commands.describe(ip="The IP address to lookup.")
    @app_commands.guilds(discord.Object(id=guild_id))
    async def ip(self, interaction: discord.Interaction, ip: str):
        # Get geolocation info for the provided IP
        geo_response = requests.get(f"https://ipinfo.io/{ip}/geo").json()
        embed = discord.Embed(title=f"Geolocation for IP: {ip}", color=discord.Color.blue())
        embed.add_field(name="City", value=geo_response.get("city", "N/A"), inline=True)
        embed.add_field(name="Region", value=geo_response.get("region", "N/A"), inline=True)
        embed.add_field(name="Country", value=geo_response.get("country", "N/A"), inline=True)
        embed.add_field(name="Location", value=geo_response.get("loc", "N/A"), inline=True)
        embed.add_field(name="Organization", value=geo_response.get("org", "N/A"), inline=True)
        embed.add_field(name="Postal Code", value=geo_response.get("postal", "N/A"), inline=True)
        embed.add_field(name="Timezone", value=geo_response.get("timezone", "N/A"), inline=True)

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(IPCommands(bot))
