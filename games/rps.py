import discord
from discord.ext import commands
from discord import app_commands
import os
import random
from dotenv import load_dotenv
from games.game_module import UserManager, GameManager
from games.errors import UserBalanceHelper

load_dotenv()
guild_id = int(os.getenv('DISCORD_GUILD_ID'))

game_name = 'rps'
entry_fee = GameManager.get_entry_fee(game_name)
win_payout = GameManager.get_win_payout(game_name)

class RockPaperScissor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="rps", description="Play a game of Rock, Paper, Scissors with the bot")
    @app_commands.describe(choice="Your choice: rock, paper, or scissor (case-insensitive)")
    @app_commands.guilds(discord.Object(id=guild_id))
    async def rps(self, interaction: discord.Interaction, choice: str):
        await interaction.response.defer()  
        
        # Fetch the user id
        user_id = interaction.user.id
        # try:
        #     user_balance = UserManager.get_user_balance(user_id)
        # except Exception as e:
        #     print(e)
        #     await interaction.followup.send("An error occurred while fetching your balance. Please try again later.", ephemeral=True)
        #     return

        # # Check if the user has sufficient balance
        # if user_balance < entry_fee:
        #     await interaction.followup.send(f"Insufficient balance to play. You need at least {entry_fee} coins.", ephemeral=True)
        #     return
        if not await UserBalanceHelper.validate_balance(
            interaction, 
            user_id = user_id, 
            entry_fee= entry_fee,
            single_player=True
            ):
            return

        # Validate the user's choice
        choice = choice.lower()
        if choice not in ["rock", "paper", "scissor"]:
            await interaction.followup.send("Invalid choice! Please choose `rock`, `paper`, or `scissor` (case-insensitive).", ephemeral=True)
            return

        # Bot's choice
        bot_choice = random.choice(["rock", "paper", "scissor"])
        payout = 0

        # Determine the winner
        if choice == bot_choice:
            result = "It's a tie!"
        elif (choice == "rock" and bot_choice == "scissor") or \
             (choice == "paper" and bot_choice == "rock") or \
             (choice == "scissor" and bot_choice == "paper"):
            result = f"You won **{win_payout} coins**!"
            payout = win_payout - entry_fee
        else:
            result = f"You lost **{entry_fee} coins**!"
            payout = -entry_fee


        try:
            UserManager.update_user_balance(user_id, payout) 
        except Exception as e:
            print(e)
            await interaction.followup.send("An error occurred while updating your balance. Please contact an administrator.", ephemeral=True)
            return



        # Send the result
        await interaction.followup.send(
            f"**Rock, Paper, Scissors**\n\n"
            f"You chose: {choice}\n"
            f"Bot chose: {bot_choice}\n\n"
            f"**Result:** {result}", 
            ephemeral=False
        )

async def setup(bot):
    await bot.add_cog(RockPaperScissor(bot))