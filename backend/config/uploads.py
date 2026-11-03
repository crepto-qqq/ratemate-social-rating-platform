"""Decode uploaded raster images and store only freshly encoded pixels."""
from io import BytesIO
from uuid import uuid4
import warnings

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_IMAGE_PIXELS = 16_000_000
ALLOWED_FORMATS = {'JPEG', 'PNG', 'WEBP'}
ALLOWED_CONTENT_TYPES = {'image/jpeg', 'image/png', 'image/webp'}


def sanitize_image(upload):
    if upload.size > MAX_UPLOAD_BYTES:
        raise ValidationError('Images must be 5 MB or smaller.')
    if getattr(upload, 'content_type', '') not in ALLOWED_CONTENT_TYPES:
        raise ValidationError('Use a JPG, PNG or WebP image.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            upload.seek(0)
            with Image.open(upload) as probe:
                if probe.format not in ALLOWED_FORMATS:
                    raise ValidationError('Use a JPG, PNG or WebP image.')
                if probe.width * probe.height > MAX_IMAGE_PIXELS:
                    raise ValidationError('Image resolution must not exceed 16 megapixels.')
                probe.verify()
            upload.seek(0)
            with Image.open(upload) as source:
                source.load()
                pixels = ImageOps.exif_transpose(source)
                mode = 'RGBA' if 'A' in pixels.getbands() or 'transparency' in pixels.info else 'RGB'
                converted = pixels.convert(mode)
                clean = Image.new(mode, converted.size)
                clean.paste(converted)
                output = BytesIO()
                clean.save(output, format='PNG')
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError,
            Image.DecompressionBombWarning) as error:
        raise ValidationError('The uploaded file is not a valid supported image.') from error
    return ContentFile(output.getvalue(), name=f'{uuid4().hex}.png')
