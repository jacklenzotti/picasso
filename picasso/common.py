"""Shared utilities for image loading, saving, scaling, and color helpers."""

import os
import math
from PIL import Image


def load_image(path):
    """Load an image as RGBA."""
    return Image.open(path).convert("RGBA")


def save_image(img, path):
    """Save an image, creating parent directories if needed."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    img.save(path)


def scale_nearest(img, factor):
    """Scale image with nearest neighbor (pixel art friendly)."""
    new_w = int(img.width * factor)
    new_h = int(img.height * factor)
    return img.resize((new_w, new_h), Image.NEAREST)


def resize_to(img, width, height, resample=Image.NEAREST):
    """Resize image to exact dimensions."""
    return img.resize((width, height), resample)


def next_power_of_2(n):
    """Return the next power of 2 >= n."""
    if n <= 0:
        return 1
    return 1 << (n - 1).bit_length()


def make_output_dir(path):
    """Create output directory if it doesn't exist. Returns the path."""
    os.makedirs(path, exist_ok=True)
    return path


def parse_color(color_str):
    """Parse a color string like '#FFFFFF' or 'FF00FF' into an (R, G, B) tuple."""
    c = color_str.strip().lstrip("#")
    if len(c) == 6:
        return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))
    elif len(c) == 8:
        return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), int(c[6:8], 16))
    raise ValueError(f"Invalid color: {color_str}")


def is_empty_tile(img, threshold=0):
    """Check if an RGBA image is effectively empty (all pixels below alpha threshold)."""
    if img.mode != "RGBA":
        return False
    alpha = img.getchannel("A")
    return alpha.getextrema()[1] <= threshold


def parse_size(size_str):
    """Parse a size string like '32x32' into (width, height)."""
    parts = size_str.lower().split("x")
    return (int(parts[0]), int(parts[1]))
