from io import BytesIO
from unittest.mock import patch

from PIL import Image, PngImagePlugin
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from .uploads import sanitize_image


class ImageSanitationTests(SimpleTestCase):
    def png(self, name='image.png'):
        output = BytesIO()
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text('Comment', 'private-image-metadata')
        Image.new('RGBA', (2, 2), (255, 0, 0, 100)).save(output, format='PNG', pnginfo=metadata)
        return SimpleUploadedFile(name, output.getvalue(), content_type='image/png')

    def test_pixels_and_transparency_survive_but_metadata_and_filename_do_not(self):
        result = sanitize_image(self.png('unicode-name.html'))
        self.assertRegex(result.name, r'^[0-9a-f]{32}\.png$')
        with Image.open(result) as clean:
            self.assertEqual(clean.mode, 'RGBA')
            self.assertEqual(clean.getpixel((0, 0)), (255, 0, 0, 100))
            self.assertNotIn('Comment', clean.info)

    def test_spoofed_image_and_svg_are_rejected(self):
        for data in [b'not an image', b'<svg xmlns="http://www.w3.org/2000/svg"><script/></svg>']:
            with self.subTest(data=data), self.assertRaises(ValidationError):
                sanitize_image(SimpleUploadedFile('photo.png', data, content_type='image/png'))

    def test_unsupported_declared_content_type_is_rejected(self):
        upload = self.png()
        upload.content_type = 'text/html'
        with self.assertRaises(ValidationError):
            sanitize_image(upload)

    def test_oversized_upload_is_rejected_before_decoding(self):
        with patch('config.uploads.MAX_UPLOAD_BYTES', 1), self.assertRaises(ValidationError):
            sanitize_image(self.png())

    def test_excessive_pixel_count_is_rejected_before_decoding(self):
        with patch('config.uploads.MAX_IMAGE_PIXELS', 1), self.assertRaises(ValidationError):
            sanitize_image(self.png())

    def test_truncated_image_is_rejected(self):
        upload = self.png()
        data = upload.read()[:25]
        with self.assertRaises(ValidationError):
            sanitize_image(SimpleUploadedFile('image.png', data, content_type='image/png'))
