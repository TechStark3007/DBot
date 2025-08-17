import discord
from discord.ext import tasks
import json
import os
from dotenv import load_dotenv
from discord import app_commands
from discord.ext import commands
from permissions import role_only

load_dotenv()
guild_id = int(os.getenv('DISCORD_GUILD_ID'))

fact_storage_path = 'data/facts.json'
log_storage_path = 'data/log.json'
channel_storage_path = 'data/channels.json'

# Load facts from JSON
def load_facts():
    if os.path.exists(fact_storage_path):
        with open(fact_storage_path, "r", encoding='utf-8') as f:
            return json.load(f)
    return []

# Load sent facts from JSON
def load_sent_facts():
    if os.path.exists(log_storage_path):
        with open(log_storage_path, "r", encoding='utf-8') as f:
            try:
                preferences = json.load(f)
                return preferences.get("sent_facts", []), preferences.get("current_fact_index", 0)
            except json.JSONDecodeError:
                return [], 0
    return [], 0

# Save sent facts and the current fact index to JSON
def save_sent_facts(sent_facts, current_fact_index):
    with open(log_storage_path, "w", encoding='utf-8') as f:
        json.dump({"sent_facts": sent_facts, "current_fact_index": current_fact_index}, f)

# Clear sent facts log
def clear_sent_facts():
    with open(log_storage_path, "w", encoding='utf-8') as f:
        json.dump({"sent_facts": [], "current_fact_index": 0}, f)

# Load channels from JSON, preserving both fact and autoreact channels
def load_channels():
    if os.path.exists(channel_storage_path):
        with open(channel_storage_path, "r", encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {"fact_channels": [], "autoreact_channels": []}
    return {"fact_channels": [], "autoreact_channels": []}

# Save channels to JSON, preserving both fact and autoreact channels
def save_channels(channels_data):
    with open(channel_storage_path, "w", encoding='utf-8') as f:
        json.dump(channels_data, f, indent=4)

# Setup function for sending facts
async def setup_facts(bot):
    facts = load_facts()
    sent_facts, current_fact_index = load_sent_facts()
    channels_data = load_channels()  # Load the whole channels.json content
    bot.sent_facts = sent_facts
    bot.facts = facts
    bot.current_fact_index = current_fact_index  # Load current fact index
    bot.send_facts_channels = channels_data.get("fact_channels", [])  # Load only fact channels

    @tasks.loop(hours=24)
    async def send_daily_facts_task():
        await bot.wait_until_ready()  # Ensure bot is ready before executing

        if bot.current_fact_index < len(bot.facts):
            fact_of_the_day = bot.facts[bot.current_fact_index]  # Get the next fact
            bot.sent_facts.append(fact_of_the_day)  # Log this fact
            bot.current_fact_index += 1  # Move to the next fact index
            save_sent_facts(bot.sent_facts, bot.current_fact_index)  # Save sent facts and index

            # Format the message
            fact_title, fact_text = fact_of_the_day.split(": ", 1)
            fact_message = f"**{fact_title}**\n```{fact_text}```"

            for channel_id in bot.send_facts_channels:
                channel = bot.get_channel(int(channel_id))
                if channel:
                    try:
                        await channel.send(fact_message)
                        # Calculate and send the next fact timer (next fact will be sent in 24 hours)
                        await channel.send("Next fact will be sent in 24 hour(s).")
                    except Exception as e:
                        print(f"Failed to send message to {channel.mention}: {e}")

    @bot.tree.command(name='sendfacts', description='Enable or disable daily facts in the specified channel.')
    @app_commands.describe(state="Enable or disable daily facts", channel="The channel to send daily facts")
    @app_commands.guilds(discord.Object(id=guild_id))
    @role_only("Owner") 
    async def send_facts(interaction: discord.Interaction, state: bool, channel: discord.TextChannel):
        channels_data = load_channels()  # Reload channels data every time this is called
        channel_id = str(channel.id)
        if state:
            if channel_id not in bot.send_facts_channels:
                bot.send_facts_channels.append(channel_id)
                channels_data["fact_channels"] = bot.send_facts_channels  # Update fact channels
                save_channels(channels_data)  # Save the entire channels data
                await interaction.response.send_message(f"Daily facts will be sent to {channel.mention}.")

                # Send an immediate fact when enabling
                if bot.current_fact_index < len(bot.facts):
                    fact_of_the_day = bot.facts[bot.current_fact_index]

                    # Format the message
                    fact_title, fact_text = fact_of_the_day.split(": ", 1)
                    fact_message = f"**{fact_title}**\n```{fact_text}```"
                    await channel.send(fact_message)
                    bot.sent_facts.append(fact_of_the_day)
                    bot.current_fact_index += 1
                    save_sent_facts(bot.sent_facts, bot.current_fact_index)  # Save after sending immediate fact

                else:
                    await interaction.response.send_message("All facts have been sent. No more facts available.")

            else:
                await interaction.response.send_message(f"Daily facts are already set for {channel.mention}.")
        else:
            if channel_id in bot.send_facts_channels:
                bot.send_facts_channels.remove(channel_id)
                channels_data["fact_channels"] = bot.send_facts_channels  # Update fact channels
                save_channels(channels_data)  # Save the entire channels data
                await interaction.response.send_message(f"Daily facts have been disabled for {channel.mention}.")
            else:
                await interaction.response.send_message(f"Daily facts are not set for {channel.mention}.")

    @bot.tree.command(name='clear', description='Clear the sent chat log.')
    @app_commands.describe(channel="The channel to clear sent facts")
    @app_commands.guilds(discord.Object(id=guild_id))
    @role_only("Owner") 
    async def clear_sent_chat_log(interaction: discord.Interaction, channel: discord.TextChannel):
        clear_sent_facts()  # Clear the sent facts log
        await interaction.response.send_message("The sent chat log has been cleared.")

    # @commands.Cog.listener()
    # async def on_app_command_error(self, interaction: discord.Interaction, error: Exception):
    #     await handle_command_error(interaction, error)  # Call the error handling function    

    @bot.event
    async def on_ready():
        send_daily_facts_task.start()  # Start the task to send daily facts
