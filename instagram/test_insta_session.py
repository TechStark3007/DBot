import instaloader
import os

def login_with_session(username, session_file):
    # Create an instance of Instaloader
    L = instaloader.Instaloader()

    try:
        # Check if the session file exists
        if os.path.exists(session_file):
            # Load the session from the file
            print(f"Loading session from {session_file}...")
            L.load_session_from_file(username, session_file)
            print(f"Successfully logged in as {username} using the session.")
        else:
            raise FileNotFoundError(f"Session file '{session_file}' not found.")
    
    except FileNotFoundError as e:
        print(f"Error: {e}")
    
    except instaloader.exceptions.BadCredentialsException:
        print("Error: Invalid credentials. The session might have expired or be invalid.")
    
    except instaloader.exceptions.ConnectionException:
        print("Error: Connection error. Unable to connect to Instagram.")
    
    except instaloader.exceptions.TwoFactorAuthRequiredException:
        print("Error: Two-factor authentication is required. Please log in manually to update the session.")
    
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    username = 'sinister.giggles_'  # Replace with your Instagram username
    session_file = 'instagram_session.session'  # Replace with the path to your session file
    login_with_session(username, session_file)
