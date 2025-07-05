from pathlib import Path
import os
import shutil
import string
import argparse
from datetime import datetime, timedelta
from custom_logger import logger_config
import secrets
import hashlib
import random
import time
import subprocess
import re
import ffmpeg
import requests
from PIL import Image, PngImagePlugin

def path_exists(path):
    return file_exists(path) or dir_exists(path)

def file_exists(file_path):
    try:
        return Path(file_path).is_file()
    except:
        pass
    return False

def dir_exists(file_path):
    try:
        return Path(file_path).is_dir()
    except:
        pass
    return False

def list_files_recursive(directory):
    remove_zone_identifier(directory)
    # Initialize an empty array to store the file paths
    file_list = []
    
    # Walk through the directory recursively
    for root, dirs, files in os.walk(directory):
        for file in files:
            # Get the full path of the file and append to the array
            file_list.append(os.path.join(root, file))
    
    return file_list

def list_directories_recursive(directory):
    remove_zone_identifier(directory)
    # Initialize an empty list to store the directory names
    directory_list = []
    
    # Walk through the directory recursively
    for root, dirs, files in os.walk(directory):
        for dir_name in dirs:
            # Get the full path of the directory and append to the list
            directory_list.append(os.path.join(root, dir_name))
    
    return directory_list

def remove_zone_identifier(directory):
    try:
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith(":Zone.Identifier"):
                    full_path = os.path.join(root, file)
                    remove_file(full_path)
    except: pass


def list_files(directory):
    remove_zone_identifier(directory)
    # Initialize an empty array to store the file paths
    file_list = []
    
    # Get the list of files in the given directory (non-recursive)
    for file in os.listdir(directory):
        # Construct the full path and check if it's a file
        full_path = os.path.join(directory, file)
        if os.path.isfile(full_path):
            file_list.append(full_path)
    
    return file_list

def remove_path(path):
    remove_file(path, True)
    remove_all_files_and_dirs(path)

def remove_file(file_path, retry=True):
    try:
        # Check if the file exists
        if os.path.exists(file_path):
            Path(file_path).unlink()
            logger_config.success(f"{file_path} has been removed successfully.")
    except Exception as e:
        logger_config.warning(f"Error occurred while trying to remove the file: {e}")
        if retry:
            logger_config.debug("retrying after 10 seconds", seconds=10)
            remove_file(file_path, False)

def remove_all_files_and_dirs(directory):
    try:
        shutil.rmtree(directory)  # Recursively delete a directory
    except Exception as e:
        logger_config.warning(f"Failed to delete {directory}. Reason: {e}")

def remove_directory(directory_path):
    try:
        if os.path.exists(directory_path):
            shutil.rmtree(directory_path)
            logger_config.debug(f'Directory Deleted at: {directory_path}')
    except Exception as e:
        logger_config.warning(f'An error occurred: {e}')

def create_directory(directory_path):
    try:
        # Create the directory
        os.makedirs(directory_path, exist_ok=True)  # exist_ok=True avoids error if the dir already exists
        logger_config.debug(f'Directory created at: {directory_path}')
    except Exception as e:
        logger_config.error(f'An error occurred: {e}')

def generate_random_string(length=10):
    characters = string.ascii_letters
    random_string = ''.join(secrets.choice(characters) for _ in range(length))
    return random_string

def get_date(when=0):
    today = datetime.now()
    sub_day = today - timedelta(days=when)

    sub_day_str = sub_day.strftime('%Y-%m-%d')    
    return sub_day_str

def generate_random_string_from_input(input_string, length=10):
    # Hash the input string to get a consistent value
    hash_object = hashlib.md5(input_string.encode())
    hashed_string = hash_object.hexdigest()

    # Use the hash to seed the random number generator
    random.seed(hashed_string)

    # Generate a random string based on the seed
    characters = string.ascii_letters + string.digits
    random_string = ''.join(random.choice(characters) for _ in range(length))

    return random_string

def rename_file(current_name, new_name):
    try:
        # Rename the file
        os.rename(current_name, new_name)
        logger_config.success(f"File renamed from '{current_name}' to '{new_name}'")
    except Exception as e:
        logger_config.error(f"An error occurred: {e}")

def copy(source, dest):
    try:
        shutil.copy2(source, dest)
    except Exception as e:
        logger_config.error(f"An error occurred: {e}")

def clean_text(text):
    text = re.sub(r"\\+", "", text)
    return re.sub(r'\s+', ' ', text).strip()

def get_media_metadata(file_path):
    try:
        probe = ffmpeg.probe(file_path, v='error', select_streams='v:0', show_entries='format=duration,streams')

        # Duration in float seconds
        duration_in_sec_float = float(probe['format']['duration'])
        duration_in_sec_int = int(duration_in_sec_float)

        # File size in MB
        size = int(os.path.getsize(file_path) // (1024 * 1024))

        fps = None
        for stream in probe['streams']:
            if stream['codec_type'] == 'video':
                fps = eval(stream['r_frame_rate'])  # Frames per second (r_frame_rate is in format num/den)

        return duration_in_sec_int, duration_in_sec_float, size, fps
    except Exception as e:
        logger_config.error(f"Error retrieving media metadata: {e}")
        return None, None, None, None

def write_videofile(video_clip, output_path, fps=24):
    audio_file = f'{generate_random_string()}.mp3'
    video_clip.write_videofile(
        output_path,
        fps=fps,
        codec='libx264',
        # audio_codec='aac',
        # preset='faster',  # Faster encoding, slightly larger file
        threads=os.cpu_count(),  # Use all available CPU cores
        bitrate='8000k',  # Adjust based on your quality needs
        remove_temp=True,
        temp_audiofile=audio_file
    )
    remove_file(audio_file)

def write_audiofile(audio_clip, output_path, fps=44100, codec="libmp3lame", bitrate="192k"):
    audio_clip.write_audiofile(
        output_path,
        fps=fps,
        codec=codec,
        bitrate=bitrate
    )

def download_image(image_url, save_path, throw_error=False):
	response = requests.get(image_url, stream=True)
	if response.status_code == 200:
		with open(save_path, 'wb') as file:
			for chunk in response.iter_content(1024):
				file.write(chunk)
	elif throw_error:
		raise ValueError(f"Error: Unable to download image, status code {response.status_code}")

def get_html_content(url):
    response = requests.get(url)
    if response.status_code != 200:
        raise ValueError(f"Error: Unable to fetch page, status code {response.status_code}")

    return response.content

def write_to_png(data_str, image_path='media/sliding_dialog_shorts/ChatGPT Image Apr 3, 2025, 02_03_23 PM.png'):
    with Image.open(image_path) as img:
        img_copy = img.copy()

        metadata = PngImagePlugin.PngInfo()
        metadata.add_text("Comment", data_str)

        img_copy.save(image_path, "PNG", pnginfo=metadata)

def read_from_png(image_path='media/sliding_dialog_shorts/ChatGPT Image Apr 3, 2025, 02_03_23 PM.png'):
    with Image.open(image_path) as image:
        return image.info.get("Comment")

def is_mostly_black(img, black_pixel_threshold=0.9, black_rgb_threshold=10):
        """
        Returns True if >= 90% of pixels are near black.
        `black_rgb_threshold` defines how dark a pixel must be to count as black.
        """
        img = img.convert("RGB")
        pixels = list(img.getdata())
        total_pixels = len(pixels)
        black_pixels = sum(
            1 for r, g, b in pixels if r <= black_rgb_threshold and g <= black_rgb_threshold and b <= black_rgb_threshold
        )
        return (black_pixels / total_pixels) >= black_pixel_threshold

def is_server_alive(url):
    try:
        response = requests.get(url, timeout=3)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False