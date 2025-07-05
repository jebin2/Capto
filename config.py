from dataclasses import dataclass, field
from typing import List, Tuple
import common

@dataclass
class Config:
    """A single configuration class to style captions."""

    # --- Font and Color ---
    font_path: List[str] = field(default_factory=lambda: ["Fonts/font_1.ttf"])
    color_palette: List[str] = field(default_factory=lambda: [
        "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4",
        "#DDA0DD", "#FF9F43", "#6C5CE7", "#A8E6CF", "#FFB6C1"
    ])

    # --- General Text Properties ---
    font_size: int = 100
    text_color: str = "white"
    stroke_color: str = "black"
    stroke_width: int = 3
    vertical_align: str = "center"
    horizontal_align: str = "center"
    
    # --- Animation (for word-by-word) ---
    use_fade_and_scale: bool = True
    fade_duration: float = 0.2
    scale_effect_intensity: float = 0.15

    # --- Text Properties ---
    word_count: int = 4
    line_spacing: int = 10
    caption_width_ratio: float = 0.9
    bg_color: str = "#6C5CE7"
    
    # --- Highlighting (for grouped) ---
    highlight_text: bool = True
    highlight_text_color: str = "white"
    highlight_bg_color: str = "#FF6B6B"
    highlight_padding: Tuple[int, int] = (10, 5) # (horizontal, vertical)

    # --- Output Path ---
    output_path: str = f'output/{common.generate_random_string()}.mp4'