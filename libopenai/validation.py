"""Validation for OpenAI image generation parameters.

Constraints follow the image generation guide for ``gpt-image-2``:
https://developers.openai.com/api/docs/guides/image-generation
"""

IMAGE_SIZE_AUTO = "auto"
IMAGE_QUALITY_AUTO = "auto"
IMAGE_SIZE_DEFAULT = "1024x1024"
IMAGE_QUALITY_DEFAULT = "low"
IMAGE_FORMAT_DEFAULT = "jpeg"
IMAGE_MODEL_DEFAULT = "gpt-image-1-mini"

IMAGE_QUALITIES = (IMAGE_QUALITY_AUTO, "low", "medium", "high")
IMAGE_FORMATS = ("png", "jpeg", "webp")
IMAGE_MODELS = ("gpt-image-2", "gpt-image-1.5", "gpt-image-1", "gpt-image-1-mini")
IMAGE_SIZE_PRESETS = (
    IMAGE_SIZE_AUTO,
    "1024x640",
    "1024x1024",
    "1536x1024",
    "1024x1536",
    "2048x2048",
    "2048x1152",
    "3840x2160",
    "2160x3840",
)

MAX_EDGE = 3840
EDGE_MULTIPLE = 16
MAX_ASPECT_RATIO = 3.0
MIN_PIXELS = 655_360
MAX_PIXELS = 8_294_400


def parse_size(size):
    """Parse ``"WIDTHxHEIGHT"`` into a ``(width, height)`` tuple of ints."""
    parts = size.lower().split("x")
    if len(parts) != 2:
        raise ValueError(f"invalid size {size!r}: expected WIDTHxHEIGHT")
    try:
        width, height = int(parts[0]), int(parts[1])
    except ValueError as e:
        raise ValueError(f"invalid size {size!r}: non-integer dimension") from e
    if width <= 0 or height <= 0:
        raise ValueError(f"invalid size {size!r}: dimensions must be positive")
    return width, height


def validate_image_size(size):
    """Return ``size`` unchanged if valid, otherwise raise ``ValueError``."""
    if size == IMAGE_SIZE_AUTO:
        return size
    width, height = parse_size(size)
    if width > MAX_EDGE or height > MAX_EDGE:
        raise ValueError(f"invalid size {size!r}: each edge must be <= {MAX_EDGE}px")
    if width % EDGE_MULTIPLE or height % EDGE_MULTIPLE:
        raise ValueError(
            f"invalid size {size!r}: each edge must be a multiple of {EDGE_MULTIPLE}px"
        )
    ratio = max(width, height) / min(width, height)
    if ratio > MAX_ASPECT_RATIO:
        raise ValueError(
            f"invalid size {size!r}: aspect ratio must be <= {MAX_ASPECT_RATIO:g}:1"
        )
    pixels = width * height
    if pixels < MIN_PIXELS or pixels > MAX_PIXELS:
        raise ValueError(
            f"invalid size {size!r}: total pixels must be between "
            f"{MIN_PIXELS:,} and {MAX_PIXELS:,}"
        )
    return size


def validate_image_quality(quality):
    """Return ``quality`` unchanged if valid, otherwise raise ``ValueError``."""
    if quality not in IMAGE_QUALITIES:
        allowed = ", ".join(IMAGE_QUALITIES)
        raise ValueError(f"invalid quality {quality!r}: must be one of {allowed}")
    return quality


def validate_image_format(image_format):
    """Return ``image_format`` unchanged if valid, otherwise raise ``ValueError``."""
    if image_format not in IMAGE_FORMATS:
        allowed = ", ".join(IMAGE_FORMATS)
        raise ValueError(f"invalid format {image_format!r}: must be one of {allowed}")
    return image_format


def validate_image_model(model):
    """Return ``model`` unchanged if valid, otherwise raise ``ValueError``."""
    if model not in IMAGE_MODELS:
        allowed = ", ".join(IMAGE_MODELS)
        raise ValueError(f"invalid image model {model!r}: must be one of {allowed}")
    return model
