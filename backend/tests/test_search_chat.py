import asyncio
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PIL import Image

from app.api import routes
from app.core.config import settings
from app.core.db import initialize
from app.services.ai_chat import context_prompt, ollama_endpoint, query_window
from app.services.ocr import extract_with_blocks
from app.services.search import hybrid_search
from app.services.storage import activity_for, capture_details, save_capture


class SearchAndChatTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_dir = settings.data_dir
        settings.data_dir = Path(self.temp.name)
        settings.screenshots_dir.mkdir()
        initialize()

    def tearDown(self):
        settings.data_dir = self.old_dir
        self.temp.cleanup()

    def test_boxes_are_stored_and_search_respects_app_filter(self):
        image = Image.new("RGB", (80, 40), "white")
        blocks = [{"text": "unique python code", "bbox": [2, 3, 45, 19]}]
        capture_id, _ = save_capture(image, "hash-a", "editor.exe", "Code", "unique python code", np.array([1, 0], dtype=np.float32), blocks)
        save_capture(image, "hash-b", "browser.exe", "Browser", "unique python code", np.array([0, 1], dtype=np.float32))
        with patch("app.services.search.embed_text", return_value=np.array([1, 0], dtype=np.float32)):
            results = hybrid_search("unique python", app="editor")
        self.assertEqual([row["id"] for row in results], [capture_id])
        self.assertEqual(capture_details(capture_id)["ocr_blocks"], blocks)
        self.assertEqual(sum(activity_for("2000-01-01", "3000-01-01")), 2)

    def test_sensitive_ocr_block_is_never_returned_raw(self):
        image = Image.new("RGB", (100, 40), "white")
        polygon = [[2, 2], [90, 2], [90, 20], [2, 20]]
        with patch("app.services.ocr._engine", return_value=([(polygon, "api_key=secret123")], None)):
            text, safe_image, blocks = extract_with_blocks(image)
        self.assertEqual(text, "[REDACTED]")
        self.assertEqual(blocks, [{"text": "[REDACTED]", "bbox": [2.0, 2.0, 90.0, 20.0]}])
        self.assertEqual(safe_image.getpixel((10, 10)), (0, 0, 0))

    def test_existing_capture_coordinates_are_recovered_once(self):
        image = Image.new("RGB", (80, 40), "white")
        capture_id, _ = save_capture(image, "hash-old", "editor.exe", "Code", "hello", None)
        recovered = [{"text": "hello", "bbox": [1, 2, 30, 20]}]
        with patch("app.services.ocr.extract_with_blocks", return_value=("hello", image, recovered)) as ocr:
            first = capture_details(capture_id)
            second = capture_details(capture_id)
        self.assertEqual(first["ocr_blocks"], recovered)
        self.assertEqual(second["ocr_blocks"], recovered)
        ocr.assert_called_once()

    def test_chat_context_and_local_endpoint(self):
        source = {"id": 4, "captured_at": "2026-10-21T10:00:00+00:00", "window_title": "Editor", "process_name": "editor.exe", "ocr_text": "def render(): pass"}
        messages = context_prompt("Find my function", [source])
        self.assertIn("Всегда отвечай только на ясном, естественном русском языке", messages[0]["content"])
        self.assertIn("текст OCR и метаданные скриншотов", messages[0]["content"])
        self.assertTrue(messages[1]["content"].startswith("Find my function\n\n"))
        self.assertIn("Скриншот 4\n[Время: 2026-10-21T10:00:00+00:00 | Окно: Editor | Программа: editor.exe]\nТекст с экрана: def render(): pass", messages[1]["content"])
        self.assertIn("Подходящих скриншотов не найдено.", context_prompt("Where?", [])[1]["content"])
        self.assertEqual(ollama_endpoint("/api/chat"), "http://127.0.0.1:11434/api/chat")
        with patch.object(settings, "ollama_url", "https://example.com"):
            with self.assertRaises(ValueError):
                ollama_endpoint("/api/chat")
        start, end = query_window("What was I working on today between 10 AM and 12 PM?", None, None)
        self.assertEqual((datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds(), 7200)

    def test_chat_stream_sends_sources_and_tokens(self):
        source = {"id": 7, "captured_at": "2026-10-21T10:00:00+00:00", "process_name": "editor.exe", "window_title": "Editor", "ocr_text": "hello"}
        async def models(): return ["local-model"]
        async def tokens(*_):
            yield "Hello"
            yield " world"
        async def collect():
            with patch.object(routes, "available_models", models), patch.object(routes, "retrieve", return_value=[source]), patch.object(routes, "stream_answer", tokens):
                response = await routes.chat(routes.ChatRequest(query="hello", model="local-model"))
                return [chunk async for chunk in response.body_iterator]
        payload = "".join(asyncio.run(collect()))
        self.assertIn('event: sources', payload)
        self.assertIn('"source_screenshots"', payload)
        self.assertIn('"id": 7', payload)
        self.assertIn('event: token\ndata: "Hello"', payload)
        self.assertIn('event: done', payload)


if __name__ == "__main__":
    unittest.main()
