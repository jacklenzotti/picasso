"""Grid slicing + auto-detect boundaries for sprite sheets."""

from PIL import Image
from .common import is_empty_tile, parse_color


def slice_grid(image, rows, cols, skip_empty=True):
    """Slice image into a fixed grid of rows x cols. Returns list of (name, image) tuples."""
    cell_w = image.width // cols
    cell_h = image.height // rows
    tiles = []
    for r in range(rows):
        for c in range(cols):
            x = c * cell_w
            y = r * cell_h
            tile = image.crop((x, y, x + cell_w, y + cell_h))
            if skip_empty and is_empty_tile(tile):
                continue
            name = f"tile_r{r}_c{c}"
            tiles.append((name, tile))
    return tiles


def slice_by_cell_size(image, cell_w, cell_h, skip_empty=True):
    """Slice image by fixed cell dimensions. Returns list of (name, image) tuples."""
    cols = image.width // cell_w
    rows = image.height // cell_h
    tiles = []
    for r in range(rows):
        for c in range(cols):
            x = c * cell_w
            y = r * cell_h
            tile = image.crop((x, y, x + cell_w, y + cell_h))
            if skip_empty and is_empty_tile(tile):
                continue
            name = f"tile_r{r}_c{c}"
            tiles.append((name, tile))
    return tiles


def _find_gaps(projection, min_gap=2):
    """Find gaps (runs of zeros) in a 1D projection array.
    Returns list of (start, end) tuples marking gap boundaries."""
    gaps = []
    in_gap = False
    gap_start = 0
    for i, val in enumerate(projection):
        if val == 0:
            if not in_gap:
                in_gap = True
                gap_start = i
        else:
            if in_gap:
                if i - gap_start >= min_gap:
                    gaps.append((gap_start, i))
                in_gap = False
    if in_gap and len(projection) - gap_start >= min_gap:
        gaps.append((gap_start, len(projection)))
    return gaps


def _project_axis(image, bg_color, tolerance, axis):
    """Project pixel differences from bg_color onto one axis.
    axis=0 projects onto X (column sums), axis=1 projects onto Y (row sums).
    Returns a list of values where 0 means 'all background'."""
    w, h = image.size
    pixels = image.load()

    if axis == 0:
        # Sum each column
        projection = []
        for x in range(w):
            col_sum = 0
            for y in range(h):
                px = pixels[x, y]
                if not _pixel_matches_bg(px, bg_color, tolerance):
                    col_sum += 1
            projection.append(col_sum)
    else:
        # Sum each row
        projection = []
        for y in range(h):
            row_sum = 0
            for x in range(w):
                px = pixels[x, y]
                if not _pixel_matches_bg(px, bg_color, tolerance):
                    row_sum += 1
            projection.append(row_sum)
    return projection


def _pixel_matches_bg(px, bg_color, tolerance):
    """Check if a pixel matches the background color within tolerance."""
    # Handle alpha: if pixel is fully transparent, it's background
    if len(px) == 4 and px[3] < 10:
        return True
    for i in range(min(len(bg_color), 3)):
        if abs(px[i] - bg_color[i]) > tolerance:
            return False
    return True


def _gaps_to_splits(gaps, total_size):
    """Convert gap positions to split ranges (content regions between gaps).
    Returns list of (start, end) for each content strip."""
    splits = []
    prev_end = 0
    for gap_start, gap_end in gaps:
        if gap_start > prev_end:
            splits.append((prev_end, gap_start))
        prev_end = gap_end
    if prev_end < total_size:
        splits.append((prev_end, total_size))
    return splits


def slice_auto(image, bg_color=(255, 255, 255), tolerance=30, min_gap=2, skip_empty=True):
    """Auto-detect sprite boundaries by projecting pixel values onto X/Y axes.

    Finds runs of background-only pixels (gaps) and uses them as grid lines.
    Works well for AI-generated grid images with consistent backgrounds.

    Args:
        image: PIL Image (RGBA)
        bg_color: Background color as (R, G, B) tuple
        tolerance: Color matching tolerance (0-255)
        min_gap: Minimum gap width in pixels to count as a separator
        skip_empty: Skip tiles that are entirely empty

    Returns:
        List of (name, image) tuples.
    """
    # Project onto X and Y axes
    x_proj = _project_axis(image, bg_color, tolerance, axis=0)
    y_proj = _project_axis(image, bg_color, tolerance, axis=1)

    # Find gaps
    x_gaps = _find_gaps(x_proj, min_gap)
    y_gaps = _find_gaps(y_proj, min_gap)

    # Convert gaps to content regions
    col_splits = _gaps_to_splits(x_gaps, image.width)
    row_splits = _gaps_to_splits(y_gaps, image.height)

    # If no gaps found, return the whole image
    if not col_splits:
        col_splits = [(0, image.width)]
    if not row_splits:
        row_splits = [(0, image.height)]

    tiles = []
    for r_idx, (y1, y2) in enumerate(row_splits):
        for c_idx, (x1, x2) in enumerate(col_splits):
            tile = image.crop((x1, y1, x2, y2))
            if skip_empty and is_empty_tile(tile):
                continue
            name = f"tile_r{r_idx}_c{c_idx}"
            tiles.append((name, tile))

    return tiles
