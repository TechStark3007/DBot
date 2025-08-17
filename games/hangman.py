import discord
import os
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from games.game_module import UserManager, GameManager
from games.errors import UserBalanceHelper
import aiohttp
import asyncio

load_dotenv()
guild_id = int(os.getenv('DISCORD_GUILD_ID'))

game_name = 'hangman'
entry_fee = GameManager.get_entry_fee(game_name)
win_payout = GameManager.get_win_payout(game_name)

hangman_image_base_url = 'https://files.catbox.moe/'

class HangmanCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

    def cog_unload(self):
        asyncio.create_task(self.session.close())

    @app_commands.command(name="hangman", description="Play a game of Hangman")
    @app_commands.guilds(discord.Object(id=guild_id))
    async def hangman(self, interaction: discord.Interaction):
        await interaction.response.defer()
        user_id = interaction.user.id

        if not await UserBalanceHelper.validate_balance(
            interaction, 
            user_id = user_id, 
            entry_fee= entry_fee,
            single_player=True
            ):
            return

        # Fetch a random word from the API
        async with self.session.get('https://random-word-api.herokuapp.com/word') as response:
            if response.status == 200:
                word = (await response.json())[0]
            else:
                await interaction.followup.send("Could not fetch a word. Please try again later.")
                return
              

        guessed_letters = []
        attempts = 6
        hidden_word = "_ " * len(word)

        hangman_images = [
            "02qywf.png", "t0hgkv.png", "wusfdh.png", "fhfao1.png",
            "yict22.png", "03wo80.png", "bl0x72.png"
        ]

        # Create initial embed
        embed = discord.Embed(title="Hangman", description=f"Word: `{hidden_word}`", color=discord.Color.blue())
        embed.set_image(url=hangman_image_base_url + hangman_images[0])

        # Send the first embed and store the message reference
        await interaction.followup.send(embed=embed)
        msg = await interaction.original_response()  # Store the message

        # Game loop
        while attempts > 0:
            def check(m):
                return m.author == interaction.user and m.channel == interaction.channel and len(m.content) == 1

            payout = 0
            try:
                guess_msg = await self.bot.wait_for('message', timeout=30.0, check=check)
            except asyncio.TimeoutError:
                embed.description = f"Time's up! The word was: `{word}`"
                embed.color = discord.Color.red()
                await msg.edit(embed=embed)
                payout = -entry_fee
                break

            guess = guess_msg.content.lower()

            if guess in guessed_letters:
                await interaction.followup.send("You've already guessed that letter!", ephemeral=True)
                continue

            guessed_letters.append(guess)

            if guess in word:
                hidden_word = "".join([letter if letter in guessed_letters else "_" for letter in word])
                if hidden_word == word:
                    embed.description = f"🎉 Congratulations! You've guessed the word: `{word}`\n You won **{win_payout} coins**"
                    embed.color = discord.Color.green()
                    await msg.edit(embed=embed)
                    payout = win_payout - entry_fee
                    break
            else:
                attempts -= 1
                if attempts == 0:
                    embed.description = f"❌ Game over! The word was: `{word}`\n You lost **{entry_fee} coins**"
                    embed.color = discord.Color.red()
                    embed.set_image(url=hangman_image_base_url + hangman_images[6])
                    await msg.edit(embed=embed)
                    payout = -entry_fee
                    break

            # Update the embed instead of sending a new one
            embed.description = f"Word: `{hidden_word}`\nAttempts left: `{attempts}`"
            embed.set_image(url=hangman_image_base_url + hangman_images[6 - attempts])
            await msg.edit(embed=embed)

        try:
            UserManager.update_user_balance(user_id, payout) 
        except Exception as e:
            print(e)
            await interaction.followup.send("An error occurred while updating your balance. Please contact an administrator.", ephemeral=True)
            return



async def setup(bot):
    await bot.add_cog(HangmanCog(bot))
