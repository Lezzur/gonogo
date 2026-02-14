from pathlib import Path
from PIL import Image
from typing import Optional


def resize_screenshot(
    image_path: Path,
    max_width: int = 1280,
    max_height: int = 800,
    quality: int = 85
) -> Path:
    """Resize a screenshot if it exceeds max dimensions."""
    with Image.open(image_path) as img:
        if img.width <= max_width and img.height <= max_height:
            return image_path

        ratio = min(max_width / img.width, max_height / img.height)
        new_size = (int(img.width * ratio), int(img.height * ratio))

        resized = img.resize(new_size, Image.Resampling.LANCZOS)
        resized.save(image_path, optimize=True, quality=quality)

    return image_path


def create_thumbnail(
    image_path: Path,
    size: tuple[int, int] = (300, 200)
) -> Path:
    """Create a thumbnail version of a screenshot."""
    thumb_path = image_path.parent / f"{image_path.stem}_thumb{image_path.suffix}"

    with Image.open(image_path) as img:
        img.thumbnail(size, Image.Resampling.LANCZOS)
        img.save(thumb_path, optimize=True, quality=80)

    return thumb_path


def get_image_dimensions(image_path: Path) -> tuple[int, int]:
    """Get the dimensions of an image."""
    with Image.open(image_path) as img:
        return img.size


def convert_to_webp(image_path: Path, quality: int = 85) -> Path:
    """Convert an image to WebP format."""
    webp_path = image_path.with_suffix('.webp')

    with Image.open(image_path) as img:
        img.save(webp_path, 'WEBP', quality=quality)

    return webp_path
