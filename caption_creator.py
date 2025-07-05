from moviepy import VideoFileClip, TextClip, CompositeVideoClip, ImageClip
from moviepy.video.fx import FadeIn, FadeOut
from stt import runner
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
            config (Optional[CaptionConfig]): A single configuration object.
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
			result = runner.initiate({"model": "fasterwhispher", "input": self.video_path})
			self.word_timestamps = result["segments"]["word"]
			
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
	
	def _create_animated_text_clip(self, word: str, start_time: float, duration: float) -> TextClip:
		"""
		Create an animated text clip with effects.
		
		Args:
			word (str): The word to display
			start_time (float): When to start displaying the word
			duration (float): How long to display the word
			
		Returns:
			TextClip: The animated text clip
		"""
		# Create the base text clip
		txt_clip = TextClip(
			text=word,
			font_size=self.config.font_size,
			color=self.config.text_color,
			font=self.font_path,
			stroke_color=self.config.stroke_color,
			stroke_width=self.config.stroke_width,
			method="caption",
			size=self.video.size,
			text_align=self.config.vertical_align
		)
		
		# Set timing and position
		txt_clip = (
			txt_clip
			.with_duration(duration)
			.with_start(start_time)
			.with_position('center')
		)
		
		# Apply animations if requested
		if self.config.use_fade_and_scale:
			fade_duration = min(self.config.fade_duration, duration * 0.3)
			
			# Apply scaling effect
			txt_clip = txt_clip.resized(lambda t: max(0.1, 1 + 0.15 * (1 - abs(t - duration / 2) / max(0.1, duration / 2))))
			
			# Apply fade effects - FIXED: Apply effects properly
			txt_clip = txt_clip.with_effects([FadeIn(fade_duration), FadeOut(fade_duration)])
		
		return txt_clip

	def _create_highlighted_group_clip(self, group_words_data: List[Dict], current_word_index: int, group_start_index: int, start_time: float, duration: float) -> CompositeVideoClip:
		"""
		Create a text clip with grouped words and current word highlighting using PIL for custom fonts.
		"""
		caption_width = int(self.video.size[0] * self.config.caption_width_ratio)
		# Prepare text with highlight
		caption_parts = []
		word_to_highlight = None
		for j, word_data in enumerate(group_words_data):
			word = self._clean_word(word_data["word"])
			if group_start_index + j == current_word_index:
				# caption_parts.append((word, highlight_color))
				caption_parts.append((word, "white"))
				word_to_highlight = word
			else:
				caption_parts.append((word, "white"))
		
		# Load font
		font = ImageFont.truetype(self.font_path, self.config.font_size)
		
		# Simulate layout to calculate required height
		dummy_img = Image.new("RGBA", (caption_width, 10), (0, 0, 0, 0))
		draw = ImageDraw.Draw(dummy_img)
		space_bbox = draw.textbbox((0, 0), " ", font=font)
		space_width = space_bbox[2] - space_bbox[0]
		
		# Buffer lines and compute dimensions
		lines = []
		current_line = []
		current_line_width = 0
		max_line_height = 0
		total_height = 0

		for word, color in caption_parts:
			bbox = draw.textbbox((0, 0), word, font=font)
			word_width = bbox[2] - bbox[0]
			word_height = bbox[3] - bbox[1]
			max_line_height = max(max_line_height, word_height)

			if current_line_width + word_width > caption_width:
				# Commit current line
				lines.append((current_line, current_line_width, max_line_height))
				total_height += max_line_height + 10  # line spacing
				# Start new line
				current_line = []
				current_line_width = 0
				max_line_height = word_height

			current_line.append((word, color, word_width))
			current_line_width += word_width + space_width

		if current_line:
			lines.append((current_line, current_line_width, max_line_height))
			total_height += max_line_height + 10

		# Add extra padding for descenders
		padding = int(self.config.font_size * 0.4)
		total_height += padding

		# Create image
		img = Image.new("RGBA", (caption_width, total_height), (0, 0, 0, 0))
		draw = ImageDraw.Draw(img)

		# Draw lines
		y = 0
		for line_words, line_width, line_height in lines:
			x = (caption_width - line_width) // 2  # Center align the entire line
			for word, color, word_width in line_words:
				if word_to_highlight == word:
					# Draw background rectangle behind word
					padding_x = 10  # horizontal padding
					padding_y = 5   # vertical padding
					
					# Use textbbox for accurate positioning on both x and y axes
					text_bbox = draw.textbbox((x, y), word, font=font)
					rect_x0 = text_bbox[0] - padding_x  # Left edge of text minus padding
					rect_y0 = text_bbox[1] - padding_y  # Top edge of text minus padding
					rect_x1 = text_bbox[2] + padding_x  # Right edge of text plus padding
					rect_y1 = text_bbox[3] + padding_y  # Bottom edge of text plus padding

					# Draw background rectangle
					draw.rectangle(
						[rect_x0, rect_y0, rect_x1, rect_y1],
						fill=self.config.highlight_bg_color  # Use the color you want for the background
					)

				# Draw stroke (outline) around text
				for dx in range(-self.config.stroke_width, self.config.stroke_width + 1):
					for dy in range(-self.config.stroke_width, self.config.stroke_width + 1):
						draw.text((x + dx, y + dy), word, font=font, fill="black")

				# Draw the actual text
				draw.text((x, y), word, font=font, fill=color)

				x += word_width + space_width  # Move to next word

			y += line_height + 10  # Move to next line

		# Convert PIL image to MoviePy ImageClip
		txt_clip = (ImageClip(np.array(img))
					.with_duration(duration)
					.with_start(start_time)
					.with_position(("center", "center")))  # Fully centered

		return txt_clip

	
	def generate_word_by_word_captions(self, output_path: str) -> str:
		"""
		Create YouTube Shorts style captions with color-changing bold text and bounce effect.
		Each word appears individually with animations.
		"""
		logger_config.info("Starting word-by-word caption generation...")
		
		text_clips = []
		
		for i, word_data in enumerate(self.word_timestamps):
			word = word_data["word"]
			start_time, end_time, duration = self._calculate_word_duration(i)
			
			# Skip if word starts after video ends
			if start_time >= self.video.duration:
				break
			
			# Skip very short words
			if duration < 0.05:
				continue
			
			# Clean and format the word
			display_word = self._clean_word(word)
			
			# Create animated text clip
			txt_clip = self._create_animated_text_clip(
				display_word, start_time, duration
			)
			
			text_clips.append(txt_clip)
			
			logger_config.info(f"Processed {i + 1}/{len(self.word_timestamps)} words...", overwrite=True)
		
		# Compose final video
		final_clip = CompositeVideoClip([self.video] + text_clips)
		common.write_videofile(final_clip, output_path)
		
		# Clean up
		final_clip.close()
		
		logger_config.success(f"Word-by-word captions video saved to: {output_path}")
		return output_path
	
	def generate_grouped_captions_with_highlight(self, output_path: str) -> str:
		"""
		Create captions that display words in groups, highlight the current word, 
		and wrap text to fit the video width.
		
		Args:
			output_path (str): Path where the output video will be saved
			
		Returns:
			str: Path to the generated video file
		"""
		logger_config.info("Starting grouped captions with highlight generation...")
		
		# Calculate caption width for proper text wrapping
		caption_width = int(self.video.size[0] * 0.9)
		logger_config.info(f"Setting caption width to {caption_width}px (90% of video width)")
		
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
			
			# Create highlighted group clip
			txt_clip = self._create_highlighted_group_clip(
				group_words_data, i, group_start_index, start_time, duration
			)
			
			text_clips.append(txt_clip)
			
			logger_config.info(f"Processed word {i + 1}/{len(self.word_timestamps)} in grouped captions...", overwrite=True)
		
		# Compose final video
		final_clip = CompositeVideoClip([self.video] + text_clips)
		common.write_videofile(final_clip, output_path)
		
		# Clean up
		final_clip.close()
		
		logger_config.success(f"Grouped captions video saved to: {output_path}")
		return output_path
	
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
	video_path = "/home/jebineinstein/git/CaptionCreator/video/SvtTCBLqqZ.mp4"

	custom_config = Config()

	# Using context manager for automatic cleanup
	with CaptionCreator(video_path) as caption_generator:
		# Generate word-by-word captions
		output_path= "output_word_by_word_shorts.mp4"
		caption_generator.generate_word_by_word_captions(output_path)
		
		# Generate grouped captions with highlighting
		output_path = "output_grouped_highlight_shorts.mp4"
		caption_generator.generate_grouped_captions_with_highlight(
			output_path
		)