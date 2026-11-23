"""Облачные глаза на Qwen3.8-Omni (Alibaba): кадр → короткое описание в ленту.

    python tools\\cloud_eyes.py camera 2      # камера, кадр раз в 2 секунды
    python tools\\cloud_eyes.py screen 2      # экран
    python tools\\cloud_eyes.py window 3      # активное окно

Ключ берётся из .secrets\\dashscope-key.txt. Лента — .tmp\\vision-cloud.log.
"Размышления" модели отключены, поэтому ответ приходит за 2–3 секунды.
"""

from __future__ import annotations

import base64
import io
import json
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from grab_screen import grab  # noqa: E402

KEY = Path(os.environ.get("DASHSCOPE_KEY_FILE", "dashscope-key.txt")).read_text(encoding="utf-8").strip()
URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"
MODEL = "qwen3.8-omni-flash"
LOG = Path(os.environ.get("EYES_LOG", "vision-cloud.log"))
PROMPT = (
    "Опиши одной короткой фразой по-русски, что видно: кто или что в кадре, "
    "что происходит. Без вступлений, не повторяйся."
)
MAX_WIDTH = 640


def log(text: str) -> None:
    line = f"{datetime.now():%H:%M:%S} {text}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def camera_frame() -> Image.Image:
    import cv2  # noqa: PLC0415

    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not camera.isOpened():
        raise RuntimeError("камера не открылась")
    ok, frame = camera.read()
    camera.release()
    if not ok:
        raise RuntimeError("кадр не получен")
    return Image.fromarray(frame[:, :, ::-1])


def describe(image: Image.Image) -> tuple[str, dict]:
    if image.width > MAX_WIDTH:
        ratio = MAX_WIDTH / image.width
        image = image.resize((MAX_WIDTH, int(image.height * ratio)))
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=70)
    b64 = base64.b64encode(buffer.getvalue()).decode("ascii")
    payload = {
        "model": MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                {"type": "text", "text": PROMPT},
            ],
        }],
        "max_tokens": 80,
        "enable_thinking": False,
    }
    request = urllib.request.Request(URL, data=json.dumps(payload).encode("utf-8"), method="POST")
    request.add_header("Authorization", f"Bearer {KEY}")
    request.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(request, timeout=120) as response:
        data = json.load(response)
    text = data["choices"][0]["message"]["content"].strip().replace("\n", " ")
    return text, data.get("usage", {})


def main() -> None:
    source = sys.argv[1] if len(sys.argv) > 1 else "camera"
    interval = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
    log(f"--- облачные глаза: {source}, кадр раз в {interval} с, модель {MODEL}")
    while True:
        started = time.monotonic()
        try:
            image = camera_frame() if source == "camera" else Image.open(grab(source))
            text, usage = describe(image)
            tokens = usage.get("total_tokens")
            log(f"{text}  [{tokens} ток.]")
        except Exception as error:  # noqa: BLE001
            log(f"ошибка: {error}")
        rest = interval - (time.monotonic() - started)
        if rest > 0:
            time.sleep(rest)


if __name__ == "__main__":
    main()
