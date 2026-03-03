"""Generate text tiles with outlines and shadows for game UIs."""

import os
import string
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from .common import save_image, make_output_dir


DEFAULT_CHARSET = string.ascii_uppercase + string.digits + ".,!?:-+/()' "


def render_text_tile(char, size, font, fg=(255, 255, 255), outline=None, shadow=None, shadow_offset=(1, 1)):
    """Render a single character tile.

    Args:
        char: Character to render
        size: (width, height) of the tile
        font: PIL ImageFont
        fg: Foreground color (R, G, B) or (R, G, B, A)
        outline: Outline color (R, G, B) or None for no outline
        shadow: Shadow color (R, G, B, A) or None
        shadow_offset: (dx, dy) shadow offset in pixels

    Returns:
        PIL Image (RGBA)
    """
    tile_w, tile_h = size
    tile = Image.new("RGBA", (tile_w, tile_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(tile)

    # Measure character
    bbox = draw.textbbox((0, 0), char, font=font)
    char_w = bbox[2] - bbox[0]
    char_h = bbox[3] - bbox[1]

    # Center in tile
    x = (tile_w - char_w) // 2 - bbox[0]
    y = (tile_h - char_h) // 2 - bbox[1]

    # Draw shadow
    if shadow:
        shadow_layer = Image.new("RGBA", (tile_w, tile_h), (0, 0, 0, 0))
        sdraw = ImageDraw.Draw(shadow_layer)
        sx = x + shadow_offset[0]
        sy = y + shadow_offset[1]
        sdraw.text((sx, sy), char, font=font, fill=shadow)
        tile = Image.alpha_composite(tile, shadow_layer)
        draw = ImageDraw.Draw(tile)

    # Draw outline by rendering text offset in 8 directions
    if outline:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                draw.text((x + dx, y + dy), char, font=font, fill=outline)

    # Draw main character
    draw.text((x, y), char, font=font, fill=fg)

    return tile


def generate_charset(chars=None, tile_size=(32, 32), font_path=None, font_size=None,
                     fg=(255, 255, 255), outline=None, shadow=None):
    """Generate tiles for a set of characters.

    Args:
        chars: String of characters (defaults to A-Z, 0-9, common symbols)
        tile_size: (width, height) per tile
        font_path: Path to .ttf font file
        font_size: Font size in pixels (auto-calculated if None)
        fg: Foreground color
        outline: Outline color or None
        shadow: Shadow color or None

    Returns:
        List of (char, image) tuples.
    """
    if chars is None:
        chars = DEFAULT_CHARSET

    if font_size is None:
        font_size = int(tile_size[1] * 0.75)

    if font_path:
        font = ImageFont.truetype(font_path, font_size)
    else:
        font = ImageFont.load_default()

    tiles = []
    for char in chars:
        tile = render_text_tile(char, tile_size, font, fg=fg, outline=outline, shadow=shadow)
        tiles.append((char, tile))

    return tiles


def generate_text_sheet(chars=None, tile_size=(32, 32), cols=16, font_path=None,
                        font_size=None, fg=(255, 255, 255), outline=None, shadow=None,
                        output_path=None):
    """Generate a sprite sheet of text tiles plus atlas JSON.

    Args:
        chars: String of characters
        tile_size: (width, height) per tile
        cols: Columns in the sheet
        font_path: Path to .ttf font
        font_size: Font size
        fg: Foreground color
        outline: Outline color
        shadow: Shadow color
        output_path: Path to save sheet PNG (atlas JSON saved alongside)

    Returns:
        (sheet_image, atlas_dict)
    """
    tiles = generate_charset(chars, tile_size, font_path, font_size, fg, outline, shadow)

    rows = (len(tiles) + cols - 1) // cols
    tile_w, tile_h = tile_size
    sheet_w = cols * tile_w
    sheet_h = rows * tile_h

    sheet = Image.new("RGBA", (sheet_w, sheet_h), (0, 0, 0, 0))
    atlas = {}

    for idx, (char, tile) in enumerate(tiles):
        r = idx // cols
        c = idx % cols
        x = c * tile_w
        y = r * tile_h
        sheet.paste(tile, (x, y))
        atlas[char] = {"x": x, "y": y, "w": tile_w, "h": tile_h}

    if output_path:
        save_image(sheet, output_path)

    return sheet, atlas
