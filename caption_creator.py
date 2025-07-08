import warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
import logging
logging.getLogger().setLevel(logging.ERROR)

import argparse
from moviepy import VideoFileClip, CompositeVideoClip, ImageClip
from moviepy.video.fx import FadeIn, FadeOut
from stt.fasterwhispher import FasterWhispherSTTProcessor
import common
from custom_logger import logger_config
from typing import List, Dict, Tuple, Optional
import random
import os
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from config import Config

class CaptionCreator:
	"""
	A class for generating YouTube Shorts style captions with various effects.
	
	This class provides methods to create captions that can:
	- Display words one by one with color changes and animations
	- Show grouped captions with current word highlighting
	- Apply various visual effects like fade, bounce, and background highlights
	"""
	
	def __init__(self, video_path: str, config: Optional[Config] = None):
		"""
		Initialize the caption generator with a video file.
		
		Args:
			video_path (str): Path to the input video file
            config (Optional[Config]): A single configuration object.
                                       If None, default settings are used.
		"""
		self.video_path = os.path.abspath(video_path)
		self.config = config or Config()

		# Randomly select a font from the provided list
		chosen_font = random.choice(self.config.font_path)
		self.font_path = os.path.abspath(chosen_font)
		logger_config.info(f"Using font: {os.path.basename(self.font_path)}")
		self.video = None
		self.word_timestamps = []
		self._load_video_data()
	
	def _load_video_data(self) -> None:
		"""Load video file and extract word timestamps."""
		try:
			self.video = VideoFileClip(self.video_path)
			with FasterWhispherSTTProcessor() as STT:
				self.word_timestamps = STT.transcribe({"model": "fasterwhispher", "input": self.video_path})["segments"]["word"]
			
			logger_config.info(f"Video loaded successfully")
			logger_config.info(f"Video duration: {self.video.duration:.2f} seconds")
			logger_config.info(f"Total words: {len(self.word_timestamps)}")
			
		except Exception as e:
			raise ValueError(f"Failed to load video data: {str(e)}")

	def _clean_word(self, word: str) -> str:
		"""
		Clean and format a word for display.
		
		Args:
			word (str): Raw word from timestamps
			
		Returns:
			str: Cleaned and formatted word
		"""
		return word.strip('.,!?;:"""''').upper()
	
	def _calculate_word_duration(self, word_index: int) -> Tuple[float, float, float]:
		"""
		Calculate start time, end time, and duration for a word.
		
		Args:
			word_index (int): Index of the word in the timestamps list
			
		Returns:
			Tuple[float, float, float]: start_time, end_time, duration
		"""
		word_data = self.word_timestamps[word_index]
		start_time = word_data["start"]
		
		# Set end time to the start time of the next word for continuity
		if word_index < len(self.word_timestamps) - 1:
			end_time = self.word_timestamps[word_index + 1]["start"]
		else:
			end_time = word_data["end"]
		
		# Ensure we don't exceed video duration
		end_time = min(end_time, self.video.duration)
		duration = end_time - start_time
		
		return start_time, end_time, duration
	
	def _create_text_clip(self,
						words_data: List[Dict],
						highlight_word_index: int,
						start_time: float,
						duration: float,
						group_start_index: int = 0) -> ImageClip:
		"""
		Create a text clip with single word or grouped words and highlighting.

		Args:
			words_data (List[Dict]): List of word data dictionaries
			highlight_word_index (int): Index of the current word to highlight
			start_time (float): When to start displaying
			duration (float): How long to display
			group_start_index (int): Starting index of the group (for grouped mode)

		Returns:
			ImageClip: The text clip
		"""
		caption_width = int(self.video.size[0] * self.config.caption_width_ratio)

		caption_parts = []
		word_to_highlight = None
		for j, word_data in enumerate(words_data):
			word = self._clean_word(word_data["word"])
			if group_start_index + j == highlight_word_index:
				caption_parts.append((word, self.config.highlight_text_color))
				word_to_highlight = word
			else:
				caption_parts.append((word, self.config.text_color))

		# Load font
		font = ImageFont.truetype(self.font_path, self.config.font_size)

		# Simulate layout to calculate required height
		dummy_img = Image.new("RGBA", (caption_width, 10), (0, 0, 0, 0))
		draw = ImageDraw.Draw(dummy_img)

		# --- FIX 1: Use textlength for accurate space width ---
		# This provides the advance width, which is better for layout than bbox.
		space_width = draw.textlength(" ", font=font)

		# Buffer lines and compute dimensions
		lines = []
		current_line = []
		current_line_width = 0
		max_line_height = 0
		total_height = 0

		for word, color in caption_parts:
			# --- FIX 2: Use textlength for word width ---
			# This ensures layout is based on advance width, not just ink area.
			word_width = draw.textlength(word, font=font)
			
			# We still need textbbox to get the actual height of the word
			bbox = draw.textbbox((0, 0), word, font=font)
			word_height = bbox[3] - bbox[1]
			max_line_height = max(max_line_height, word_height)

			if current_line_width + word_width > caption_width:
				# Commit current line, removing trailing space width for accurate centering
				if current_line:
					lines.append((current_line, current_line_width - space_width, max_line_height))
					total_height += max_line_height + self.config.line_spacing
				# Start new line
				current_line = []
				current_line_width = 0
				max_line_height = word_height

			current_line.append((word, color, word_width))
			current_line_width += word_width + space_width

		if current_line:
			# Commit the last line, also removing the trailing space width
			lines.append((current_line, current_line_width - space_width, max_line_height))
			total_height += max_line_height + self.config.line_spacing

		# Add extra padding for descenders
		padding = int(self.config.font_size * 0.4)
		total_height += padding

		# Create image
		img = Image.new("RGBA", (caption_width, total_height), (0, 0, 0, 0))
		draw = ImageDraw.Draw(img)

		# Draw lines
		y = 0
		for line_words, line_width, line_height in lines:
			# Center align based on horizontal_align config
			if self.config.horizontal_align == "center":
				x = (caption_width - line_width) / 2
			elif self.config.horizontal_align == "left":
				x = 0
			else:  # right
				x = caption_width - line_width

			for word, color, word_width in line_words:
				# Draw background highlight if this is the word to highlight
				if word_to_highlight == word:
					padding_x, padding_y = self.config.highlight_padding

					# --- FIX 3: Calculate highlight box based on layout position (x) and width ---
					# This ensures the highlight padding is symmetrical around the word's allocated space.
					
					# Use textbbox only for accurate *vertical* positioning
					text_bbox = draw.textbbox((x, y), word, font=font)
					rect_y0 = text_bbox[1] - padding_y
					rect_y1 = text_bbox[3] + padding_y

					# Use the layout's x and word_width for horizontal bounds
					rect_x0 = x - padding_x
					rect_x1 = x + word_width + padding_x

					# Draw background rectangle
					draw.rectangle(
						[rect_x0, rect_y0, rect_x1, rect_y1],
						fill=self.config.highlight_bg_color
					)

				# Draw stroke (outline) around text
				for dx in range(-self.config.stroke_width, self.config.stroke_width + 1):
					for dy in range(-self.config.stroke_width, self.config.stroke_width + 1):
						draw.text((x + dx, y + dy), word, font=font, fill=self.config.stroke_color)

				# Draw the actual text
				draw.text((x, y), word, font=font, fill=color)

				x += word_width + space_width

			y += line_height + self.config.line_spacing

		# Convert PIL image to MoviePy ImageClip
		txt_clip = ImageClip(np.array(img)).with_duration(duration).with_start(start_time)

		txt_clip = txt_clip.with_position((self.config.vertical_align, self.config.horizontal_align))

		# Apply animations for single word mode
		if self.config.use_fade_and_scale:
			fade_duration = min(self.config.fade_duration, duration * 0.3)

			# Apply scaling effect
			txt_clip = txt_clip.resized(lambda t: max(0.1, 1 + self.config.scale_effect_intensity * (1 - abs(t - duration / 2) / max(0.1, duration / 2))))

			# Apply fade effects
			txt_clip = txt_clip.with_effects([FadeIn(fade_duration), FadeOut(fade_duration)])

		return txt_clip
	
	def generate(self) -> str:
		"""
		Create captions that display words in groups, highlight the current word, 
		and wrap text to fit the video width.

		Returns:
			str: Path to the generated video file
		"""
		logger_config.info("Starting grouped captions with highlight generation...")
		
		# Calculate caption width for proper text wrapping
		caption_width = int(self.video.size[0] * self.config.caption_width_ratio)
		logger_config.info(f"Setting caption width to {caption_width}px ({self.config.caption_width_ratio*100}% of video width)")
		
		text_clips = []
		for i in range(len(self.word_timestamps)):
			# Calculate group boundaries
			group_start_index = (i // self.config.word_count) * self.config.word_count
			group_end_index = min(len(self.word_timestamps), group_start_index + self.config.word_count)
			group_words_data = self.word_timestamps[group_start_index:group_end_index]
			
			# Calculate timing
			start_time, end_time, duration = self._calculate_word_duration(i)
			
			# Skip if word starts after video ends
			if start_time >= self.video.duration:
				break
			
			# Skip if duration is too short
			if duration <= 0:
				continue
			
			# Create text clip for grouped words
			txt_clip = self._create_text_clip(
				words_data=group_words_data,
				highlight_word_index=i if self.config.highlight_text else -1,
				start_time=start_time,
				duration=duration,
				group_start_index=group_start_index
			)
			
			text_clips.append(txt_clip)
			
			logger_config.info(f"Processed word {i + 1}/{len(self.word_timestamps)} in grouped captions...", overwrite=True)
		
		# Compose final video
		final_clip = CompositeVideoClip([self.video] + text_clips)
		common.write_videofile(final_clip, self.config.output_path)
		
		# Clean up
		final_clip.close()
		
		logger_config.success(f"Grouped captions video saved to: {self.config.output_path}")
		return self.config.output_path
	
	def close(self) -> None:
		"""Clean up resources."""
		if self.video:
			self.video.close()
	
	def __enter__(self):
		"""Context manager entry."""
		return self
	
	def __exit__(self, exc_type, exc_val, exc_tb):
		"""Context manager exit."""
		self.close()


# Usage example
if __name__ == "__main__":
	"""Main entry point."""
	parser = argparse.ArgumentParser()
	parser.add_argument("--input", required=True, help="Path to the input video")
	parser.add_argument("--config_path", required=False, help="Path to configuration JSON")
	args = parser.parse_args()

	if args.config_path:
		custom_config = Config.from_json(args.config_path)
	else:
		custom_config = Config()
	# args.input = "SvtTCBLqqZ.mp4"

	if args.input:
		with CaptionCreator(args.input, custom_config) as caption_generator:
			caption_generator.generate()

	else: logger_config.warning("Please provide input file using --input")