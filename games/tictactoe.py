#DEVELOPER MODE

import discord
import asyncio
import os
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from games.game_module import GameManager, UserManager
from games.errors import UserBalanceHelper

load_dotenv()
guild_id = int(os.getenv('DISCORD_GUILD_ID'))

game_name = 'tictactoe'
entry_fee = GameManager.get_entry_fee(game_name)
win_payout = GameManager.get_win_payout(game_name)

class TicTacToeButton(discord.ui.Button):
    def __init__(self, x: int, y: int):
        super().__init__(label="\u200b", style=discord.ButtonStyle.secondary, row=y)
        self.x = x
        self.y = y

    async def callback(self, interaction: discord.Interaction):
        game = self.view
        if interaction.user != game.current_player:
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return

        if game.board[self.y][self.x] != " ":
            await interaction.response.send_message("That spot is already taken!", ephemeral=True)
            return

        # Mark the board
        game.board[self.y][self.x] = game.current_symbol
        self.label = game.current_symbol
        self.style = discord.ButtonStyle.success if game.current_symbol == "X" else discord.ButtonStyle.danger
        self.disabled = True

        # Reset inactivity timer
        game.reset_timer()


        # Check game status
        winner = game.check_winner()
        if winner:
            game.disable_all_buttons()
            game.cancel_timer()
            UserManager.update_user_balance(str(game.current_player.id), win_payout)
            embed = discord.Embed(title="Tic-Tac-Toe", description=f"🎉 **{game.current_player.mention} won {win_payout} coins!**", color=discord.Color.green())
            await interaction.response.edit_message(view=game, embed=embed)
            return
        
        if game.is_draw():
            game.disable_all_buttons()
            embed = discord.Embed(title="Tic-Tac-Toe", description="😲 **It's a draw!**", color=discord.Color.orange())
            await interaction.response.edit_message(view=game, embed=embed)
            return

        # Switch players
        game.switch_player()
        await interaction.response.edit_message(view=game)

class TicTacToeGame(discord.ui.View):
    def __init__(self, player1, player2, message):
        super().__init__()
        self.player1 = player1
        self.player2 = player2
        self.current_player = player1
        self.current_symbol = "X"
        self.board = [[" " for _ in range(3)] for _ in range(3)]
        self.message = message  # Store message to update later
        self.task = asyncio.create_task(self.inactivity_timer())  # Start inactivity timer

        # Add buttons
        for y in range(3):
            for x in range(3):
                self.add_item(TicTacToeButton(x, y))

    async def inactivity_timer(self):
        """Ends the game if no move is made within 30 seconds."""
        await asyncio.sleep(30)
        self.disable_all_buttons()
        embed = discord.Embed(title="Tic-Tac-Toe", description="⏳ **Game ended due to inactivity!**", color=discord.Color.red())
        await self.message.edit(embed=embed, view=None)


    def cancel_timer(self):
        """Safely cancels the inactivity timer."""
        if self.task and not self.task.done():
            self.task.cancel()

    def reset_timer(self):
        """Cancels the current timer and starts a new one."""
        self.task.cancel()
        self.task = asyncio.create_task(self.inactivity_timer())

    def switch_player(self):
        self.current_player = self.player1 if self.current_player == self.player2 else self.player2
        self.current_symbol = "X" if self.current_symbol == "O" else "O"

    def check_winner(self):
        lines = self.board + [list(x) for x in zip(*self.board)]  # Rows + Columns
        lines.append([self.board[i][i] for i in range(3)])  # Diagonal \
        lines.append([self.board[i][2 - i] for i in range(3)])  # Diagonal /

        for line in lines:
            if line[0] != " " and all(cell == line[0] for cell in line):
                return line[0]  # Return winning symbol
        return None

    def is_draw(self):
        return all(cell != " " for row in self.board for cell in row)

    def disable_all_buttons(self):
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

class TicTacToeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="tictactoe", description="Start a game of Tic-Tac-Toe with another player")
    @app_commands.guilds(discord.Object(id=guild_id))
    async def tictactoe(self, interaction: discord.Interaction, opponent: discord.Member):
        await interaction.response.defer()
        
        user_id = interaction.user.id
        opponent_id = opponent.id
        
        if opponent == interaction.user:
            await interaction.followup.send("You can't play against yourself!", ephemeral=True)
            return
        
        if not await UserBalanceHelper.validate_balance(interaction, user_id = user_id, entry_fee =entry_fee, single_player=False) or \
            not await UserBalanceHelper.validate_balance(interaction, user_id=opponent_id, entry_fee=entry_fee, single_player=False):
            return
        
        try:
            UserManager.update_user_balance(str(user_id), -entry_fee)
            UserManager.update_user_balance(str(opponent_id), -entry_fee)
        except Exception as e:
            await interaction.followup.send(f"Failed to deduct entry fee: {e}", ephemeral=True)
            return
            

        embed = discord.Embed(
            title="Tic-Tac-Toe",
            description=f"🎮 {interaction.user.mention} vs {opponent.mention}\n**{interaction.user.mention}'s turn!** (X)",
            color=discord.Color.blue(),
        )

        await interaction.followup.send(embed=embed)  # Send initial message
        message = await interaction.original_response()  # Get the sent message

        game = TicTacToeGame(interaction.user, opponent, message)
        await message.edit(view=game)  # Attach the game view


async def setup(bot):
    await bot.add_cog(TicTacToeCog(bot))
