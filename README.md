# Picasso

AI image to game-ready 2D asset pipeline. Slice sprite sheets, remove backgrounds, generate text tiles, build UI panels, and pack everything into optimized sprite sheets — all from the command line.

## Setup

```bash
pip install -r requirements.txt
```

For AI image generation, set your Gemini API key:

```bash
export GEMINI_API_KEY=your_key_here
```

## Commands

### slice — Split sprite sheets into tiles

```bash
# Auto-detect tile boundaries
python3 cli.py slice input.png -o ./sprites --auto --bg-color "#FFFFFF"

# Grid-based slicing
python3 cli.py slice input.png -o ./sprites --rows 3 --cols 3

# Cell size slicing
python3 cli.py slice input.png -o ./sprites --cell-size 32x32
```

### process — Post-process sprites

```bash
# Remove white background
python3 cli.py process sprite.png -o clean.png --remove-bg "#FFFFFF"

# Edge-based background removal + clean alpha edges
python3 cli.py process sprite.png -o clean.png --remove-bg-edge --clean-edges

# Batch process a directory
python3 cli.py process ./sprites/ -o ./processed/ --batch --remove-bg "#FFFFFF"

# Reduce colors and resize
python3 cli.py process sprite.png -o small.png --quantize 16 --resize 2x
```

### text — Generate text tile sprites

```bash
python3 cli.py text -o ./text_tiles \
  --font ./fonts/pixel.ttf --font-size 16 \
  --tile-size 32x32 --cols 16 \
  --fg "#FFFFFF" --outline "#000000" --shadow "#00000080"
```

### panel — Generate 9-slice UI panels

```bash
# Single panel
python3 cli.py panel -o ./panel.png \
  --size 256x64 --border 4 --radius 3 \
  --fill "#28283CDD" --border-color "#B4B4C8" \
  --highlight "#FFFFFF40" --shadow "#00000060"

# Panel + 9-slice pieces for engine-side stretching
python3 cli.py panel -o ./panel_parts/ \
  --size 48x48 --border 3 --nine-slice

# Generate preset panel sets
python3 cli.py panel -o ./ui_panels/ --presets chessmatch
```

### pack — Pack sprites into a sheet

```bash
python3 cli.py pack ./sprites/ -o sheet.png \
  --atlas atlas.json --padding 1 --power-of-2

# With Godot AtlasTexture .tres files
python3 cli.py pack ./sprites/ -o sheet.png \
  --atlas atlas.json --godot --godot-sheet-path "res://assets/sheet.png"
```

### generate — AI image generation (Gemini)

```bash
python3 cli.py generate "16x16 pixel art treasure chest, transparent background" \
  -o chest.png

# Generate and pipe into a processing pipeline
python3 cli.py generate "pixel art character sprite sheet" \
  -o ./output/character.png --pipeline pipeline.json
```

### pipeline — Config-driven batch processing

```bash
# Run a pipeline config
python3 cli.py pipeline config.json --input ./raw/sheet.png

# Watch a folder for new images
python3 cli.py pipeline config.json --watch --watch-dir ./incoming/
```

Pipeline config example:

```json
{
  "input": "./raw/",
  "steps": [
    { "op": "slice", "args": { "auto": true, "bg_color": "#FFFFFF" } },
    {
      "op": "process",
      "args": { "remove_bg": "#FFFFFF", "clean_edges": true }
    },
    { "op": "pack", "args": { "padding": 1, "power_of_2": true } }
  ],
  "output": "./game_assets/"
}
```

Available pipeline operations: `generate`, `slice`, `process`, `panel`, `pack`

## Color Format

All color arguments accept hex strings with optional alpha:

- `#RRGGBB` — e.g. `#FF0000` (red, fully opaque)
- `#RRGGBBAA` — e.g. `#FF000080` (red, 50% transparent)

## Project Structure

```
picasso/
├── cli.py              # CLI entry point
├── picasso/
│   ├── common.py       # Shared utilities (color parsing, image I/O)
│   ├── slice.py        # Sprite sheet slicing (grid, cell, auto-detect)
│   ├── process.py      # Background removal, edge cleanup, quantize
│   ├── text_tiles.py   # Text glyph rendering with outlines/shadows
│   ├── panel.py        # 9-slice UI panel generation
│   ├── pack.py         # Sprite sheet packing with atlas output
│   ├── generate.py     # AI image generation (Gemini)
│   └── pipeline.py     # Config-driven pipeline orchestrator
├── examples/           # Example pipeline configs
└── requirements.txt
```
