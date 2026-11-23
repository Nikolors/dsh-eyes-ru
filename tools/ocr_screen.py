"""Чтение текста с экрана встроенным распознаванием Windows.

    python tools\\ocr_screen.py                 # весь экран
    python tools\\ocr_screen.py window          # активное окно
    python tools\\ocr_screen.py monitor 1
    python tools\\ocr_screen.py file путь.jpg   # готовый снимок

Печатает распознанный текст построчно.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from PIL import Image, ImageGrab
from winsdk.windows.globalization import Language
from winsdk.windows.graphics.imaging import BitmapDecoder, SoftwareBitmap
from winsdk.windows.media.ocr import OcrEngine
from winsdk.windows.storage import StorageFile

sys.path.insert(0, str(Path(__file__).parent))
from grab_screen import active_window_rect, grab, monitors  # noqa: E402


async def recognize(image_path: Path, language: str = "ru") -> str:
    file = await StorageFile.get_file_from_path_async(str(image_path))
    stream = await file.open_async(0)
    decoder = await BitmapDecoder.create_async(stream)
    bitmap = await decoder.get_software_bitmap_async()
    engine = OcrEngine.try_create_from_language(Language(language))
    if engine is None:
        engine = OcrEngine.try_create_from_user_profile_languages()
    if engine is None:
        raise RuntimeError("распознавание текста Windows недоступно")
    result = await engine.recognize_async(bitmap)
    return "\n".join(line.text for line in result.lines)


def main() -> None:
    args = sys.argv[1:]
    if args and args[0] == "file":
        path = Path(args[1])
    else:
        mode = args[0] if args else "screen"
        monitor_index = int(args[1]) if len(args) > 1 and mode == "monitor" else 1
        path = grab(mode, monitor_index)
    text = asyncio.run(recognize(path))
    print(text.strip() or "(текст не найден)")


if __name__ == "__main__":
    main()
