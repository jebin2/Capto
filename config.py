from dataclasses import dataclass, field, asdict, fields
from typing import List, Tuple
import common
import json

@dataclass
class Config:
    """A single configuration class to style captions."""

    # --- Font and Color ---
    font_path: List[str] = field(default_factory=lambda: ["Fonts/font_1.ttf", "Fonts/font_2.ttf"])
    color_palette: List[str] = field(default_factory=lambda: [
        "#FF6B6B", "#4ECDC4", "#2AA0BB", "#36AF77",
        "#C565C5", "#58310B", "#6C5CE7", "#1C533F", "#BB394C"
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
    highlight_padding: Tuple[int, int] = (10, 5)  # (horizontal, vertical)

    # --- Output Path ---
    output_path: str = f'output/{common.generate_random_string()}.mp4'

    @staticmethod
    def from_json(json_path: str) -> "Config":
        """Load Config from JSON, merging with defaults."""
        with open(json_path, "r") as f:
            json_data = json.load(f)

        # Get default config as dict
        default_values = asdict(Config())

        # Filter json_data to only keys present in Config fields
        field_names = {f.name for f in fields(Config)}
        filtered_data = {k: v for k, v in json_data.items() if k in field_names}

        # Merge filtered JSON data into defaults
        merged = {**default_values, **filtered_data}

        return Config(**merged)

    def to_json(self, json_path: str, indent: int = 4) -> None:
        """Export current Config instance to a JSON file."""
        with open(json_path, "w") as f:
            json.dump(asdict(self), f, indent=indent)
        print(f"✅ Config saved to {json_path}")
