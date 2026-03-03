#!/usr/bin/env python3
"""Picasso: AI Image → Game-Ready 2D Asset Pipeline CLI."""

import argparse
import json
import os
import sys

from picasso.common import load_image, save_image, make_output_dir, parse_color, parse_size, scale_nearest


def cmd_slice(args):
    """Handle the 'slice' subcommand."""
    from picasso.slice import slice_grid, slice_by_cell_size, slice_auto

    img = load_image(args.input)
    out_dir = make_output_dir(args.output)

    if args.auto:
        bg = parse_color(args.bg_color) if args.bg_color else (255, 255, 255)
        tiles = slice_auto(img, bg_color=bg, tolerance=args.tolerance, min_gap=args.min_gap)
        mode = "auto"
    elif args.cell_size:
        w, h = parse_size(args.cell_size)
        tiles = slice_by_cell_size(img, w, h, skip_empty=not args.keep_empty)
        mode = f"cell {w}x{h}"
    elif args.rows and args.cols:
        tiles = slice_grid(img, args.rows, args.cols, skip_empty=not args.keep_empty)
        mode = f"grid {args.rows}x{args.cols}"
    else:
        print("Error: specify --auto, --cell-size, or --rows/--cols", file=sys.stderr)
        sys.exit(1)

    for name, tile in tiles:
        save_image(tile, os.path.join(out_dir, f"{name}.png"))

    print(f"Sliced ({mode}): {len(tiles)} tiles → {out_dir}")


def cmd_process(args):
    """Handle the 'process' subcommand."""
    from picasso.process import (
        remove_background_color, remove_background_edge,
        clean_edges, quantize_colors, batch_process
    )

    out = args.output

    # Build operation list
    operations = []
    if args.remove_bg:
        color = parse_color(args.remove_bg)
        operations.append((remove_background_color, {"color": color, "tolerance": args.tolerance}))
    if args.remove_bg_edge:
        operations.append((remove_background_edge, {"threshold": args.tolerance}))
    if args.clean_edges:
        operations.append((clean_edges, {"alpha_threshold": args.alpha_threshold}))
    if args.quantize:
        operations.append((quantize_colors, {"n_colors": args.quantize}))

    if not operations:
        print("Error: specify at least one processing operation", file=sys.stderr)
        sys.exit(1)

    input_path = args.input

    if args.batch or os.path.isdir(input_path):
        # Batch mode
        out_dir = make_output_dir(out)
        results = batch_process(input_path, out_dir, operations)
        print(f"Processed {len(results)} files → {out_dir}")
    else:
        # Single file
        img = load_image(input_path)
        for func, kwargs in operations:
            img = func(img, **kwargs)

        # Handle resize
        if args.resize:
            if args.resize.endswith("x"):
                factor = float(args.resize[:-1])
                img = scale_nearest(img, factor)
            else:
                w, h = parse_size(args.resize)
                from picasso.common import resize_to
                img = resize_to(img, w, h)

        save_image(img, out)
        print(f"Processed → {out}")


def cmd_text(args):
    """Handle the 'text' subcommand."""
    from picasso.text_tiles import generate_text_sheet, generate_charset
    import json as json_mod

    tile_size = parse_size(args.tile_size)
    fg = parse_color(args.fg) if args.fg else (255, 255, 255)
    outline = parse_color(args.outline) if args.outline else None
    shadow = parse_color(args.shadow) if args.shadow else None

    out_dir = make_output_dir(args.output)
    sheet_path = os.path.join(out_dir, "text_sheet.png")

    sheet, atlas = generate_text_sheet(
        chars=args.chars,
        tile_size=tile_size,
        cols=args.cols,
        font_path=args.font,
        font_size=args.font_size,
        fg=fg,
        outline=outline,
        shadow=shadow,
        output_path=sheet_path,
    )

    atlas_path = os.path.join(out_dir, "text_atlas.json")
    with open(atlas_path, "w") as f:
        json_mod.dump(atlas, f, indent=2)

    # Also save individual tiles if requested
    if args.individual:
        tiles_dir = make_output_dir(os.path.join(out_dir, "tiles"))
        tiles = generate_charset(
            chars=args.chars,
            tile_size=tile_size,
            font_path=args.font,
            font_size=args.font_size,
            fg=fg,
            outline=outline,
            shadow=shadow,
        )
        for char, tile in tiles:
            safe_name = f"char_{ord(char):04d}"
            save_image(tile, os.path.join(tiles_dir, f"{safe_name}.png"))

    print(f"Text sheet ({len(atlas)} chars) → {sheet_path}")
    print(f"Atlas → {atlas_path}")


def cmd_pack(args):
    """Handle the 'pack' subcommand."""
    from picasso.pack import pack_directory, save_atlas_json, generate_godot_atlas

    sheet, atlas = pack_directory(
        args.input,
        args.output,
        padding=args.padding,
        power_of_2=args.power_of_2,
    )

    if args.atlas:
        save_atlas_json(atlas, args.atlas)
        print(f"Atlas → {args.atlas}")

    if args.godot:
        godot_dir = os.path.splitext(args.output)[0] + "_atlas"
        sheet_res_path = args.godot_sheet_path or f"res://{args.output}"
        generate_godot_atlas(atlas, sheet_res_path, godot_dir)
        print(f"Godot .tres → {godot_dir}/")

    print(f"Packed {len(atlas)} sprites → {args.output} ({sheet.width}x{sheet.height})")


def cmd_generate(args):
    """Handle the 'generate' subcommand."""
    from picasso.generate import generate_image

    try:
        img = generate_image(
            prompt=args.prompt,
            api_key=args.api_key,
            model=args.model,
            aspect_ratio=args.aspect_ratio,
            save_path=args.output,
        )
    except (ValueError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        err = str(e)
        if "429" in err or "RESOURCE_EXHAUSTED" in err:
            print("Error: Rate limit exceeded. Wait a minute and try again.", file=sys.stderr)
            sys.exit(1)
        raise

    if args.pipeline:
        # Chain into a pipeline config
        from picasso.pipeline import run_pipeline
        with open(args.pipeline) as f:
            config = json.load(f)
        # Skip any generate step in the config (we already have the image)
        steps = [s for s in config.get("steps", []) if s["op"] != "generate"]
        config["steps"] = steps
        # Use -o as output dir if provided, otherwise config's output
        if args.output:
            output_dir = os.path.dirname(args.output) or config.get("output", "./output")
            config["output"] = output_dir

        # Run pipeline with the generated image injected
        from picasso.common import make_output_dir
        output_dir = config.get("output", "./output")
        make_output_dir(output_dir)

        images = [("generated", img)]
        print(f"Generated image, running pipeline ({len(steps)} steps)...")

        for i, step in enumerate(steps):
            op = step["op"]
            step_args = step.get("args", {})
            print(f"Step {i+1}: {op}")

            if op == "slice":
                from picasso.pipeline import _run_slice_step
                images = _run_slice_step(images, step_args)
            elif op == "process":
                from picasso.pipeline import _run_process_step
                images = _run_process_step(images, step_args)
            elif op == "panel":
                from picasso.pipeline import _run_panel_step
                images = _run_panel_step(images, step_args)
            elif op == "pack":
                from picasso.pipeline import _run_pack_step
                images = _run_pack_step(images, step_args, output_dir)

            print(f"  → {len(images)} image(s)")

        # Save remaining images if last step wasn't pack
        if images and steps and steps[-1]["op"] != "pack":
            sprites_dir = os.path.join(output_dir, "sprites")
            make_output_dir(sprites_dir)
            for name, tile in images:
                from picasso.common import save_image
                save_image(tile, os.path.join(sprites_dir, f"{name}.png"))
            print(f"Saved {len(images)} sprites to {sprites_dir}")

        print("Pipeline complete.")
    else:
        if not args.output:
            print("Generated image (use -o to save to disk)")
        print(f"Image size: {img.width}x{img.height}")


def cmd_panel(args):
    """Handle the 'panel' subcommand."""
    from picasso.panel import generate_panel, slice_nine, get_presets

    out = args.output

    if args.presets:
        # Generate all panels in a preset group
        presets = get_presets(args.presets)
        out_dir = make_output_dir(out)
        for name, kwargs in presets.items():
            panel = generate_panel(**kwargs)
            save_image(panel, os.path.join(out_dir, f"{name}.png"))

            if args.nine_slice:
                nine_dir = make_output_dir(os.path.join(out_dir, name))
                pieces = slice_nine(panel, kwargs["border"])
                for piece_name, piece_img in pieces:
                    save_image(piece_img, os.path.join(nine_dir, f"{piece_name}.png"))

        print(f"Generated {len(presets)} preset panels → {out_dir}")
        return

    # Single panel from CLI args
    w, h = parse_size(args.size)
    fill = parse_color(args.fill) if args.fill else (40, 40, 60, 220)
    border_color = parse_color(args.border_color) if args.border_color else (180, 180, 200, 255)
    highlight = parse_color(args.highlight) if args.highlight else None
    shadow = parse_color(args.shadow) if args.shadow else None

    panel = generate_panel(
        size=(w, h),
        border=args.border,
        radius=args.radius,
        fill=fill,
        border_color=border_color,
        highlight=highlight,
        shadow=shadow,
    )

    if args.nine_slice:
        out_dir = make_output_dir(out)
        save_image(panel, os.path.join(out_dir, "panel.png"))
        pieces = slice_nine(panel, args.border)
        for piece_name, piece_img in pieces:
            save_image(piece_img, os.path.join(out_dir, f"{piece_name}.png"))
        print(f"Panel {w}x{h} + 9 slices → {out_dir}")
    else:
        save_image(panel, out)
        print(f"Panel {w}x{h} → {out}")


def cmd_pipeline(args):
    """Handle the 'pipeline' subcommand."""
    from picasso.pipeline import run_pipeline_file, watch_folder

    if args.watch:
        import json as json_mod
        with open(args.config) as f:
            config = json_mod.load(f)
        watch_dir = args.watch_dir or config.get("input", ".")
        watch_folder(watch_dir, config)
    else:
        run_pipeline_file(args.config, input_path=args.input)


def main():
    parser = argparse.ArgumentParser(
        prog="picasso",
        description="AI Image → Game-Ready 2D Asset Pipeline",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- slice ---
    p_slice = subparsers.add_parser("slice", help="Slice sprite sheets into individual tiles")
    p_slice.add_argument("input", help="Input image path")
    p_slice.add_argument("-o", "--output", default="./sprites", help="Output directory")
    p_slice.add_argument("--rows", type=int, help="Grid rows")
    p_slice.add_argument("--cols", type=int, help="Grid columns")
    p_slice.add_argument("--cell-size", help="Cell size (e.g. 32x32)")
    p_slice.add_argument("--auto", action="store_true", help="Auto-detect boundaries")
    p_slice.add_argument("--bg-color", help="Background color for auto mode (e.g. #FFFFFF)")
    p_slice.add_argument("--tolerance", type=int, default=30, help="Color tolerance (0-255)")
    p_slice.add_argument("--min-gap", type=int, default=2, help="Minimum gap width for auto mode")
    p_slice.add_argument("--keep-empty", action="store_true", help="Keep empty tiles")
    p_slice.set_defaults(func=cmd_slice)

    # --- process ---
    p_proc = subparsers.add_parser("process", help="Post-process sprites")
    p_proc.add_argument("input", help="Input image or directory")
    p_proc.add_argument("-o", "--output", default="./processed", help="Output path")
    p_proc.add_argument("--batch", action="store_true", help="Process all PNGs in directory")
    p_proc.add_argument("--remove-bg", help="Remove background color (e.g. #FFFFFF)")
    p_proc.add_argument("--remove-bg-edge", action="store_true", help="Flood-fill BG removal from edges")
    p_proc.add_argument("--clean-edges", action="store_true", help="Threshold alpha for crisp edges")
    p_proc.add_argument("--alpha-threshold", type=int, default=128, help="Alpha threshold (0-255)")
    p_proc.add_argument("--quantize", type=int, help="Reduce to N colors")
    p_proc.add_argument("--resize", help="Resize (e.g. 2x for scale, or 64x64 for exact)")
    p_proc.add_argument("--tolerance", type=int, default=30, help="Color tolerance (0-255)")
    p_proc.set_defaults(func=cmd_process)

    # --- text ---
    p_text = subparsers.add_parser("text", help="Generate text tile sprites")
    p_text.add_argument("-o", "--output", default="./text_tiles", help="Output directory")
    p_text.add_argument("--font", help="Path to .ttf font file")
    p_text.add_argument("--font-size", type=int, help="Font size in pixels")
    p_text.add_argument("--tile-size", default="32x32", help="Tile size (e.g. 32x32)")
    p_text.add_argument("--cols", type=int, default=16, help="Columns in sheet")
    p_text.add_argument("--chars", help="Characters to render (default: A-Z, 0-9, symbols)")
    p_text.add_argument("--fg", help="Foreground color (e.g. #FFFFFF)")
    p_text.add_argument("--outline", help="Outline color (e.g. #000000)")
    p_text.add_argument("--shadow", help="Shadow color (e.g. #00000080)")
    p_text.add_argument("--individual", action="store_true", help="Also save individual tile PNGs")
    p_text.set_defaults(func=cmd_text)

    # --- pack ---
    p_pack = subparsers.add_parser("pack", help="Pack sprites into a sheet")
    p_pack.add_argument("input", help="Input directory of sprites")
    p_pack.add_argument("-o", "--output", default="sheet.png", help="Output sheet path")
    p_pack.add_argument("--atlas", help="Output atlas JSON path")
    p_pack.add_argument("--godot", action="store_true", help="Generate Godot .tres AtlasTexture files")
    p_pack.add_argument("--godot-sheet-path", help="Godot res:// path for the sheet texture")
    p_pack.add_argument("--padding", type=int, default=0, help="Pixels between sprites")
    p_pack.add_argument("--power-of-2", action="store_true", help="Round to power-of-2 dimensions")
    p_pack.set_defaults(func=cmd_pack)

    # --- generate ---
    p_gen = subparsers.add_parser("generate", help="Generate an image with Gemini AI")
    p_gen.add_argument("prompt", help="Text prompt for image generation")
    p_gen.add_argument("-o", "--output", help="Output image path")
    p_gen.add_argument("--model", default="gemini-2.5-flash-image", help="Gemini model")
    p_gen.add_argument("--aspect-ratio", help="Aspect ratio (e.g. 1:1, 16:9)")
    p_gen.add_argument("--api-key", help="Gemini API key (or set GEMINI_API_KEY)")
    p_gen.add_argument("--pipeline", help="Pipeline config JSON to chain into")
    p_gen.set_defaults(func=cmd_generate)

    # --- panel ---
    p_panel = subparsers.add_parser("panel", help="Generate 9-slice UI panel sprites")
    p_panel.add_argument("-o", "--output", default="./panel_out", help="Output path (file or directory)")
    p_panel.add_argument("--size", default="256x64", help="Panel dimensions (e.g. 256x64)")
    p_panel.add_argument("--border", type=int, default=4, help="Border thickness in pixels")
    p_panel.add_argument("--radius", type=int, default=0, help="Corner radius")
    p_panel.add_argument("--fill", help="Interior fill color (e.g. #28283CDD)")
    p_panel.add_argument("--border-color", help="Border color (e.g. #B4B4C8FF)")
    p_panel.add_argument("--highlight", help="Top/left bevel highlight color")
    p_panel.add_argument("--shadow", help="Bottom/right bevel shadow color")
    p_panel.add_argument("--nine-slice", action="store_true", help="Also output 9 individual pieces")
    p_panel.add_argument("--presets", help="Generate preset panels (e.g. chessmatch)")
    p_panel.set_defaults(func=cmd_panel)

    # --- pipeline ---
    p_pipe = subparsers.add_parser("pipeline", help="Run a config-driven pipeline")
    p_pipe.add_argument("config", help="Pipeline config JSON file")
    p_pipe.add_argument("--input", help="Override input path")
    p_pipe.add_argument("--watch", action="store_true", help="Watch folder for new images")
    p_pipe.add_argument("--watch-dir", help="Directory to watch (overrides config input)")
    p_pipe.set_defaults(func=cmd_pipeline)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
