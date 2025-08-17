#DEVELOPER MODE

import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()
guild_id = int(os.getenv('DISCORD_GUILD_ID'))

# Constants
ROWS = 6
COLS = 7
TIMEOUT = 30  # 30 seconds timeout

class Connect4Game:
    def __init__(self):
        self.board = [['⚪' for _ in range(COLS)] for _ in range(ROWS)]
        self.players = {}
        self.current_player = None
        self.game_over = False

    def drop_disc(self, col, emoji):
        """Drops a disc in the selected column."""
        for row in range(ROWS - 1, -1, -1):
            if self.board[row][col] == '⚪':
                self.board[row][col] = emoji
                return row
        return None  # Column is full

    def check_win(self, row, col, emoji):
        """Checks if the last move caused a win."""
        directions = [(1, 0), (0, 1), (1, 1), (1, -1)]
        for dr, dc in directions:
            count = 1
            for d in (1, -1):
                r, c = row, col
                while 0 <= (r := r + d * dr) < ROWS and 0 <= (c := c + d * dc) < COLS and self.board[r][c] == emoji:
                    count += 1
                    if count >= 4:
                        return True
        return False

    def is_draw(self):
        return all(self.board[0][c] != '⚪' for c in range(COLS))

    def render_board(self):
        """Creates a Discord-friendly board representation."""
        return "\n".join("".join(row) for row in self.board) + "\n1️⃣2️⃣3️⃣4️⃣5️⃣6️⃣7️⃣"

class Connect4(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.games = {}  # Stores ongoing games (per channel)

    @app_commands.command(name="connect4", description="Start a game of Connect 4 with another player")
    @app_commands.guilds(discord.Object(id=guild_id))
    async def connect4(self, interaction: discord.Interaction, opponent: discord.Member):
        """Start a Connect 4 game"""
        if interaction.user == opponent:
            await interaction.response.send_message("You cannot play against yourself!", ephemeral=True)
            return

        if interaction.channel_id in self.games:
            await interaction.response.send_message("A game is already running in this channel!", ephemeral=True)
            return

        game = Connect4Game()
        game.players = {interaction.user: '🔴', opponent: '🟡'}
        game.current_player = interaction.user
        self.games[interaction.channel_id] = game

        await interaction.response.send_message(f"{interaction.user.mention} (🔴) vs {opponent.mention} (🟡)\n{game.render_board()}")
        await self.send_controls(interaction)

        # Start the timeout task
        self.bot.loop.create_task(self.check_inactivity(interaction.channel_id, game))

    async def send_controls(self, interaction):
        """Send buttons for column selection"""
        game = self.games[interaction.channel_id]
        view = discord.ui.View()
        for i in range(COLS):
            view.add_item(Connect4Button(i, self))
        await interaction.followup.send(f"{game.current_player.mention}, it's your turn!", view=view)

    async def make_move(self, button, interaction):
        """Handle button press"""
        game = self.games.get(interaction.channel_id)
        if not game or game.game_over:
            await interaction.response.send_message("No active game here!", ephemeral=True)
            return

        if interaction.user != game.current_player:
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return

        col = button.column
        row = game.drop_disc(col, game.players[game.current_player])
        if row is None:
            await interaction.response.send_message("That column is full!", ephemeral=True)
            return

        # Check win/draw conditions
        if game.check_win(row, col, game.players[game.current_player]):
            game.game_over = True
            await interaction.message.edit(content=f"{game.current_player.mention} wins!\n{game.render_board()}", view=None)
            del self.games[interaction.channel_id]
            return
        elif game.is_draw():
            game.game_over = True
            await interaction.message.edit(content=f"It's a draw!\n{game.render_board()}", view=None)
            del self.games[interaction.channel_id]
            return

        # Switch turn
        game.current_player = next(player for player in game.players if player != game.current_player)
        await interaction.message.edit(content=f"{game.current_player.mention}, it's your turn!\n{game.render_board()}")

        # Restart inactivity timer
        self.bot.loop.create_task(self.check_inactivity(interaction.channel_id, game))

    async def check_inactivity(self, channel_id, game):
        """Ends game if inactive for too long"""
        await asyncio.sleep(TIMEOUT)

        # If the game still exists and is not over, end it
        if channel_id in self.games and not game.game_over:
            self.games[channel_id].game_over = True
            del self.games[channel_id]
            await self.bot.get_channel(channel_id).send("Game ended due to inactivity.")

class Connect4Button(discord.ui.Button):
    """Represents a column button"""
    def __init__(self, column, game_cog):
        super().__init__(label=str(column + 1), style=discord.ButtonStyle.primary)
        self.column = column
        self.game_cog = game_cog

    async def callback(self, interaction: discord.Interaction):
        await self.game_cog.make_move(self, interaction)

async def setup(bot):
    await bot.add_cog(Connect4(bot))
