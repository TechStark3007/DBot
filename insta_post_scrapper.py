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

load_dotenv()
instagram_username = str(os.getenv("INSTAGRAM_USERNAME"))

# Generate a random filename
def generate_random_filename(length=14):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# Compress image
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

# Compress video
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

# Fetch only the latest post without extra GraphQL calls
def fetch_image_links(username: str, post_info: dict):
    L = instaloader.Instaloader(download_pictures=False, download_videos=False, download_comments=False, save_metadata=False, compress_json=False)

    # Load cookies from env
    cookies = {
        "sessionid": os.getenv("IG_SESSIONID"),
        "csrftoken": os.getenv("IG_CSRFTOKEN"),
        "ds_user_id": os.getenv("IG_DS_USER_ID"),
        "mid": os.getenv("IG_MID"),
        "ig_did": os.getenv("IG_DID"),
    }

    if not all(cookies.values()):
        raise Exception("Missing Instagram cookies in environment.")

    for key, value in cookies.items():
        L.context._session.cookies.set(key, value)

    try:
        profile = instaloader.Profile.from_username(L.context, username)
    except Exception as e:
        raise Exception(f"Error loading profile: {e}")

    try:
        latest_post = next(profile.get_posts())
    except Exception as e:
        raise Exception(f"Error fetching posts: {e}")

    latest_post_id = str(latest_post.mediaid)
    if latest_post_id == str(post_info.get("post_id")):
        print(f"No new post for {username}.")
        return post_info.get("post_id"), post_info.get("last_updated")

    folder_path = "insta_posts"
    os.makedirs(folder_path, exist_ok=True)

    try:
        # Sidecar post (carousel)
        if latest_post.typename == 'GraphSidecar':
            for node in latest_post.get_sidecar_nodes():
                url = node.video_url if node.is_video else node.display_url
                ext = "mp4" if node.is_video else "jpg"

                response = requests.get(url)
                response.raise_for_status()
                media_bytes = response.content

                if node.is_video and len(media_bytes) > 10 * 1024 * 1024:
                    media_bytes = compress_video(media_bytes)
                elif not node.is_video and len(media_bytes) > 9 * 1024 * 1024:
                    media_bytes = compress_image(media_bytes)

                filename = generate_random_filename() + f".{ext}"
                with open(os.path.join(folder_path, filename), 'wb') as file:
                    file.write(media_bytes)
                print(f"Downloaded media: {filename}")

        else:
            # Single media
            url = latest_post.video_url if latest_post.is_video else latest_post.url
            ext = "mp4" if latest_post.is_video else "jpg"

            response = requests.get(url)
            response.raise_for_status()
            media_bytes = response.content

            if latest_post.is_video and len(media_bytes) > 10 * 1024 * 1024:
                media_bytes = compress_video(media_bytes)
            elif not latest_post.is_video and len(media_bytes) > 9 * 1024 * 1024:
                media_bytes = compress_image(media_bytes)

            filename = generate_random_filename() + f".{ext}"
            with open(os.path.join(folder_path, filename), 'wb') as file:
                file.write(media_bytes)
            print(f"Downloaded media: {filename}")

    except Exception as e:
        raise Exception(f"Error downloading media: {e}")

    post_timestamp = latest_post.date_utc.strftime("%Y-%m-%dT%H:%M:%S.%f")
    return latest_post_id, post_timestamp
