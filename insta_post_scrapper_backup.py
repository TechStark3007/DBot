import instaloader
import os
import requests
import random
import string
from PIL import Image
from io import BytesIO
from moviepy.editor import VideoFileClip
from datetime import datetime
from dotenv import load_dotenv
import json

load_dotenv()
instagram_username = str(os.getenv("INSTAGRAM_USERNAME"))

# Function to generate a random 14 char file name
def generate_random_filename(length=14):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# Function to compress image
def compress_image(image_bytes, max_size_mb=9):
    max_size_bytes = max_size_mb * 1024 * 1024
    image = Image.open(BytesIO(image_bytes))
    if len(image_bytes) > max_size_bytes:
        quality = 95
        while len(image_bytes) > max_size_bytes and quality > 10:
            buffer = BytesIO()
            image.save(buffer, format=image.format, optimize=True, quality=quality)
            image_bytes = buffer.getvalue()
            quality -= 5
    return image_bytes

# Function to compress video
def compress_video(video_bytes, max_size_mb=9):
    max_size_bytes = max_size_mb * 1024 * 1024
    temp_input = 'temp_input_video.mp4'
    temp_output = 'temp_compressed_video.mp4'
    with open(temp_input, 'wb') as f:
        f.write(video_bytes)

    video = VideoFileClip(temp_input)
    if os.path.getsize(temp_input) > max_size_bytes:
        video.write_videofile(temp_output, codec='libx264', bitrate="500k", threads=4)
        with open(temp_output, 'rb') as compressed_file:
            video_bytes = compressed_file.read()
        os.remove(temp_output)
    video.close()
    os.remove(temp_input)
    return video_bytes

# Fetch image/video links from the latest Instagram post
def fetch_image_links(username: str, post_info: dict):
    L = instaloader.Instaloader()

    # Load Instagram cookies from environment
    IG_SESSIONID = os.getenv("IG_SESSIONID")
    IG_CSRFTOKEN = os.getenv("IG_CSRFTOKEN")
    IG_DS_USER_ID = os.getenv("IG_DS_USER_ID")
    IG_MID = os.getenv("IG_MID")
    IG_DID = os.getenv("IG_DID")

    if not all([IG_SESSIONID, IG_CSRFTOKEN, IG_DS_USER_ID, IG_MID, IG_DID]):
        raise Exception("One or more Instagram cookie variables are missing from the environment.")

    # Set cookies manually
    cookies = {
        "sessionid": IG_SESSIONID,
        "csrftoken": IG_CSRFTOKEN,
        "ds_user_id": IG_DS_USER_ID,
        "mid": IG_MID,
        "ig_did": IG_DID,
    }
    for key, value in cookies.items():
        L.context._session.cookies.set(key, value)

    # Load the profile
    try:
        profile = instaloader.Profile.from_username(L.context, username)
    except Exception as e:
        raise Exception(f"Error loading profile: {e}")

    # Get the latest post
    try:
        latest_post = next(profile.get_posts())
    except Exception as e:
        raise Exception(f"Error fetching posts: {e}")

    latest_post_id = str(latest_post.mediaid)
    if latest_post_id == str(post_info.get("post_id")):
        print(f"Post ID matches. No new post for {username}. Skipping media download.")
        return post_info.get("post_id"), post_info.get("last_updated")

    folder_path = "insta_posts"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    try:
        # Handle carousel (GraphSidecar)
        if latest_post.typename == 'GraphSidecar':
            for node in latest_post.get_sidecar_nodes():
                try:
                    is_video = node.is_video
                    url = node.video_url if is_video else node.display_url
                    response = requests.get(url)
                    response.raise_for_status()
                    media_bytes = response.content

                    if is_video:
                        if len(media_bytes) > 10 * 1024 * 1024:
                            media_bytes = compress_video(media_bytes)
                        file_extension = "mp4"
                    else:
                        if len(media_bytes) > 9 * 1024 * 1024:
                            media_bytes = compress_image(media_bytes)
                        file_extension = "jpg"

                    random_filename = generate_random_filename() + f".{file_extension}"
                    with open(os.path.join(folder_path, random_filename), 'wb') as file:
                        file.write(media_bytes)
                    print(f"Downloaded media: {random_filename}")

                except Exception as download_error:
                    print(f"Error downloading media: {download_error}")

        else:
            # Single photo or video post
            is_video = latest_post.is_video
            url = latest_post.video_url if is_video else latest_post.url
            response = requests.get(url)
            response.raise_for_status()
            media_bytes = response.content

            if is_video:
                if len(media_bytes) > 10 * 1024 * 1024:
                    media_bytes = compress_video(media_bytes)
                file_extension = "mp4"
            else:
                if len(media_bytes) > 9 * 1024 * 1024:
                    media_bytes = compress_image(media_bytes)
                file_extension = "jpg"

            random_filename = generate_random_filename() + f".{file_extension}"
            with open(os.path.join(folder_path, random_filename), 'wb') as file:
                file.write(media_bytes)
            print(f"Downloaded media: {random_filename}")

    except Exception as e:
        raise Exception(f"Error processing media: {e}")

    post_timestamp = latest_post.date_utc.strftime("%Y-%m-%dT%H:%M:%S.%f")
    return latest_post_id, post_timestamp
