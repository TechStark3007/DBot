from firebase_admin import credentials, firestore

# Initialize Firebase
#cred = credentials.Certificate("firebase_key.json")  # Path to your Firebase service account key
#firebase_admin.initialize_app(cred)

# Firestore client
firestore_db = firestore.client()

class UserManager:
    """Handles user-related operations in Firestore."""

    @staticmethod
    def get_user_balance(user_id: str) -> int:
        """
        Fetch the user's balance from Firestore. If the user doesn't exist, create a new document with balance = 0.
        """
        user_ref = firestore_db.collection('users').document(str(user_id))
        user_data = user_ref.get()

        if user_data.exists:
            return user_data.to_dict().get("balance", 0)  

        else:
            user_ref.set({'balance': 0})  # Create user with balance = 0
            return 0  # Return initial balance

    @staticmethod
    def update_user_balance(user_id: str, amount: int):
        """
        Update the user's balance in Firestore.
        """
        user_ref = firestore_db.collection('users').document(str(user_id))
        user_data = user_ref.get()

        if user_data.exists:
            current_balance = user_data.to_dict().get('balance', 0)
            new_balance = max(0, current_balance + amount)  # Ensure balance doesn't go negative
        else:
            new_balance = max(0, amount)  # If user doesn't exist, set initial balance to amount

        user_ref.set({'balance': new_balance}, merge=True)
        return new_balance  # Return updated balance



class GameManager:
    """Handles game-related fees and payouts."""

    @staticmethod
    def game_fees():
        """Returns the win payout and entry fee for all games."""
        return {
            "rps": {"win_payout": 20, "entry_fee": 10},
            "tictactoe": {"win_payout": 30, "entry_fee": 15},
            "hangman": {"win_payout": 40, "entry_fee": 20},
            "connect4": {"win_payout": 60, "entry_fee": 30},
            "chess": {"win_payout": 100, "entry_fee": 50},
        }

    @staticmethod
    def get_entry_fee(game_name):
        """Fetch the entry fee for a given game, defaulting to 0 if not found."""
        return GameManager.game_fees().get(game_name, {}).get("entry_fee", 0)
    
    @staticmethod
    def get_win_payout(game_name):
        """Fetch the win payout for a given game, deafulting to 0 if not found"""
        return GameManager.game_fees().get(game_name, {}).get("win_payout", 0)



