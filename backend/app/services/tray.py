import asyncio
import logging
import signal
import sys
import webbrowser

from PIL import Image, ImageDraw

from .. import state

logger = logging.getLogger(__name__)


def _icon_image() -> Image.Image:
    image = Image.new("RGB", (64, 64), "#182333")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((13, 10, 51, 54), radius=7, outline="white", width=4)
    draw.line((21, 23, 43, 23), fill="white", width=4)
    draw.line((21, 33, 43, 33), fill="white", width=4)
    draw.line((21, 43, 36, 43), fill="white", width=4)
    return image


class RecallTray:
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop
        self.icon = None

    def start(self) -> None:
        if sys.platform != "win32":
            return
        import pystray

        def toggle(icon, item):
            try:
                if state.worker.running:
                    state.stop_worker()
                else:
                    state.start_worker()
                icon.update_menu()
            except Exception:
                logger.exception("Could not toggle capture from tray")

        def exit_app(icon, item):
            icon.stop()
            # Uvicorn handles SIGINT and completes FastAPI lifespan cleanup.
            self.loop.call_soon_threadsafe(signal.raise_signal, signal.SIGINT)

        self.icon = pystray.Icon(
            "local-recall",
            _icon_image(),
            "Local Recall",
            pystray.Menu(
                pystray.MenuItem("Open Local Recall", lambda icon, item: webbrowser.open("http://localhost:5173"), default=True),
                pystray.MenuItem("Pause Capture", toggle, checked=lambda item: not state.worker.running),
                pystray.MenuItem("Exit", exit_app),
            ),
        )
        self.icon.run_detached()

    def stop(self) -> None:
        if self.icon is not None:
            self.icon.stop()
            self.icon = None
