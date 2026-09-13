"""Utility helpers for the Flask application.

Provides a small compatibility wrapper around the project-level
`utils.images` helpers so other modules can import `save_optimized_image`
from `app.utils` as before.
"""
from typing import BinaryIO

try:
	from utils.images import optimize_image_from_file
except Exception:
	optimize_image_from_file = None


def save_optimized_image(file_like: BinaryIO, dest_path: str, max_size=(800, 800), quality=80):
	"""Save an optimized JPEG from a file-like object. Delegates to `utils.images.optimize_image_from_file`.

	Kept for backwards compatibility with earlier code that imported this name from `app.utils`.
	"""
	if optimize_image_from_file is None:
		raise RuntimeError('optimize_image_from_file is not available; ensure Pillow and utils.images are present')
	return optimize_image_from_file(file_like, dest_path, max_size=max_size, quality=quality)


