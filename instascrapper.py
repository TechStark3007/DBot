import instaloader
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
instagram_username = str(os.getenv("INSTAGRAM_USERNAME"))

class InstaScrapper:
    def __init__(self):
        self.loader = instaloader.Instaloader()
        self.rss_file_path = 'rss.json'

        # Load the session from the session file path stored in an environment variable
        session_file_path = os.getenv('INSTAGRAM_SESSION_PATH', 'instagram_session.session')  # Ensure this is set in your environment
        if not session_file_path:
            raise Exception("Session file path not set in environment variables.")
        
        try:
            self.loader.load_session_from_file(instagram_username, session_file_path)  # Replace 'your_username' with your Instagram username
        except Exception as e:
            raise Exception(f"Error loading session: {e}")

    def load_feeds(self):
        """Load RSS feeds from the JSON file."""
        if os.path.exists(self.rss_file_path):
            with open(self.rss_file_path, 'r') as file:
                try:
                    feeds = json.load(file)
                    # Ensure 'instagram' structure is present
                    if 'instagram' not in feeds:
                        feeds['instagram'] = {'feeds': {}}
                except json.JSONDecodeError:
                    # Handle empty or corrupted JSON file
                    feeds = {"instagram": {"feeds": {}}}
        else:
            # Initialize a new structure if the file doesn't exist
            feeds = {"instagram": {"feeds": {}}}
        return feeds

    def save_feeds(self, feeds):
        """Save RSS feeds to the JSON file."""
        with open(self.rss_file_path, 'w') as file:
            json.dump(feeds, file, indent=4)

    def fetch_last_post(self, username):
        """Fetch the latest post from the specified Instagram username."""
        try:
            profile = instaloader.Profile.from_username(self.loader.context, username)
            posts = profile.get_posts()
            last_post = next(posts)  # Get the latest post

            post_data = {
                'caption': last_post.caption,
                'image_url': last_post.url,
                'timestamp': last_post.date,
                'post_id': last_post.date.timestamp()  # Use timestamp as a unique ID
            }
            return post_data
        except Exception as e:
            print(f"Error fetching post for {username}: {str(e)}")
            return None

    def format_post_as_rss(self, post_data):
        """Convert post data to a simplified RSS-like format."""
        caption = post_data['caption'] or "No caption available"  # Provide a default caption if it's None
        return {
            'title': caption[:50],  # Limit to 50 characters for title
            'link': post_data['image_url'],
            'description': caption,
            'pub_date': post_data['timestamp'].strftime("%a, %d %b %Y %H:%M:%S %z")
        }

    def run_scraper(self):
        """Run the scraper for all feeds."""
        feeds = self.load_feeds()
        now = datetime.now()

        for feed_name, feed_info in feeds['instagram']['feeds'].items():
            username = feed_info['username']
            post_id = feed_info.get('post_id')

            # Calculate the last updated time
            last_updated = datetime.fromisoformat(feed_info.get('last_updated', '1970-01-01T00:00:00'))

            # Check if it's time to scrape again (every 2 minutes)
            if now - last_updated >= timedelta(minutes=30):
                post_data = self.fetch_last_post(username)

                if post_data:
                    # Check if the post ID is null or does not match the new post ID
                    if post_id is None or post_data['post_id'] != post_id:
                        # Update the RSS JSON with new values
                        feed_info['post_id'] = post_data['post_id']
                        feed_info['last_updated'] = now.isoformat()
                        self.save_feeds(feeds)  # Save the updated feeds
                        print(f"New post for {username} sent to Discord.")
                    else:
                        print(f"No new posts for {username}.")
                else:
                    print(f"Could not fetch post for {username}.")

        # Update last run time
        feeds['instagram']['last_updated'] = now.isoformat()
        self.save_feeds(feeds)
