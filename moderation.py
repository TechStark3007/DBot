import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv
from datetime import timedelta
from permissions import role_only

load_dotenv()
guild_id = int(os.getenv('DISCORD_GUILD_ID'))

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="mute", description="Mute a member for a specified time with a reason")
    @app_commands.describe(member="The member to mute", time="The duration of the mute (e.g., 10m, 1h)", reason="The reason for the mute")
    @role_only("Owner", "Admin", "Moderator")
    @app_commands.guilds(discord.Object(id=guild_id))
    async def mute(self, interaction: discord.Interaction, member: discord.Member, time: str, reason: str):
        # Convert time to seconds
        time_dict = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        duration = int(time[:-1]) * time_dict[time[-1]]

        # Mute the member
        await member.timeout(timedelta(seconds=duration), reason=reason)
        await interaction.response.send_message(f"{member.mention} has been muted for {time}. Reason: {reason}")

        # Send a private message to the member
        try:
            await member.send(f"You have been muted for {time}. Reason: {reason}")
        except discord.Forbidden:
            await interaction.followup.send("Could not send a DM to the member.")

    @app_commands.command(name="unmute", description="Unmute a member")
    @app_commands.describe(member="The member to unmute")
    @role_only("Owner", "Admin", "Moderator")  # Apply the role check
    @app_commands.guilds(discord.Object(id=guild_id))
    async def unmute(self, interaction: discord.Interaction, member: discord.Member):
        # Unmute the member
        await member.timeout(None)
        await interaction.response.send_message(f"{member.mention} has been unmuted.")

        # Send a private message to the member
        try:
            await member.send("You have been unmuted.")
        except discord.Forbidden:
            await interaction.followup.send("Could not send a DM to the member.")

    @app_commands.command(name="kick", description="Kick a member with a reason")
    @app_commands.describe(member="The member to kick", reason="The reason for the kick")
    @role_only("Owner", "Admin")  # Apply the role check
    @app_commands.guilds(discord.Object(id=guild_id))
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        # Kick the member
        await member.kick(reason=reason)
        await interaction.response.send_message(f"{member.mention} has been kicked. Reason: {reason}")

        # Send a private message to the member
        try:
            await member.send(f"You have been kicked from the server. Reason: {reason}")
        except discord.Forbidden:
            await interaction.followup.send("Could not send a DM to the member.")

    @app_commands.command(name="ban", description="Ban a member with a reason")
    @app_commands.describe(member="The member to ban", reason="The reason for the ban")
    @role_only("Owner", "Admin")  # Apply the role check
    @app_commands.guilds(discord.Object(id=guild_id))
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        # Ban the member
        await member.ban(reason=reason)
        await interaction.response.send_message(f"{member.mention} has been banned. Reason: {reason}")

        # Send a private message to the member
        try:
            await member.send(f"You have been banned from the server. Reason: {reason}")
        except discord.Forbidden:
            await interaction.followup.send("Could not send a DM to the member.")

    @app_commands.command(name="unban", description="Unban a member")
    @app_commands.describe(user_id="The ID of the user to unban", reason="The reason for the unban")
    @role_only("Owner", "Admin")  # Apply the role check
    @app_commands.guilds(discord.Object(id=guild_id))
    async def unban(self, interaction: discord.Interaction, user_id: str, reason: str):
        # Fetch the banned users
        banned_users = await interaction.guild.bans()
        user_id = int(user_id)

        # Find the user in the banned list
        for ban_entry in banned_users:
            user = ban_entry.user
            if user.id == user_id:
                # Unban the user
                await interaction.guild.unban(user, reason=reason)
                await interaction.response.send_message(f"{user.name}#{user.discriminator} has been unbanned. Reason: {reason}")
                return

        # If the user is not found in the banned list
        await interaction.response.send_message(f"User with ID {user_id} is not banned.")

async def setup(bot):
    await bot.add_cog(Moderation(bot))