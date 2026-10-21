import io
import re
import threading
from pathlib import Path

from PIL import Image, ImageDraw

_engine = None
_engine_lock = threading.Lock()

_SENSITIVE = re.compile(
    r"(?<!\d)(?:\d[ -]?){15}\d(?!\d)"
    r"|\bsk-\s*[A-Za-z0-9_-]{8,}\b"
    r"|\b(?:api_key|password|passwd|pwd)\s*[:=]\s*['\"]?[^\s'\"]+"
    r"|\bbearer\s+[^\s'\"]+",
    re.IGNORECASE,
)


def redact_text(text: str) -> str:
    return _SENSITIVE.sub("[REDACTED]", text)


def extract_with_blocks(image: Image.Image) -> tuple[str, Image.Image, list[dict]]:
    """Return safe text, redacted image, and safe OCR boxes in image pixels."""
    global _engine
    with _engine_lock:
        if _engine is None:
            from rapidocr_onnxruntime import RapidOCR
            model_dir = Path(__file__).resolve().parents[2] / "models"
            _engine = RapidOCR(
                rec_model_path=str(model_dir / "cyrillic_PP-OCRv5_rec_mobile.onnx"),
                rec_keys_path=str(model_dir / "ppocrv5_cyrillic_dict.txt"),
            )
        result, _ = _engine(image.convert("RGB"))
    items = [item for item in (result or []) if len(item) > 1 and item[1]]
    # Joining items lets a card number or key span adjacent OCR boxes.
    text = " ".join(str(item[1]) for item in items)
    ranges = []
    offset = 0
    for item in items:
        end = offset + len(str(item[1]))
        ranges.append((offset, end, item[0]))
        offset = end + 1

    redacted = image.copy()
    draw = ImageDraw.Draw(redacted)
    sensitive = set()
    for match in _SENSITIVE.finditer(text):
        for index, (start, end, polygon) in enumerate(ranges):
            if start >= match.end() or end <= match.start():
                continue
            sensitive.add(index)
            xs = [point[0] for point in polygon]
            ys = [point[1] for point in polygon]
            padding = 3
            draw.rectangle(
                (max(0, min(xs) - padding), max(0, min(ys) - padding),
                 min(image.width, max(xs) + padding), min(image.height, max(ys) + padding)),
                fill="black",
            )
    blocks = []
    for index, item in enumerate(items):
        xs = [float(point[0]) for point in item[0]]
        ys = [float(point[1]) for point in item[0]]
        blocks.append({"text": "[REDACTED]" if index in sensitive else str(item[1]),
                       "bbox": [min(xs), min(ys), max(xs), max(ys)]})
    return redact_text(text), redacted, blocks


def extract_and_redact(image: Image.Image) -> tuple[str, Image.Image]:
    text, redacted, _ = extract_with_blocks(image)
    return text, redacted


def extract_text(image_bytes: bytes) -> str:
    """Legacy text-only helper; captures should use extract_and_redact."""
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    text, _ = extract_and_redact(image)
    return text
