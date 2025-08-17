from games.game_module import UserManager

class UserBalanceHelper:
    """Handles user balance retrieval and validation in Firestore."""

    @staticmethod
    async def validate_balance(interaction, *, user_id:int, entry_fee: int, single_player:bool) -> bool:
        """
        Fetches the user's balance and checks if they have enough to proceed.
        If an error occurs, it notifies the user.
        
        Returns:
            - True if the user has enough balance
            - False if there was an error or insufficient balance
        """
    
        try:
            user_balance = UserManager.get_user_balance(user_id)  
        except Exception as e:
            print(f"Error fetching balance for {user_id}: {e}")
            await interaction.followup.send(
                "An error occurred while fetching your balance. Please try again later.", ephemeral=True
            )
            return False  # ❌ Balance retrieval failed
        
        # Get the username for multiplayer games
        user_mention = 'You' if single_player == True else interaction.user.mention if interaction.user.id == user_id else f"<@{user_id}>"


        if user_balance < entry_fee:
            await interaction.followup.send(
                f"Insufficient balance: {user_mention} need at least {entry_fee} coins to play.", ephemeral=True
            )
            return False  # ❌ Not enough balance

        return True  # ✅ Balance is sufficient
