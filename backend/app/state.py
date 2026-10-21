import threading
from .services.capture import CaptureWorker

worker = CaptureWorker()
_thread = None
_lock = threading.Lock()
def start_worker():
    global _thread
    with _lock:
        if worker.running:
            return
        if _thread is not None and _thread.is_alive():
            _thread.join()
        from .core.db import write_setting
        write_setting("capture_enabled", "true")
        worker.start()
        _thread = threading.Thread(target=worker.run, daemon=True, name="local-recall-capture")
        try:
            _thread.start()
        except Exception:
            worker.stop()
            raise


def stop_worker(persist: bool = True):
    with _lock:
        if persist:
            from .core.db import write_setting
            write_setting("capture_enabled", "false")
        worker.stop()
        if _thread is not None and _thread.is_alive() and _thread is not threading.current_thread():
            _thread.join()
