import os
import unittest
from io import BytesIO

from fastapi import HTTPException, UploadFile
from PIL import Image

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")

from app.utils.uploads import validate_image_upload


def image_bytes(format_name="PNG"):

    buffer = BytesIO()
    image = Image.new(
        "RGB",
        (8, 8),
        color=(255, 0, 0)
    )
    image.save(buffer, format=format_name)
    buffer.seek(0)
    return buffer


def upload_file(content, content_type):

    return UploadFile(
        filename="upload",
        file=content,
        headers={
            "content-type": content_type
        }
    )


class UploadSecurityTests(unittest.TestCase):

    def test_valid_png_is_accepted(self):

        file = upload_file(
            image_bytes("PNG"),
            "image/png"
        )

        result = validate_image_upload(file)

        self.assertEqual(result["content_type"], "image/png")
        self.assertEqual(result["width"], 8)
        self.assertEqual(result["height"], 8)

    def test_non_image_is_rejected_even_with_image_mime(self):

        file = upload_file(
            BytesIO(b"not an image"),
            "image/png"
        )

        with self.assertRaises(HTTPException) as exc:
            validate_image_upload(file)

        self.assertEqual(exc.exception.status_code, 400)

    def test_fake_mime_type_is_rejected(self):

        file = upload_file(
            image_bytes("JPEG"),
            "image/png"
        )

        with self.assertRaises(HTTPException) as exc:
            validate_image_upload(file)

        self.assertEqual(exc.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
