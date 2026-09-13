#!/usr/bin/env python3
"""One-time script to optimize existing uploaded images and resize logos.

Usage:
    python scripts/optimize_uploads.py
"""
import os
import sys

# Ensure project root is on sys.path so `from app import ...` works when the
# script is run directly from the repository root or a different cwd.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import Config
from app.utils import save_optimized_image, save_resized_png


def optimize_uploads():
    upload_folder = Config.UPLOAD_FOLDER
    if not os.path.isdir(upload_folder):
        print(f"Upload folder not found: {upload_folder}")
        return
    exts = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp'}
    for fname in os.listdir(upload_folder):
        path = os.path.join(upload_folder, fname)
        if not os.path.isfile(path):
            continue
        base, ext = os.path.splitext(fname)
        if ext.lower() not in exts:
            continue
        new_fname = f"{base}.jpg"
        dest = os.path.join(upload_folder, new_fname)
        try:
            with open(path, 'rb') as f:
                save_optimized_image(f, dest, max_size=(800, 800), quality=80)
            if os.path.abspath(dest) != os.path.abspath(path):
                try:
                    os.remove(path)
                except Exception:
                    pass
            print(f"Optimized: {fname} -> {new_fname}")
        except Exception as e:
            print(f"Failed to optimize {fname}: {e}")


def resize_logos():
    # images directory sits one level above uploads
    images_dir = os.path.normpath(os.path.join(Config.UPLOAD_FOLDER, os.pardir))
    logo = os.path.join(images_dir, 'logo.png')
    logo_text = os.path.join(images_dir, 'logo_text.png')
    if os.path.exists(logo):
        try:
            save_resized_png(logo, logo, (55, 55))
            print("Resized logo.png to 55x55")
        except Exception as e:
            print("Failed resizing logo.png:", e)
    else:
        print(f"logo.png not found at {logo}")

    if os.path.exists(logo_text):
        try:
            save_resized_png(logo_text, logo_text, (120, 60))
            print("Resized logo_text.png to 120x60")
        except Exception as e:
            print("Failed resizing logo_text.png:", e)
    else:
        print(f"logo_text.png not found at {logo_text}")


def main():
    optimize_uploads()
    resize_logos()
    print("Done.")


if __name__ == '__main__':
    main()
