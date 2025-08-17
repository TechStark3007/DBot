import discord
import json
import os
import asyncio
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime
from dotenv import load_dotenv
from insta_post_scrapper import fetch_image_links  
from permissions import role_only

load_dotenv()
guild_id = int(os.getenv('DISCORD_GUILD_ID'))

INSTAPOST_JSON = "instapost.json"
INSTA_POSTS_FOLDER = "insta_posts"

class InstaPost(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_new_posts.start()  # Start the loop on bot initialization

    # Helper function to load data from JSON
    def load_instapost_data(self):
        try:
            with open(INSTAPOST_JSON, "r") as f:
                data = json.load(f)

                # Check and initialize 'instagram' and 'posts' if not present
                if "instagram" not in data:
                    data["instagram"] = {"posts": {}}
                if "posts" not in data["instagram"]:
                    data["instagram"]["posts"] = {}

                return data
        except FileNotFoundError:
            print("Data file not found. Initializing new data structure.")
            return {"instagram": {"posts": {}}}
        except json.JSONDecodeError:
            print("Error decoding JSON. Initializing new data structure.")
            return {"instagram": {"posts": {}}}

    # Helper function to save data to JSON
    def save_instapost_data(self, data):
        with open(INSTAPOST_JSON, "w") as f:
            json.dump(data, f, indent=4)

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{self.bot.user.name} is ready and InstaPost checking loop is running.")

    # Register /instapost command
    @app_commands.command(name="instapost", description="Register a custom Instagram post to monitor")
    @app_commands.describe(custom_name="Custom name for the Instagram post", username="Instagram username", channel="Channel to post in")
    @role_only("Owner")   # Apply the role check
    @app_commands.guilds(discord.Object(id=guild_id))
    async def instapost(self, interaction: discord.Interaction, custom_name: str, username: str, channel: discord.TextChannel):
        # Log the instapost data
        data = self.load_instapost_data()
        data["instagram"]["posts"][custom_name] = {
            "username": username,
            "channel_id": str(channel.id),
            "post_id": None,
            "last_updated": None
        }
        self.save_instapost_data(data)
        await interaction.response.send_message(f"Registered Instagram user '{username}' for tracking in channel {channel.mention}.", ephemeral=True)

    # Function to send media (images and videos) from the 'insta_posts' folder to Discord
    async def send_media_from_folder(self, channel):
        if not os.path.exists(INSTA_POSTS_FOLDER):
            print(f"Folder '{INSTA_POSTS_FOLDER}' does not exist. Skipping media posting.")
            return

        # Iterate over files in the folder and send each image or video
        for filename in os.listdir(INSTA_POSTS_FOLDER):
            file_path = os.path.join(INSTA_POSTS_FOLDER, filename)
            if os.path.isfile(file_path):
                try:
                    with open(file_path, "rb") as media_file:
                        # Check if the file is an image or a video based on its extension
                        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                            try:
                                response = await channel.send(file=discord.File(media_file, filename))
                                rate_limit_headers = response.headers  # Access rate limit headers
                                remaining = int(rate_limit_headers.get("X-RateLimit-Remaining", 1))
                                reset_after = float(rate_limit_headers.get("X-RateLimit-Reset-After", 0))

                                if remaining <= 0:
                                    print(f"Rate limit hit. Sleeping for {reset_after} seconds.")
                                    await asyncio.sleep(reset_after)
                            except discord.HTTPException as e:
                                if e.status == 429:  # Rate limit hit
                                    reset_after = float(e.response.headers.get("Retry-After", 1))
                                    print(f"Global rate limit reached. Sleeping for {reset_after} seconds.")
                                    await asyncio.sleep(reset_after)
                                else:
                                    print(f"Error sending image '{filename}': {e}")

                            print(f"Sent image '{filename}' to channel.")
                        elif filename.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):  # Check for video files
                            try:
                                response = await channel.send(file=discord.File(media_file, filename))
                                rate_limit_headers = response.headers
                                remaining = int(rate_limit_headers.get("X-RateLimit-Remaining", 1))
                                reset_after = float(rate_limit_headers.get("X-RateLimit-Reset-After", 0))

                                if remaining <= 0:
                                    print(f"Rate limit hit. Sleeping for {reset_after} seconds.")
                                    await asyncio.sleep(reset_after)
                            except discord.HTTPException as e:
                                if e.status == 429:  # Rate limit hit
                                    reset_after = float(e.response.headers.get("Retry-After", 1))
                                    print(f"Global rate limit reached. Sleeping for {reset_after} seconds.")
                                    await asyncio.sleep(reset_after)
                                else:
                                    print(f"Error sending video '{filename}': {e}")

                            print(f"Sent video '{filename}' to channel.")
                except Exception as e:
                    print(f"Error handling media '{filename}': {e}")

        # Delete all files in the folder after sending
        for filename in os.listdir(INSTA_POSTS_FOLDER):
            file_path = os.path.join(INSTA_POSTS_FOLDER, filename)
            try:
                os.remove(file_path)
                print(f"Deleted media '{filename}' from '{INSTA_POSTS_FOLDER}'.")
            except Exception as e:
                print(f"Error deleting media '{filename}': {e}")


    # Test a registered Instagram post
    @app_commands.command(name="test_instapost", description="Test and fetch images for the registered Instagram post")
    @app_commands.describe(name="Custom name for the Instagram post")
    @role_only("Owner")   # Apply the role check 
    @app_commands.guilds(discord.Object(id=guild_id))
    async def test_instapost(self, interaction: discord.Interaction, name: str):
        data = self.load_instapost_data()

        if name not in data["instagram"]["posts"]:
            await interaction.response.send_message(f"No Instagram post registered with the name '{name}'.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        post_data = data["instagram"]["posts"][name]
        username = post_data["username"]
        channel_id = post_data["channel_id"]
        channel = interaction.guild.get_channel(int(channel_id))

        if channel is None:
            await interaction.followup.send(f"Could not find the channel with ID '{channel_id}'.", ephemeral=True)
            return

        try:
            # Fetch the latest post and update JSON
            # Call fetch_image_links() to get latest_post_id and post_timestamp
            latest_post_id, post_timestamp = fetch_image_links(username, post_data)

            # Check if there is a new post
            if latest_post_id == post_data["post_id"]:
                await interaction.followup.send(f"No new post found for '{username}'.", ephemeral=True)
                return

            # Update the post_id and last_updated in the JSON data
            post_data["post_id"] = str(latest_post_id)
            post_data["last_updated"] = post_timestamp
            self.save_instapost_data(data)

            # Send the images from the 'insta_posts' folder 
            await self.send_media_from_folder(channel)

            await interaction.followup.send(f"Images from the latest post of '{username}' have been posted in {channel.mention}.", ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"Error fetching post for '{username}': {e}", ephemeral=True)

  # Delete a registered Instagram post
    @app_commands.command(name="delete_instapost", description="Delete a registered Instagram post")
    @app_commands.describe(name="Custom name for the Instagram post")
    @role_only("Owner")   # Apply the role check  
    @app_commands.guilds(discord.Object(id=guild_id))
    async def delete_instapost(self, interaction: discord.Interaction, name: str):
        data = self.load_instapost_data()

        if name not in data["instagram"]["posts"]:
            await interaction.response.send_message(f"No Instagram post registered with the name '{name}'.", ephemeral=True)
            return

        del data["instagram"]["posts"][name]
        self.save_instapost_data(data)

        await interaction.response.send_message(f"Removed Instagram post tracking for '{name}'.", ephemeral=True)

    # @commands.Cog.listener()
    # async def on_app_command_error(self, interaction: discord.Interaction, error: Exception):
    #     await handle_command_error(interaction, error)  # Call the error handling function        


    # Background loop to check for new posts every 210 minute
    @tasks.loop(minutes=210)
    async def check_new_posts(self):
        data = self.load_instapost_data()

        if not data["instagram"]["posts"]:
            print("No Instagram posts registered for checking.")
            return

        for custom_name, post_info in data["instagram"]["posts"].items():
            username = post_info["username"]
            channel_id = post_info["channel_id"]
            last_post_id = post_info["post_id"]

            # Fetch the Discord channel
            channel = self.bot.get_channel(int(channel_id))
            if channel is None:
                print(f"Channel ID {channel_id} not found. Skipping...")
                continue

            # Fetch the latest post from Instagram
            try:
                latest_post_id, post_timestamp = fetch_image_links(username, post_info)

                # Convert both post IDs to strings to ensure consistency
                last_post_id_str = str(last_post_id) if last_post_id is not None else None
                latest_post_id_str = str(latest_post_id)

                # Debugging information
                print(f"Username: {username}, Last Post ID: {last_post_id_str}, Latest Post ID: {latest_post_id_str}")

                # Check if the latest post is different from the last posted one
                if last_post_id_str is None or latest_post_id_str != last_post_id_str:
                    # New post detected, send images from the 'insta_posts' folder
                    await self.send_media_from_folder(channel)

                    # Update the JSON with the latest post ID and timestamp
                    post_info["post_id"] = latest_post_id_str
                    post_info["last_updated"] = post_timestamp
                    self.save_instapost_data(data)

                    print(f"New post detected for {username}. Images have been posted in {channel.name}.")
                else:
                    print(f"No new post for {username}. Last Post ID remains the same.")

            except Exception as e:
                print(f"Error fetching posts for '{username}': {e}")

        # Save updated data
        self.save_instapost_data(data)

# Register the commands in the command tree
async def setup(bot: commands.Bot):
    await bot.add_cog(InstaPost(bot))
