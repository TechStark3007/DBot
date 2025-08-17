import discord
from discord.ext import commands, tasks
from discord import app_commands
import requests  # For checking Instagram usernames
from instascrapper import InstaScrapper  # Import the class
from datetime import datetime
import os
import json
import asyncio  # Import asyncio
from dotenv import load_dotenv
from permissions import role_only

load_dotenv()
guild_id = int(os.getenv('DISCORD_GUILD_ID'))

# File to store RSS feeds
RSS_FILE = 'rss.json'


def load_rss_feeds():
    try:
        with open(RSS_FILE, 'r') as file:
            rss_feeds = json.load(file)
            # Ensure the 'instagram' structure is present
            if 'instagram' not in rss_feeds:
                rss_feeds['instagram'] = {'feeds': {}}
            return rss_feeds
    except FileNotFoundError:
        # Return a default structure if the file is not found
        return {'instagram': {'feeds': {}}}
    except json.JSONDecodeError:
        # Handle case where the file is corrupted or unreadable
        return {'instagram': {'feeds': {}}}


def save_rss_feeds(rss_feeds):
    with open(RSS_FILE, 'w') as file:
        json.dump(rss_feeds, file, indent=4)

class RSS(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.scraper_loop.start()  # Start the scraper loop on cog initialization

    @app_commands.command(name="instarss", description="Create a new Instagram RSS feed.")
    @app_commands.describe(name="The name of the RSS feed", username="The Instagram username", channel="The channel to post in")
    @role_only("Owner")   # Apply the role check    
    @app_commands.guilds(discord.Object(id=guild_id))  # Replace with your guild ID
    async def create_instagram_rss(self, interaction: discord.Interaction, name: str, username: str, channel: discord.TextChannel):
        # Defer the response to allow time for processing
        await interaction.response.defer()

        rss_feeds = load_rss_feeds()

        if "instagram" not in rss_feeds:
            rss_feeds["instagram"] = {"feeds": {}}

        rss_feeds["instagram"]["feeds"][name] = {
            'username': username,
            'channel_id': str(channel.id),
            'post_id': None,
            'last_updated': None
        }

        save_rss_feeds(rss_feeds)

        instascrapper = InstaScrapper()
        post_data = instascrapper.fetch_last_post(username)

        if post_data:
            rss_post = instascrapper.format_post_as_rss(post_data)
            now = datetime.now()
            rss_feeds["instagram"]["feeds"][name]['post_id'] = post_data['post_id']
            rss_feeds["instagram"]["feeds"][name]['last_updated'] = now.isoformat()

            save_rss_feeds(rss_feeds)
            await self.send_instagram_post_embed(channel, rss_post)
            # Send final message after processing
            await interaction.followup.send(f"Instagram RSS feed '{name}' created and last post fetched successfully.")
        else:
            # Send an ephemeral message for failure
            await interaction.followup.send(f"Could not fetch the last post for {username}.", ephemeral=True)


    @tasks.loop(minutes=30)  # Run every 2 minutes
    async def scraper_loop(self):
        scrapper = InstaScrapper()
        rss_feeds = load_rss_feeds()
        
        # Ensure 'instagram' key exists
        if 'instagram' not in rss_feeds:
            rss_feeds['instagram'] = {'feeds': {}}

        # Loop through feeds and process them
        for feed_name, feed_info in rss_feeds['instagram']['feeds'].items():
            username = feed_info['username']
            channel_id = int(feed_info['channel_id'])
            channel = self.bot.get_channel(channel_id)
            
            post_data = scrapper.fetch_last_post(username)
            if post_data and (feed_info['post_id'] is None or post_data['post_id'] != feed_info['post_id']):
                feed_info['post_id'] = post_data['post_id']
                feed_info['last_updated'] = datetime.now().isoformat()
                save_rss_feeds(rss_feeds)
                rss_post = scrapper.format_post_as_rss(post_data)
                await self.send_instagram_post_embed(channel, rss_post)

    async def send_instagram_post_embed(self, channel, post_data):
        embed = discord.Embed(description=post_data['description'], color=0xffa500)
        title = post_data['title'][:253] + "..." if len(post_data['title']) > 256 else post_data['title']
        embed.title = title
        embed.add_field(name="Link", value=f"[View Post]({post_data['link']})", inline=False)
        embed.set_image(url=post_data['link'])
        embed.set_footer(text=f"Posted on: {post_data['pub_date']}")
        await channel.send(embed=embed)

    @app_commands.command(name="test", description="Test an existing Instagram RSS feed.")
    @app_commands.describe(name="The name of the RSS feed to test")
    @role_only("Owner")   # Apply the role check    
    @app_commands.guilds(discord.Object(id=guild_id))  # Replace with your guild ID
    async def test_instagram_rss(self, interaction: discord.Interaction, name: str):
        """Test an existing Instagram RSS feed to check if it works."""
        rss_feeds = load_rss_feeds()
        
        if "instagram" not in rss_feeds or name not in rss_feeds["instagram"]["feeds"]:
            await interaction.response.send_message(f"RSS feed '{name}' not found.", ephemeral=True)
            return

        username = rss_feeds["instagram"]["feeds"][name]['username']
        url = f"https://www.instagram.com/{username}/?__a=1"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                await interaction.response.send_message(f"Instagram RSS feed '{name}' is valid and accessible.")
            else:
                await interaction.response.send_message(f"Instagram RSS feed '{name}' is not valid. Status code: {response.status_code}", ephemeral=True)
        except requests.RequestException as e:
            await interaction.response.send_message(f"Error testing Instagram RSS feed '{name}': {str(e)}", ephemeral=True)

    @app_commands.command(name="delete", description="Delete an existing Instagram RSS feed.")
    @app_commands.describe(name="The name of the RSS feed to delete")
    @role_only("Owner")   # Apply the role check    
    @app_commands.guilds(discord.Object(id=guild_id))  # Replace with your guild ID
    async def delete_instagram_rss(self, interaction: discord.Interaction, name: str):
        """Delete an existing Instagram RSS feed."""
        rss_feeds = load_rss_feeds()
        
        if "instagram" in rss_feeds and name in rss_feeds["instagram"]["feeds"]:
            del rss_feeds["instagram"]["feeds"][name]
            save_rss_feeds(rss_feeds)  # Save updated feeds to JSON
            await interaction.response.send_message(f"Instagram RSS feed '{name}' deleted successfully.")
        else:
            await interaction.response.send_message(f"Instagram RSS feed '{name}' not found.", ephemeral=True)

    async def run_scraper(self):
        """Run the Instagram scraper in the background."""
        scrapper = InstaScrapper()
        while True:
            await scrapper.run_scraper()  # Call the method you defined in instascrapper.py
            await asyncio.sleep(60)  # Sleep for a minute before checking again (this can be adjusted)

    # @commands.Cog.listener()
    # async def on_app_command_error(self, interaction: discord.Interaction, error: Exception):
    #     await handle_command_error(interaction, error)  # Call the error handling function            

# Setup function to add the RSS cog to the bot
async def setup(bot):
    await bot.add_cog(RSS(bot))
