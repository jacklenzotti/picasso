"""9-slice panel builder for UI containers (scoreboards, frames, popups)."""

from PIL import Image, ImageDraw


def generate_panel(size, border=4, radius=0,
                   fill=(40, 40, 60, 220),
                   border_color=(180, 180, 200, 255),
                   highlight=None, shadow=None):
    """Generate an RGBA panel frame.

    Args:
        size: (width, height) tuple
        border: Border thickness in pixels
        radius: Corner radius (0 for sharp corners)
        fill: Interior fill color (R, G, B, A)
        border_color: Border color (R, G, B, A)
        highlight: Optional top/left bevel color (R, G, B, A)
        shadow: Optional bottom/right bevel color (R, G, B, A)

    Returns:
        PIL Image (RGBA)
    """
    w, h = size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    # Layer 1: border (full rounded rect)
    border_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw_b = ImageDraw.Draw(border_layer)
    if radius > 0:
        draw_b.rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=border_color)
    else:
        draw_b.rectangle([0, 0, w - 1, h - 1], fill=border_color)
    img = Image.alpha_composite(img, border_layer)

    # Layer 2: fill (inset by border width)
    if border > 0:
        fill_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw_f = ImageDraw.Draw(fill_layer)
        inner_radius = max(0, radius - border)
        if inner_radius > 0:
            draw_f.rounded_rectangle(
                [border, border, w - 1 - border, h - 1 - border],
                radius=inner_radius, fill=fill,
            )
        else:
            draw_f.rectangle(
                [border, border, w - 1 - border, h - 1 - border],
                fill=fill,
            )
        img = Image.alpha_composite(img, fill_layer)
    else:
        # No border — fill the whole shape
        fill_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw_f = ImageDraw.Draw(fill_layer)
        if radius > 0:
            draw_f.rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=fill)
        else:
            draw_f.rectangle([0, 0, w - 1, h - 1], fill=fill)
        img = Image.alpha_composite(img, fill_layer)

    # Layer 3: highlight bevel (top and left edges, inset 1px from outer edge)
    if highlight and border >= 2:
        hl_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw_hl = ImageDraw.Draw(hl_layer)
        # Top edge highlight
        for i in range(1, min(border, 3)):
            draw_hl.line([(border, i), (w - 1 - border, i)], fill=highlight)
        # Left edge highlight
        for i in range(1, min(border, 3)):
            draw_hl.line([(i, border), (i, h - 1 - border)], fill=highlight)
        img = Image.alpha_composite(img, hl_layer)

    # Layer 4: shadow bevel (bottom and right edges)
    if shadow and border >= 2:
        sh_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw_sh = ImageDraw.Draw(sh_layer)
        # Bottom edge shadow
        for i in range(1, min(border, 3)):
            y = h - 1 - i
            draw_sh.line([(border, y), (w - 1 - border, y)], fill=shadow)
        # Right edge shadow
        for i in range(1, min(border, 3)):
            x = w - 1 - i
            draw_sh.line([(x, border), (x, h - 1 - border)], fill=shadow)
        img = Image.alpha_composite(img, sh_layer)

    return img


def slice_nine(image, border):
    """Cut a panel image into 9 pieces for 9-slice rendering.

    Args:
        image: Source PIL Image
        border: Border width used to determine slice boundaries

    Returns:
        List of (name, Image) tuples:
        [corner_tl, edge_t, corner_tr, edge_l, center, edge_r, corner_bl, edge_b, corner_br]
    """
    w, h = image.size
    b = border

    # Define crop regions: (left, upper, right, lower)
    regions = {
        "corner_tl": (0, 0, b, b),
        "edge_t":    (b, 0, w - b, b),
        "corner_tr": (w - b, 0, w, b),
        "edge_l":    (0, b, b, h - b),
        "center":    (b, b, w - b, h - b),
        "edge_r":    (w - b, b, w, h - b),
        "corner_bl": (0, h - b, b, h),
        "edge_b":    (b, h - b, w - b, h),
        "corner_br": (w - b, h - b, w, h),
    }

    pieces = []
    for name, box in regions.items():
        piece = image.crop(box)
        pieces.append((name, piece))
    return pieces


def generate_panel_sheet(panels, cols=4):
    """Pack multiple panel variants into a sprite sheet with atlas.

    Args:
        panels: List of (name, Image) tuples
        cols: Number of columns in the sheet

    Returns:
        (sheet_image, atlas_dict)
    """
    if not panels:
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0)), {}

    rows = -(-len(panels) // cols)  # ceil division
    max_w = max(img.width for _, img in panels)
    max_h = max(img.height for _, img in panels)

    sheet_w = cols * max_w
    sheet_h = rows * max_h
    sheet = Image.new("RGBA", (sheet_w, sheet_h), (0, 0, 0, 0))
    atlas = {}

    for idx, (name, img) in enumerate(panels):
        col = idx % cols
        row = idx // cols
        x = col * max_w
        y = row * max_h
        sheet.paste(img, (x, y))
        atlas[name] = {"x": x, "y": y, "w": img.width, "h": img.height}

    return sheet, atlas


# --- ChessMatch Presets ---

CHESSMATCH_PRESETS = {
    "scoreboard": {
        "size": (256, 64),
        "border": 4,
        "radius": 3,
        "fill": (40, 40, 60, 220),
        "border_color": (100, 100, 120, 255),
        "highlight": (255, 255, 255, 40),
        "shadow": (0, 0, 0, 60),
    },
    "powerup_slot": {
        "size": (48, 48),
        "border": 3,
        "radius": 0,
        "fill": (60, 55, 50, 240),
        "border_color": (140, 130, 110, 255),
        "highlight": (255, 255, 240, 50),
        "shadow": (0, 0, 0, 80),
    },
    "banner": {
        "size": (200, 40),
        "border": 3,
        "radius": 2,
        "fill": (50, 40, 20, 230),
        "border_color": (200, 170, 80, 255),
        "highlight": (255, 230, 140, 60),
        "shadow": (0, 0, 0, 70),
    },
    "popup": {
        "size": (180, 120),
        "border": 4,
        "radius": 6,
        "fill": (35, 35, 55, 235),
        "border_color": (120, 120, 150, 255),
        "highlight": (255, 255, 255, 45),
        "shadow": (0, 0, 0, 65),
    },
}


def get_presets(preset_group):
    """Get preset panels by group name.

    Args:
        preset_group: Name of preset group (e.g. 'chessmatch')

    Returns:
        Dict of {name: panel_kwargs}
    """
    groups = {
        "chessmatch": CHESSMATCH_PRESETS,
    }
    group = groups.get(preset_group.lower())
    if group is None:
        raise ValueError(f"Unknown preset group: {preset_group}. Available: {', '.join(groups)}")
    return group
