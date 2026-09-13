from PIL import Image
import os
from pathlib import Path


def _ensure_dir(path):
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


def optimize_image_from_file(file_like, dest_path, max_size=(800, 800), quality=80):
    """Open an uploaded file-like object (e.g. Werkzeug FileStorage) and save an optimized JPEG.

    - resizes with thumbnail() to keep aspect ratio up to max_size
    - converts alpha/PNG to RGB with white background
    - saves as JPEG with given quality and optimize=True
    """
    try:
        img = Image.open(file_like)
    except Exception:
        _ensure_dir(dest_path)
        Image.new('RGB', (1, 1), (255, 255, 255)).save(dest_path, format='JPEG', quality=quality)
        return
    img.convert('RGBA')
    img.thumbnail(max_size, Image.LANCZOS)

    if img.mode in ("RGBA", "LA") or (img.mode == "P" and 'transparency' in img.info):
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "RGBA":
            background.paste(img, mask=img.split()[3])
        else:
            background.paste(img)
        out = background
    else:
        out = img.convert('RGB')

    _ensure_dir(dest_path)
    out.save(dest_path, format='JPEG', quality=quality, optimize=True)


def optimize_image_from_path(src_path, dest_path=None, max_size=(800, 800), quality=80):
    src_path = str(src_path)
    if dest_path is None:
        dest_path = src_path
    _ensure_dir(dest_path)
    with open(src_path, 'rb') as fh:
        optimize_image_from_file(fh, dest_path, max_size=max_size, quality=quality)


def resize_and_pad_image(src_path, dest_path, size=(55, 55), quality=80, bgcolor=(255, 255, 255)):
    """Resize image keeping aspect ratio and pad to exact `size` with `bgcolor` then save as JPEG."""
    img = Image.open(src_path)
    img.thumbnail(size, Image.LANCZOS)

    if img.mode in ("RGBA", "LA") or (img.mode == "P" and 'transparency' in img.info):
        img = img.convert('RGBA')
        base = Image.new('RGB', size, bgcolor)
        paste_pos = ((size[0] - img.width) // 2, (size[1] - img.height) // 2)
        base.paste(img, paste_pos, mask=img.split()[3] if img.mode == 'RGBA' else None)
        out = base
    else:
        base = Image.new('RGB', size, bgcolor)
        paste_pos = ((size[0] - img.width) // 2, (size[1] - img.height) // 2)
        base.paste(img.convert('RGB'), paste_pos)
        out = base

    _ensure_dir(dest_path)
    out.save(dest_path, format='JPEG', quality=quality, optimize=True)
