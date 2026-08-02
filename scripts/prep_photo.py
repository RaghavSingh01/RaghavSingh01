#!/usr/bin/env python3
"""
prep_photo.py — turn a normal portrait photo into a clean, high-contrast
grayscale image that's ready for ASCII conversion.

Pipeline:
  1. Remove the background (rembg) so only the subject remains.
  2. Boost local contrast with CLAHE so a flatly-lit face gets real
     highlights and shadows (this is what makes the ASCII art readable).
  3. Composite onto pure white so the background maps to the blank end
     of the ASCII ramp (white -> space character).

Usage:
    python scripts/prep_photo.py source-photo.jpg
Output:
    source-prepped.png (grayscale, same folder as this script's parent)
"""
import sys
import os
import numpy as np
import cv2
from PIL import Image
from rembg import remove


def prep_photo(input_path: str, output_path: str) -> None:
    print(f"[1/3] Loading {input_path} ...")
    with open(input_path, "rb") as f:
        input_bytes = f.read()

    print("[2/3] Removing background (rembg) ...")
    # Returns RGBA PNG bytes with background made transparent
    result_bytes = remove(input_bytes)
    rgba = Image.open(__import__("io").BytesIO(result_bytes)).convert("RGBA")

    # Composite onto solid white background first, so any semi-transparent
    # edge pixels (hair, glasses rim) blend to white instead of black.
    white_bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    composited = Image.alpha_composite(white_bg, rgba).convert("RGB")

    print("[3/3] Boosting local contrast (CLAHE) and converting to grayscale ...")
    arr = np.array(composited)
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

    # CLAHE: contrast-limited adaptive histogram equalization.
    # This is what gives a flat, evenly-lit face real highlights/shadows
    # instead of the ASCII output looking like a dark, unreadable blob.
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    equalized = clahe.apply(gray)

    # Re-mask: force pixels that were transparent (background) back to
    # pure white, since CLAHE can otherwise drag near-white background
    # noise into mid-gray values.
    alpha = np.array(rgba)[:, :, 3]
    equalized[alpha < 10] = 255

    out_img = Image.fromarray(equalized)
    out_img.save(output_path)
    print(f"Done -> {output_path}  ({out_img.size[0]}x{out_img.size[1]})")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/prep_photo.py <source-photo.jpg>")
        sys.exit(1)

    src = sys.argv[1]
    base = os.path.splitext(os.path.basename(src))[0]
    out = os.path.join(os.path.dirname(src) or ".", f"{base}-prepped.png")
    prep_photo(src, out)
