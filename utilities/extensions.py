from discord.ext import commands

extensions = [
    "utilities.ip",
    "features.anime_sfw",
    "announce",
    "utilities.emailchecker",
    "features.giphy",
    "instarss",        # Instagram RSS feed
    "instapost",       # Instagram Post
    "gemini",         # Text gen AI
    "weather",
    "moderation",
    "music",
    "games.rps",       # Rock, Paper, Scissors
    "games.hangman",   # Hangman
    "games.tictactoe", # Tic Tac Toe
    "games.connect4",  # Connect 4
    "games.chess"      # Chess
]

async def load_extensions(bot: commands.Bot):
    for ext in extensions:
        await bot.load_extension(ext)
