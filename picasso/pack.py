"""Sprite sheet packer using shelf algorithm + JSON/Godot atlas output."""

import os
import json
from PIL import Image
from .common import load_image, save_image, next_power_of_2, make_output_dir


def pack_sprites(input_paths, padding=0, power_of_2=False):
    """Pack sprites into a single sheet using shelf packing.

    Sorts sprites by height (descending), then fills rows (shelves).

    Args:
        input_paths: List of image file paths
        padding: Pixels between sprites
        power_of_2: Round sheet dimensions up to power of 2

    Returns:
        (sheet_image, atlas_dict) where atlas maps filename → {x, y, w, h}
    """
    # Load all sprites
    sprites = []
    for path in input_paths:
        img = load_image(path)
        name = os.path.splitext(os.path.basename(path))[0]
        sprites.append((name, img))

    if not sprites:
        sheet = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        return sheet, {}

    # Sort by height descending for better shelf packing
    sprites.sort(key=lambda s: s[1].height, reverse=True)

    # Estimate sheet width: aim for roughly square
    total_area = sum(img.width * img.height for _, img in sprites)
    est_side = int(total_area ** 0.5)
    max_w = max(img.width for _, img in sprites)
    sheet_w = max(est_side, max_w + padding)

    if power_of_2:
        sheet_w = next_power_of_2(sheet_w)

    # Shelf packing
    shelves = []  # List of (y, shelf_height, cursor_x)
    placements = {}

    cur_y = 0
    cur_x = 0
    shelf_h = 0

    for name, img in sprites:
        w, h = img.width + padding, img.height + padding

        if cur_x + w > sheet_w:
            # Start new shelf
            cur_y += shelf_h
            cur_x = 0
            shelf_h = 0

        placements[name] = (cur_x, cur_y, img.width, img.height)
        shelf_h = max(shelf_h, h)
        cur_x += w

    sheet_h = cur_y + shelf_h

    if power_of_2:
        sheet_h = next_power_of_2(sheet_h)

    # Compose sheet
    sheet = Image.new("RGBA", (sheet_w, sheet_h), (0, 0, 0, 0))
    atlas = {}

    for name, img in sprites:
        x, y, w, h = placements[name]
        sheet.paste(img, (x, y))
        atlas[name] = {"x": x, "y": y, "w": w, "h": h}

    return sheet, atlas


def pack_directory(input_dir, output_path, padding=0, power_of_2=False):
    """Pack all PNGs in a directory into a sprite sheet.

    Args:
        input_dir: Directory containing PNG sprites
        output_path: Path for the output sheet PNG
        padding: Pixels between sprites
        power_of_2: Round dimensions to power of 2

    Returns:
        (sheet_image, atlas_dict)
    """
    paths = sorted([
        os.path.join(input_dir, f)
        for f in os.listdir(input_dir)
        if f.lower().endswith(".png")
    ])
    sheet, atlas = pack_sprites(paths, padding=padding, power_of_2=power_of_2)
    save_image(sheet, output_path)
    return sheet, atlas


def save_atlas_json(atlas, path):
    """Save atlas dictionary as JSON.

    Args:
        atlas: Dict mapping sprite name → {x, y, w, h}
        path: Output JSON file path
    """
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w") as f:
        json.dump(atlas, f, indent=2, sort_keys=True)


def generate_godot_atlas(atlas, sheet_path, output_dir):
    """Generate Godot .tres AtlasTexture files for each sprite in the atlas.

    Creates one .tres file per sprite that references the sheet texture.

    Args:
        atlas: Dict mapping sprite name → {x, y, w, h}
        sheet_path: Path to the sprite sheet image (relative to Godot project)
        output_dir: Directory to write .tres files
    """
    os.makedirs(output_dir, exist_ok=True)

    for name, rect in atlas.items():
        tres_content = (
            '[gd_resource type="AtlasTexture" load_steps=2 format=3]\n'
            '\n'
            f'[ext_resource type="Texture2D" path="{sheet_path}" id="1"]\n'
            '\n'
            '[resource]\n'
            'atlas = ExtResource("1")\n'
            f'region = Rect2({rect["x"]}, {rect["y"]}, {rect["w"]}, {rect["h"]})\n'
        )
        tres_path = os.path.join(output_dir, f"{name}.tres")
        with open(tres_path, "w") as f:
            f.write(tres_content)
