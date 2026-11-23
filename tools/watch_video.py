"""Смотрю ролик со субтитрами: снимок экрана → OCR → лента реплик.

    python tools\\watch_video.py [секунд_между_кадрами] [минут_работы]

Пишет в .tmp\\video-log.log по строке на кадр; повторяющиеся строки пропускает,
чтобы лента была читаемой.
"""

from __future__ import annotations

import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from grab_screen import grab  # noqa: E402
from ocr_screen import recognize  # noqa: E402

LOG = Path(os.environ.get("EYES_LOG", "video-log.log"))


def log(text: str) -> None:
    line = f"{datetime.now():%H:%M:%S} {text}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def main() -> None:
    interval = float(sys.argv[1]) if len(sys.argv) > 1 else 2.0
    minutes = float(sys.argv[2]) if len(sys.argv) > 2 else 10.0
    mode = sys.argv[3] if len(sys.argv) > 3 else "screen"
    deadline = time.monotonic() + minutes * 60
    last = ""
    log(f"--- смотрю экран: кадр раз в {interval} с, до {minutes} мин")
    while time.monotonic() < deadline:
        started = time.monotonic()
        try:
            path = grab(mode)
            text = asyncio.run(recognize(path))
            text = " ".join(text.split())
            if text and text != last:
                log(text[-300:])
                last = text
        except Exception as error:  # noqa: BLE001
            log(f"ошибка: {error}")
        rest = interval - (time.monotonic() - started)
        if rest > 0:
            time.sleep(rest)
    log("--- конец просмотра")


if __name__ == "__main__":
    main()
