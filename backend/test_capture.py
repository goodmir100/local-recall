import time
import sqlite3
import mss
from PIL import Image
import pygetwindow as gw
from rapidocr_onnxruntime import RapidOCR

print("1. Получение активного окна...")
try:
    active_window = gw.getActiveWindow()
    window_title = active_window.title if active_window else "Unknown"
    print(f"   [+] Окно: {window_title}")
except Exception as e:
    window_title = "Error"
    print(f"   [-] Ошибка окна: {e}")

print("2. Захват экрана...")
with mss.MSS() as sct:
    monitor = sct.monitors[1]  # Основной монитор
    sct_img = sct.grab(monitor)
    img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
    img.save("test_screen.png")
    print("   [+] Скриншот сохранен в test_screen.png")

print("3. Запуск OCR (RapidOCR)...")
ocr_engine = RapidOCR()
ocr_result, _ = ocr_engine("test_screen.png")

extracted_text = ""
if ocr_result:
    # Собираем весь найденный текст в одну строку
    extracted_text = " ".join([item[1] for item in ocr_result])
    print(f"   [+] Распознано элементов: {len(ocr_result)}")
    print(f"   [+] Фрагмент текста: {extracted_text[:100]}...")
else:
    print("   [-] Текст не найден")

print("4. Проверка записи в SQLite...")
conn = sqlite3.connect("test_local_recall.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS screenshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    window_title TEXT,
    ocr_text TEXT
)
""")

cursor.execute(
    "INSERT INTO screenshots (window_title, ocr_text) VALUES (?, ?)",
    (window_title, extracted_text)
)
conn.commit()

cursor.execute("SELECT COUNT(*) FROM screenshots")
count = cursor.fetchone()[0]
conn.close()

print(f"   [+] Успешно записано в SQLite. Всего записей в тестовой БД: {count}")
print("\n🔥 Backend-ядро (Capture + OCR + DB) работает корректно!")