"""Post-processing: BG removal, edge cleanup, color quantization, resize."""

import os
from PIL import Image
from .common import load_image, save_image, scale_nearest, parse_color, is_empty_tile


def remove_background_color(img, color=(255, 255, 255), tolerance=30):
    """Remove background by color-keying. Pixels matching color become transparent.

    Args:
        img: PIL Image (RGBA)
        color: (R, G, B) background color to remove
        tolerance: Color matching tolerance (0-255)
    """
    img = img.copy().convert("RGBA")
    pixels = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if (abs(r - color[0]) <= tolerance and
                abs(g - color[1]) <= tolerance and
                abs(b - color[2]) <= tolerance):
                pixels[x, y] = (0, 0, 0, 0)
    return img


def remove_background_edge(img, threshold=20):
    """Remove background by flood-filling from edges.

    Samples the corner colors, then flood-fills from all edge pixels
    that match, setting them to transparent.

    Args:
        img: PIL Image (RGBA)
        threshold: Color similarity threshold for flood fill
    """
    img = img.copy().convert("RGBA")
    w, h = img.size
    pixels = img.load()

    # Sample background color from corners
    corners = [pixels[0, 0], pixels[w-1, 0], pixels[0, h-1], pixels[w-1, h-1]]
    # Use the most common corner color
    bg_color = max(set(corners), key=corners.count)

    visited = set()
    stack = []

    # Seed from all edge pixels
    for x in range(w):
        stack.append((x, 0))
        stack.append((x, h - 1))
    for y in range(h):
        stack.append((0, y))
        stack.append((w - 1, y))

    while stack:
        x, y = stack.pop()
        if (x, y) in visited:
            continue
        if x < 0 or x >= w or y < 0 or y >= h:
            continue
        visited.add((x, y))

        px = pixels[x, y]
        if (abs(px[0] - bg_color[0]) <= threshold and
            abs(px[1] - bg_color[1]) <= threshold and
            abs(px[2] - bg_color[2]) <= threshold):
            pixels[x, y] = (0, 0, 0, 0)
            stack.append((x + 1, y))
            stack.append((x - 1, y))
            stack.append((x, y + 1))
            stack.append((x, y - 1))

    return img


def clean_edges(img, alpha_threshold=128):
    """Threshold alpha channel for crisp pixel art edges.

    Pixels with alpha >= threshold become fully opaque,
    pixels below become fully transparent.

    Args:
        img: PIL Image (RGBA)
        alpha_threshold: Cutoff value (0-255)
    """
    img = img.copy().convert("RGBA")
    alpha = img.getchannel("A")
    alpha = alpha.point(lambda v: 255 if v >= alpha_threshold else 0)
    img.putalpha(alpha)
    return img


def quantize_colors(img, n_colors=16, palette=None):
    """Reduce image to n colors. Optionally snap to a provided palette.

    Args:
        img: PIL Image (RGBA)
        n_colors: Number of colors to quantize to
        palette: Optional list of (R, G, B) tuples to snap to
    """
    # Preserve alpha
    alpha = img.getchannel("A")

    # Quantize the RGB channels
    rgb = img.convert("RGB")
    quantized = rgb.quantize(colors=n_colors, method=Image.Quantize.MEDIANCUT)
    quantized = quantized.convert("RGB")

    if palette:
        # Snap each pixel to nearest palette color
        pixels = quantized.load()
        w, h = quantized.size
        for y in range(h):
            for x in range(w):
                px = pixels[x, y]
                nearest = min(palette, key=lambda c: sum((a - b) ** 2 for a, b in zip(px, c)))
                pixels[x, y] = nearest

    result = quantized.convert("RGBA")
    result.putalpha(alpha)
    return result


def batch_process(input_dir, output_dir, operations):
    """Apply a list of operations to all PNG files in a directory.

    Args:
        input_dir: Directory containing source PNGs
        output_dir: Directory for processed outputs
        operations: List of (func, kwargs) tuples to apply in order
    """
    os.makedirs(output_dir, exist_ok=True)
    results = []
    for filename in sorted(os.listdir(input_dir)):
        if not filename.lower().endswith(".png"):
            continue
        img = load_image(os.path.join(input_dir, filename))
        for func, kwargs in operations:
            img = func(img, **kwargs)
        out_path = os.path.join(output_dir, filename)
        save_image(img, out_path)
        results.append(out_path)
    return results
