import discord
from discord.ext import commands

# Cooldown system mapped to user ID
cooldown_mapping = commands.CooldownMapping.from_cooldown(1, 1, lambda i: i.user.id)

async def check_cooldown(interaction: discord.Interaction, cooldown_time: int):
    # Roles that bypass cooldown
    exempt_roles = {"Owner", "Admin", "Moderator"}  # add as many as you like 😘

    user_roles = {role.name for role in interaction.user.roles}  # set for faster lookup
    if exempt_roles & user_roles:  # check if there's any overlap
        return False  # No cooldown for exempt roles

    """Checks if a user is on cooldown."""
    bucket = cooldown_mapping.get_bucket(interaction)
    bucket.per = cooldown_time
    retry_after = bucket.update_rate_limit()
    if retry_after:
        minutes, seconds = divmod(int(retry_after), 60)
        await interaction.response.send_message(
            f"You're on cooldown! Try again in {minutes}m {seconds}s.", ephemeral=True
        )
        return True
    return False
