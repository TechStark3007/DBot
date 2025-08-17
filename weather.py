import discord
from discord import app_commands
from discord.ext import commands
import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
API_KEY = os.getenv('OPENWEATHER_API_KEY')
guild_id = int(os.getenv('DISCORD_GUILD_ID'))

class Weather(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="weather", description="Get the current weather for a city.")
    @app_commands.describe(city="The name of the city to get the weather for.")
    @app_commands.guilds(discord.Object(id=guild_id))
    async def weather(self, interaction: discord.Interaction, city: str):
        # OpenWeatherMap API endpoint
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"

        # Make the API request
        response = requests.get(url)
        data = response.json()

        if response.status_code == 200:
            # Extract relevant information from the response
            city_name = data['name']
            country = data['sys']['country']
            temperature = data['main']['temp']
            feels_like = data['main']['feels_like']
            temp_min = data['main']['temp_min']
            temp_max = data['main']['temp_max']
            pressure = data['main']['pressure']
            humidity = data['main']['humidity']
            weather_description = data['weather'][0]['description']
            wind_speed = data['wind']['speed']
            wind_deg = data['wind']['deg']
            visibility = data['visibility']
            cloud_cover = data['clouds']['all']
            sunrise = data['sys']['sunrise']
            sunset = data['sys']['sunset']
            timezone = data['timezone']

            # Create an embed message to send the weather information
            embed = discord.Embed(title=f"Weather in {city_name}, {country}", color=discord.Color.blue())
            embed.add_field(name="Temperature", value=f"{temperature} °C", inline=True)
            embed.add_field(name="Feels Like", value=f"{feels_like} °C", inline=True)
            embed.add_field(name="Min Temperature", value=f"{temp_min} °C", inline=True)
            embed.add_field(name="Max Temperature", value=f"{temp_max} °C", inline=True)
            embed.add_field(name="Pressure", value=f"{pressure} hPa", inline=True)
            embed.add_field(name="Humidity", value=f"{humidity}%", inline=True)
            embed.add_field(name="Wind Speed", value=f"{wind_speed} m/s", inline=True)
            embed.add_field(name="Wind Direction", value=f"{wind_deg}°", inline=True)
            embed.add_field(name="Visibility", value=f"{visibility} m", inline=True)
            embed.add_field(name="Cloud Cover", value=f"{cloud_cover}%", inline=True)
            embed.add_field(name="Sunrise", value=f"<t:{sunrise}:t>", inline=True)  # Discord timestamp format
            embed.add_field(name="Sunset", value=f"<t:{sunset}:t>", inline=True)    # Discord timestamp format
            embed.add_field(name="Timezone", value=f"{timezone // 3600} hours from UTC", inline=True)

            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("Sorry, I couldn't find that city. Please check the name and try again.")

async def setup(bot):
    await bot.add_cog(Weather(bot))
