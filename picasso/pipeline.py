"""Config-driven pipeline orchestrator with optional folder watching."""

import os
import json
import time

from .common import load_image, save_image, make_output_dir, parse_color
from .slice import slice_grid, slice_by_cell_size, slice_auto
from .process import remove_background_color, remove_background_edge, clean_edges, quantize_colors
from .pack import pack_sprites, save_atlas_json, generate_godot_atlas


def _run_generate_step(images, args):
    """Run a generate step, returning list of (name, image) tuples."""
    from .generate import generate_image

    prompt = args.get("prompt", "")
    model = args.get("model", "gemini-2.5-flash-image")
    api_key = args.get("api_key")
    aspect_ratio = args.get("aspect_ratio")

    img = generate_image(
        prompt=prompt,
        api_key=api_key,
        model=model,
        aspect_ratio=aspect_ratio,
    )
    images.append(("generated", img))
    return images


def _run_slice_step(images, args):
    """Run a slice step, returning list of (name, image) tuples."""
    results = []
    for name, img in images:
        if args.get("auto"):
            bg = parse_color(args.get("bg_color", "#FFFFFF"))
            tolerance = args.get("tolerance", 30)
            tiles = slice_auto(img, bg_color=bg, tolerance=tolerance)
        elif "rows" in args and "cols" in args:
            tiles = slice_grid(img, args["rows"], args["cols"])
        elif "cell_w" in args and "cell_h" in args:
            tiles = slice_by_cell_size(img, args["cell_w"], args["cell_h"])
        else:
            tiles = [(name, img)]

        for tile_name, tile_img in tiles:
            results.append((f"{name}_{tile_name}", tile_img))
    return results


def _run_process_step(images, args):
    """Run processing operations on images."""
    results = []
    for name, img in images:
        if "remove_bg" in args:
            color = parse_color(args["remove_bg"])
            tolerance = args.get("tolerance", 30)
            img = remove_background_color(img, color=color, tolerance=tolerance)
        if args.get("remove_bg_edge"):
            threshold = args.get("edge_threshold", 20)
            img = remove_background_edge(img, threshold=threshold)
        if args.get("clean_edges"):
            threshold = args.get("alpha_threshold", 128)
            img = clean_edges(img, alpha_threshold=threshold)
        if "quantize" in args:
            n = args["quantize"]
            img = quantize_colors(img, n_colors=n)
        results.append((name, img))
    return results


def _run_pack_step(images, args, output_dir):
    """Pack images into a sprite sheet."""
    import tempfile

    # Save tiles to temp dir, then pack
    tmp_dir = tempfile.mkdtemp(prefix="picasso_pack_")
    paths = []
    for name, img in images:
        path = os.path.join(tmp_dir, f"{name}.png")
        save_image(img, path)
        paths.append(path)

    padding = args.get("padding", 0)
    po2 = args.get("power_of_2", False)
    sheet, atlas = pack_sprites(paths, padding=padding, power_of_2=po2)

    # Save outputs
    sheet_path = os.path.join(output_dir, "sheet.png")
    save_image(sheet, sheet_path)

    atlas_path = os.path.join(output_dir, "atlas.json")
    save_atlas_json(atlas, atlas_path)

    if args.get("godot"):
        godot_sheet = args.get("godot_sheet_path", "res://assets/sheet.png")
        godot_dir = os.path.join(output_dir, "atlas")
        generate_godot_atlas(atlas, godot_sheet, godot_dir)

    # Cleanup temp files
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)

    return [("sheet", sheet)]


def _run_panel_step(images, args):
    """Generate a panel and add it to the image list."""
    from .panel import generate_panel
    from .common import parse_size as _parse_size

    size = _parse_size(args.get("size", "256x64"))
    border = args.get("border", 4)
    radius = args.get("radius", 0)
    fill = parse_color(args["fill"]) if "fill" in args else (40, 40, 60, 220)
    border_color = parse_color(args["border_color"]) if "border_color" in args else (180, 180, 200, 255)
    highlight = parse_color(args["highlight"]) if "highlight" in args else None
    shadow = parse_color(args["shadow"]) if "shadow" in args else None

    panel = generate_panel(
        size=size, border=border, radius=radius,
        fill=fill, border_color=border_color,
        highlight=highlight, shadow=shadow,
    )

    name = args.get("name", "panel")
    images.append((name, panel))
    return images


def run_pipeline(config, input_path=None):
    """Execute a pipeline from a config dict.

    Config format:
        {
            "input": "./raw/",
            "steps": [
                {"op": "slice", "args": {...}},
                {"op": "process", "args": {...}},
                {"op": "pack", "args": {...}}
            ],
            "output": "./game_assets/"
        }

    Args:
        config: Pipeline config dict
        input_path: Override for config's input path
    """
    input_dir = input_path or config.get("input", ".")
    output_dir = config.get("output", "./output")
    make_output_dir(output_dir)

    # Check if first step is generate (no input files needed)
    steps = config.get("steps", [])
    has_generate_first = steps and steps[0].get("op") == "generate"

    # Skip generate step when input is provided manually
    if has_generate_first and input_path:
        steps = steps[1:]
        config = dict(config, steps=steps)
        has_generate_first = False

    # Load input images
    images = []
    if has_generate_first:
        # Generate step will produce images, skip loading
        pass
    elif os.path.isfile(input_dir):
        img = load_image(input_dir)
        name = os.path.splitext(os.path.basename(input_dir))[0]
        images.append((name, img))
    elif os.path.isdir(input_dir):
        for f in sorted(os.listdir(input_dir)):
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                img = load_image(os.path.join(input_dir, f))
                name = os.path.splitext(f)[0]
                images.append((name, img))

    if not images and not has_generate_first:
        print(f"No images found in {input_dir}")
        return

    print(f"Loaded {len(images)} image(s)")

    # Execute steps
    for i, step in enumerate(config.get("steps", [])):
        op = step["op"]
        args = step.get("args", {})
        print(f"Step {i+1}: {op}")

        if op == "generate":
            images = _run_generate_step(images, args)
        elif op == "slice":
            images = _run_slice_step(images, args)
        elif op == "process":
            images = _run_process_step(images, args)
        elif op == "panel":
            images = _run_panel_step(images, args)
        elif op == "pack":
            images = _run_pack_step(images, args, output_dir)
        else:
            print(f"  Unknown operation: {op}")
            continue

        print(f"  → {len(images)} image(s)")

    # Save any remaining individual images (if last step wasn't pack)
    if images and config.get("steps", [])[-1]["op"] != "pack":
        sprites_dir = os.path.join(output_dir, "sprites")
        make_output_dir(sprites_dir)
        for name, img in images:
            save_image(img, os.path.join(sprites_dir, f"{name}.png"))
        print(f"Saved {len(images)} sprites to {sprites_dir}")

    print("Pipeline complete.")


def run_pipeline_file(config_path, input_path=None):
    """Load and run a pipeline from a JSON config file."""
    with open(config_path) as f:
        config = json.load(f)
    run_pipeline(config, input_path)


def watch_folder(watch_dir, config, poll_interval=1.0):
    """Watch a directory for new images and auto-process them.

    Uses watchdog if available, falls back to polling.

    Args:
        watch_dir: Directory to watch
        config: Pipeline config dict
        poll_interval: Seconds between poll checks (fallback mode)
    """
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler

        class Handler(FileSystemEventHandler):
            def on_created(self, event):
                if event.is_directory:
                    return
                ext = os.path.splitext(event.src_path)[1].lower()
                if ext in (".png", ".jpg", ".jpeg", ".webp"):
                    print(f"New file: {event.src_path}")
                    time.sleep(0.5)  # Wait for file write to finish
                    run_pipeline(config, input_path=event.src_path)

        observer = Observer()
        observer.schedule(Handler(), watch_dir, recursive=False)
        observer.start()
        print(f"Watching {watch_dir} for new images (Ctrl+C to stop)")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()

    except ImportError:
        # Fallback: simple polling
        print(f"Watching {watch_dir} (polling, install watchdog for better performance)")
        seen = set(os.listdir(watch_dir))
        try:
            while True:
                time.sleep(poll_interval)
                current = set(os.listdir(watch_dir))
                new_files = current - seen
                for f in sorted(new_files):
                    ext = os.path.splitext(f)[1].lower()
                    if ext in (".png", ".jpg", ".jpeg", ".webp"):
                        path = os.path.join(watch_dir, f)
                        print(f"New file: {path}")
                        run_pipeline(config, input_path=path)
                seen = current
        except KeyboardInterrupt:
            pass
    print("Watch stopped.")
