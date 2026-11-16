"""
Before/After Photo Processing Pipeline
--------------------------------------
Batch-processes photos for social media:
  1. Fixes orientation (EXIF) and applies light color correction
  2. Optionally removes the background (rembg) and places a brand-color backdrop
  3. Exports each photo in Instagram sizes (post 4:5, square 1:1, story 9:16)
  4. Builds a labeled before/after image for your portfolio

Usage:
    pip install pillow
    pip install "rembg[cpu]"          # only needed for --remove-bg
    python photo_pipeline.py --input photos --output results
    python photo_pipeline.py --input photos --output results --remove-bg --bg "#F2E3CF"
"""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

SIZES = {
    "post_4x5": (1080, 1350),
    "square_1x1": (1080, 1080),
    "story_9x16": (1080, 1920),
}
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def correct(img: Image.Image) -> Image.Image:
    """Orientation fix + gentle, natural-looking color correction."""
    img = ImageOps.exif_transpose(img).convert("RGB")
    img = ImageOps.autocontrast(img, cutoff=1)
    img = ImageEnhance.Color(img).enhance(1.10)
    img = ImageEnhance.Sharpness(img).enhance(1.15)
    return img


def replace_background(img: Image.Image, color: str) -> Image.Image:
    """Cut out the subject with rembg and place it on a solid color."""
    from rembg import remove  # imported here so the script works without rembg

    cutout = remove(img).convert("RGBA")
    backdrop = Image.new("RGBA", cutout.size, color)
    backdrop.alpha_composite(cutout)
    return backdrop.convert("RGB")


def export_sizes(img: Image.Image, stem: str, out_dir: Path) -> None:
    """Center-crop and resize to each social format."""
    for name, size in SIZES.items():
        fitted = ImageOps.fit(img, size, Image.LANCZOS, centering=(0.5, 0.5))
        fitted.save(out_dir / f"{stem}_{name}.jpg", quality=92)


def before_after(before: Image.Image, after: Image.Image, path: Path) -> None:
    """Side-by-side comparison with labels, for the portfolio."""
    height = 800
    b = ImageOps.contain(before, (height * 2, height))
    a = ImageOps.contain(after, (height * 2, height))
    gap, label_h = 20, 50
    canvas = Image.new("RGB", (b.width + a.width + gap, height + label_h), "white")
    canvas.paste(b, (0, label_h))
    canvas.paste(a, (b.width + gap, label_h))

    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 28)
    except OSError:
        font = ImageFont.load_default()
    draw.text((15, 8), "BEFORE", fill="black", font=font)
    draw.text((b.width + gap + 15, 8), "AFTER", fill="black", font=font)
    canvas.save(path, quality=92)


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch photo processing pipeline")
    parser.add_argument("--input", required=True, help="folder with original photos")
    parser.add_argument("--output", required=True, help="folder for results")
    parser.add_argument("--remove-bg", action="store_true", help="remove background")
    parser.add_argument("--bg", default="#F2E3CF", help="backdrop color if --remove-bg")
    args = parser.parse_args()

    in_dir, out_dir = Path(args.input), Path(args.output)
    exports = out_dir / "exports"
    compare = out_dir / "before_after"
    exports.mkdir(parents=True, exist_ok=True)
    compare.mkdir(parents=True, exist_ok=True)

    files = sorted(p for p in in_dir.iterdir() if p.suffix.lower() in EXTENSIONS)
    if not files:
        raise SystemExit(f"No images found in {in_dir}")

    for path in files:
        try:
            original = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
            result = correct(original)
            if args.remove_bg:
                result = replace_background(result, args.bg)
            export_sizes(result, path.stem, exports)
            before_after(original, result, compare / f"{path.stem}_compare.jpg")
            print(f"OK    {path.name}")
        except Exception as exc:  # keep the batch going if one file fails
            print(f"FAIL  {path.name}: {exc}")

    print(f"\nDone. {len(files)} file(s) processed -> {out_dir}")


if __name__ == "__main__":
    main()
