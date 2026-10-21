import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from app.services import ocr


def box(left, top, right, bottom):
    return [[left, top], [right, top], [right, bottom], [left, bottom]]


class RedactionTests(unittest.TestCase):
    def test_card_split_across_ocr_boxes_is_covered_and_removed_from_text(self):
        image = Image.new("RGB", (100, 40), "white")
        results = [(box(2, 2, 40, 20), "4111 1111"),
                   (box(45, 2, 95, 20), "1111 1111")]
        with patch.object(ocr, "_engine", return_value=(results, None)):
            text, safe_image = ocr.extract_and_redact(image)

        self.assertEqual(text, "[REDACTED]")
        self.assertEqual(safe_image.getpixel((10, 10)), (0, 0, 0))
        self.assertEqual(safe_image.getpixel((60, 10)), (0, 0, 0))
        self.assertEqual(image.getpixel((10, 10)), (255, 255, 255))

    def test_api_key_and_bearer_values_are_removed(self):
        image = Image.new("RGB", (120, 70), "white")
        results = [(box(2, 2, 100, 20), "api_key=secret123"),
                   (box(2, 30, 100, 50), "Bearer abc.def.ghi")]
        with patch.object(ocr, "_engine", return_value=(results, None)):
            text, safe_image = ocr.extract_and_redact(image)

        self.assertEqual(text, "[REDACTED] [REDACTED]")
        self.assertEqual(safe_image.getpixel((50, 10)), (0, 0, 0))
        self.assertEqual(safe_image.getpixel((50, 40)), (0, 0, 0))

    def test_plain_text_remains(self):
        image = Image.new("RGB", (40, 30), "white")
        with patch.object(ocr, "_engine", return_value=([(box(2, 2, 35, 20), "hello")], None)):
            text, safe_image = ocr.extract_and_redact(image)

        self.assertEqual(text, "hello")
        self.assertEqual(safe_image.getpixel((10, 10)), (255, 255, 255))

    def test_russian_and_english_recognition(self):
        image_path = Path(__file__).with_name("fixtures") / "ru_en_ocr.png"
        with Image.open(image_path) as image:
            text, _, blocks = ocr.extract_with_blocks(image)

        self.assertEqual(text, "Новая вкладка New tab")
        self.assertEqual([block["text"] for block in blocks], ["Новая вкладка", "New tab"])


if __name__ == "__main__":
    unittest.main()
