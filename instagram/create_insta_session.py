import instaloader

# Define Instagram credentials
USERNAME = 'sinister.giggles_'
PASSWORD = 'vetke2-jykwid-qAdneh'
SESSION_FILE = 'instagram_session.session'

# Initialize Instaloader instance
loader = instaloader.Instaloader()

# Log in to Instagram and save the session
try:
    print("Logging in to Instagram...")
    loader.login(USERNAME, PASSWORD)  # Log in with username and password

    # Save the session to the specified file
    loader.save_session_to_file(SESSION_FILE)
    print(f"Session saved to '{SESSION_FILE}' successfully.")

except instaloader.exceptions.BadCredentialsException:
    print("Failed to log in. Please check your username and password.")
except Exception as e:
    print(f"An error occurred: {e}")
