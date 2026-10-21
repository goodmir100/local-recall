from datetime import datetime, timezone, timedelta
from io import BytesIO
import json
from pathlib import Path
import numpy as np
from PIL import Image
from ..core.config import settings
from ..core.db import connection


def save_capture(image: Image.Image, image_hash: str, process_name: str, window_title: str, ocr_text: str, embedding: np.ndarray | None, ocr_blocks: list[dict] | None = None) -> tuple[int, str]:
    captured_at = datetime.now(timezone.utc)
    filename = captured_at.strftime("%Y%m%d_%H%M%S_%f") + ".jpg"
    target = settings.screenshots_dir / filename
    image.save(target, "JPEG", quality=78, optimize=True)
    vector = embedding.astype(np.float32).tobytes() if embedding is not None else None
    try:
        with connection() as db:
            cur = db.execute("INSERT INTO captures(captured_at,image_path,image_hash,process_name,window_title,ocr_text,embedding,ocr_blocks) VALUES(?,?,?,?,?,?,?,?)",
                (captured_at.isoformat(), str(target), image_hash, process_name, window_title, ocr_text, vector, json.dumps(ocr_blocks or [])))
            return int(cur.lastrowid), filename
    except Exception:
        target.unlink(missing_ok=True)
        raise


def list_captures(limit=20, offset=0, app=None, date_from=None, date_to=None):
    clauses, args = [], []
    if app:
        clauses.append("process_name LIKE ?"); args.append(f"%{app}%")
    if date_from:
        clauses.append("captured_at >= ?"); args.append(date_from)
    if date_to:
        clauses.append("captured_at <= ?"); args.append(date_to)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    with connection() as db:
        rows = db.execute(f"SELECT id,captured_at,process_name,window_title,ocr_text FROM captures{where} ORDER BY captured_at DESC LIMIT ? OFFSET ?", (*args, min(max(limit, 1), 500), max(offset, 0)))
        return [dict(row) for row in rows]


def image_for(capture_id: int) -> bytes | None:
    with connection() as db:
        row = db.execute("SELECT image_path,image FROM captures WHERE id=?", (capture_id,)).fetchone()
    if not row:
        return None
    path = row["image_path"]
    if path and Path(path).is_file():
        return Path(path).read_bytes()
    return bytes(row["image"]) if row["image"] is not None else None


def capture_details(capture_id: int) -> dict | None:
    with connection() as db:
        row = db.execute("SELECT id,captured_at,process_name,window_title,ocr_text,ocr_blocks FROM captures WHERE id=?", (capture_id,)).fetchone()
    if row is None:
        return None
    result = dict(row)
    blocks = json.loads(result["ocr_blocks"] or "[]")
    if blocks == [] and result["ocr_text"]:
        # Older captures have OCR text but no coordinates. Recover them from the
        # stored, already-redacted screenshot when the frame is first inspected.
        data = image_for(capture_id)
        if data:
            try:
                from .ocr import extract_with_blocks
                _, _, blocks = extract_with_blocks(Image.open(BytesIO(data)).convert("RGB"))
                with connection() as db:
                    db.execute("UPDATE captures SET ocr_blocks=? WHERE id=?", (json.dumps(blocks if blocks else None), capture_id))
            except (OSError, RuntimeError, ImportError, ValueError):
                blocks = []
    result["ocr_blocks"] = blocks or []
    return result


def activity_for(date_from: str, date_to: str, utc_offset_minutes: int = 0) -> list[int]:
    with connection() as db:
        rows = db.execute("SELECT captured_at FROM captures WHERE captured_at >= ? AND captured_at < ?", (date_from, date_to)).fetchall()
    counts = [0] * 24
    for row in rows:
        counts[datetime.fromisoformat(row[0]).astimezone(timezone(timedelta(minutes=utc_offset_minutes))).hour] += 1
    return counts


def cleanup(days: int) -> int:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    with connection() as db:
        rows = db.execute("SELECT id,image_path FROM captures WHERE captured_at < ?", (cutoff,)).fetchall()
        db.executemany("DELETE FROM captures WHERE id=?", [(row["id"],) for row in rows])
    for row in rows:
        if row["image_path"]:
            Path(row["image_path"]).unlink(missing_ok=True)
    return len(rows)
