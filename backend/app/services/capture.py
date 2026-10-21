import logging
import os
import time
import traceback
import threading
from pathlib import Path
import imagehash
from mss import mss
from PIL import Image
from ..core.config import settings
from .embedder import embed_text
from .ignore_list import is_ignored
from .ocr import extract_with_blocks, redact_text
from .storage import save_capture

logger = logging.getLogger(__name__)


def active_window() -> tuple[str, str]:
    """Read the foreground window title via pygetwindow and resolve its executable on Windows."""
    try:
        import pygetwindow
        window = pygetwindow.getActiveWindow()
        title = window.title if window else ""
        process = ""
        if window and getattr(window, "_hWnd", None):
            import psutil
            import win32process
            _, pid = win32process.GetWindowThreadProcessId(window._hWnd)
            process = Path(psutil.Process(pid).exe()).name
        return process, title
    except Exception:
        logger.exception("Failed to read the active window")
        return "", ""


class CaptureWorker:
    def __init__(self):
        self.running = False
        self.previous_hash = None
        self._stop_event = threading.Event()

    def start(self):
        self._stop_event.clear()
        self.running = True

    def run(self):
        print("[Worker] Capture worker thread started!", flush=True)
        try:
            os.makedirs(settings.screenshots_dir, exist_ok=True)
            print(f"[capture] Screenshots directory: {settings.screenshots_dir}", flush=True)
            with mss() as screen:
                monitor = screen.monitors[0]
                while not self._stop_event.is_set():
                    started = time.monotonic()
                    try:
                        print("[capture] Getting active window...", flush=True)
                        process, title = active_window()
                        if is_ignored(process, title):
                            print("[capture] Window ignored", flush=True)
                        else:
                            print(f"[Worker] Capturing window: {redact_text(title)}", flush=True)
                            print("[capture] Grabbing screen...", flush=True)
                            shot = screen.grab(monitor)
                            frame = Image.frombytes("RGB", shot.size, shot.rgb)
                            print("[capture] Computing pHash...", flush=True)
                            digest = imagehash.phash(frame)
                            # pHash is a 64-bit fingerprint; avoid saving near-identical frames.
                            difference_percent = ((self.previous_hash - digest) / 64 * 100) if self.previous_hash is not None else 100
                            if self.previous_hash is None or difference_percent > settings.dedupe_threshold:
                                print("[capture] Running OCR...", flush=True)
                                try:
                                    text, safe_frame, blocks = extract_with_blocks(frame)
                                except Exception as e:
                                    print(f"[Worker ERROR] OCR: {e}", flush=True)
                                    traceback.print_exc()
                                    self._stop_event.wait(settings.capture_interval_seconds)
                                    continue
                                if self._stop_event.is_set():
                                    break
                                try:
                                    vector = embed_text(f"{redact_text(title)}\n{process}\n{text}")
                                except Exception as e:
                                    print(f"[Worker ERROR] Embedding: {e}", flush=True)
                                    traceback.print_exc()
                                    vector = None
                                print("[capture] Saving screenshot...", flush=True)
                                if self._stop_event.is_set():
                                    break
                                _, filename = save_capture(safe_frame, str(digest), process, redact_text(title), text, vector, blocks)
                                self.previous_hash = digest
                                print(f"[+] Screenshot saved: {filename}", flush=True)
                                print(f"[Worker SUCCESS] Saved screenshot to {settings.screenshots_dir / filename}", flush=True)
                            else:
                                print("[capture] Frame skipped (similar pHash)", flush=True)
                                print("[Worker] Frame skipped (identical to previous)", flush=True)
                    except Exception as e:
                        print(f"[Worker ERROR] {e}", flush=True)
                        traceback.print_exc()
                    self._stop_event.wait(max(0, settings.capture_interval_seconds - (time.monotonic() - started)))
        except Exception as e:
            print(f"[Worker ERROR] {e}", flush=True)
            traceback.print_exc()
        finally:
            self.running = False

    def stop(self):
        self.running = False
        self._stop_event.set()
