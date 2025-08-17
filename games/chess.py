#DEVELOPER MODE

import discord
from discord.ext import commands
from discord import app_commands
import random
import chess
import chess.svg
import asyncio
import os
import cairosvg
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()
guild_id = int(os.getenv('DISCORD_GUILD_ID'))

class BlitzChess:
    def __init__(self, player1: discord.Member, player2: discord.Member):
        self.board = chess.Board()
        self.players = {chess.WHITE: player1, chess.BLACK: player2}
        self.timers = {chess.WHITE: 480, chess.BLACK: 480}  # 8 min per player
        self.current_turn = chess.WHITE
        self.game_over = False
        self.task = None
        self.last_move_time = None
        self.message_id = None  # Variable to store the message ID 


    def cancel_timer(self):
        if self.task and not self.task.done():
            self.task.cancel()

    async def start_timer(self, interaction: discord.Interaction):
        """Handles player time tracking."""
        self.last_move_time = asyncio.get_event_loop().time()
        while not self.game_over:
            await asyncio.sleep(1)
            elapsed = asyncio.get_event_loop().time() - self.last_move_time
            self.timers[self.current_turn] -= int(elapsed)
            self.last_move_time = asyncio.get_event_loop().time()

            if self.timers[self.current_turn] <= 0:
                self.game_over = True
                await interaction.followup.send(f"{self.players[self.current_turn].mention} ran out of time! {self.players[not self.current_turn].mention} wins!")
                return

    def switch_turn(self):
        self.current_turn = not self.current_turn
        self.last_move_time = asyncio.get_event_loop().time()

    def validate_move(self, move: str):
        try:
            chess.Move.from_uci(move)
            return move in [m.uci() for m in self.board.legal_moves]
        except:
            return False

    def make_move(self, move: str):
        if self.validate_move(move):
            self.board.push_uci(move)
            return True
        return False

    def check_game_status(self):
        if self.board.is_checkmate():
            self.game_over = True
            return "Checkmate!"
        elif self.board.is_stalemate() or self.board.is_insufficient_material() or self.board.is_repetition():
            self.game_over = True
            return "Game drawn!"
        return None

    def generate_board_image(self) -> BytesIO:
        """Generates a PNG image of the current board state."""
        try:
            board_svg = chess.svg.board(self.board, size=500)
            board_png = BytesIO()
            cairosvg.svg2png(bytestring=board_svg.encode('utf-8'), write_to=board_png)
            board_png.seek(0)
            return board_png
        except Exception as e:
            print(f"Error generating board image: {e}")
            return None


class ChessCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.games = {}

    @app_commands.command(name="chess", description="Start a game of Blitz Chess")
    @app_commands.guilds(discord.Object(id=guild_id))
    async def chess(self, interaction: discord.Interaction, opponent: discord.Member):
        if interaction.channel_id in self.games:
            await interaction.response.send_message("A chess game is already in progress in this channel!", ephemeral=True)
            return

        if opponent == interaction.user:
            await interaction.response.send_message("You can't play against yourself!", ephemeral=True)
            return

        # Randomly assign colors
        white, black = random.sample([interaction.user, opponent], 2)

        game = BlitzChess(white, black)
        self.games[interaction.channel_id] = game

        board_image = game.generate_board_image()
        file = discord.File(board_image, filename="chessboard.png")

        embed = discord.Embed(
            title="Blitz Chess",
            description=f"{white.mention} (**White ♔**) vs {black.mention} (**Black ♚**)"
        )
        embed.set_image(url="attachment://chessboard.png")

        await interaction.response.send_message(embed=embed, file=file)
        message = await interaction.original_response() 
        game.message_id = message.id  # Stores the message ID

        game.task = asyncio.create_task(game.start_timer(interaction))

    @app_commands.command(name="move", description="Make a move in your ongoing chess game")
    @app_commands.guilds(discord.Object(id=guild_id))
    async def move(self, interaction: discord.Interaction, move: str):
        game = self.games.get(interaction.channel_id)
        if not game or game.game_over:
            await interaction.response.send_message("No active chess game here!", ephemeral=True)
            return

        if interaction.user != game.players[game.current_turn]:
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)  

        if game.make_move(move):
            status = game.check_game_status()

            board_image = game.generate_board_image()
            file = discord.File(board_image, filename="chessboard.png")

            # Fetch the original game message using its ID
            try:
                game_message = await interaction.channel.fetch_message(game.message_id)
            except discord.NotFound:
                await interaction.response.send_message("Game message not found!", ephemeral=True)
                return

            # Edit the existing embed
            embed = game_message.embeds[0]
            embed.description = f"{interaction.user.mention} played `{move}`."
            embed.set_image(url="attachment://chessboard.png")

            if status:
                embed.add_field(name="Game Over", value=status)
                await game_message.edit(embed=embed, attachments=[file])
                game.cancel_timer()
                del self.games[interaction.channel_id]
                return

            game.switch_turn()
            embed.add_field(name="Next Turn", value=f"{game.players[game.current_turn].mention}'s turn!", inline=False)
            embed.add_field(name="White Time", value=f"{game.timers[chess.WHITE] // 60}:{game.timers[chess.WHITE] % 60:02}")
            embed.add_field(name="Black Time", value=f"{game.timers[chess.BLACK] // 60}:{game.timers[chess.BLACK] % 60:02}")

            await game_message.edit(embed=embed, attachments=[file])
            await interaction.followup.send(f"You played {move}", ephemeral=True)
        else:
            await interaction.followup.send("Invalid move!", ephemeral=True)


    @app_commands.command(name="resign", description="Resign from your ongoing chess game")
    @app_commands.guilds(discord.Object(id=guild_id))
    async def resign(self, interaction: discord.Interaction):
        game = self.games.get(interaction.channel_id)
        if not game or game.game_over:
            await interaction.response.send_message("No active chess game here!", ephemeral=True)
            return

        if interaction.user not in game.players.values():
            await interaction.response.send_message("You're not part of this game!", ephemeral=True)
            return

        # Determine the opponent of the resigning user
        resigning_player = interaction.user
        opponent = None
        for color, player in game.players.items():
            if player == resigning_player:
                opponent = game.players[not color]  # Get the opponent
                break

        if not opponent:
            await interaction.response.send_message("Error: Could not determine the opponent.", ephemeral=True)
            return

        game.game_over = True
        game.cancel_timer()
        await interaction.response.send_message(f"{resigning_player.mention} resigned! {opponent.mention} wins!")
        del self.games[interaction.channel_id]

async def setup(bot):
    await bot.add_cog(ChessCog(bot))
