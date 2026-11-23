"""Мои глаза в одном месте: снимок, текст с экрана, камера, описание модели.

    python tools\\eyes.py text                 # текст с экрана (OCR)
    python tools\\eyes.py text window          # текст активного окна
    python tools\\eyes.py text monitor 1
    python tools\\eyes.py shot                 # снимок экрана, печатает путь
    python tools\\eyes.py shot window
    python tools\\eyes.py camera               # кадр с камеры + путь
    python tools\\eyes.py look                 # камера и описание маленькой моделью
    python tools\\eyes.py look screen          # экран и описание маленькой моделью
    python tools\\eyes.py ask путь.jpg "вопрос" # спросить модель о готовом снимке
"""

from __future__ import annotations

import asyncio
import os
import base64
import io
import json
import sys
import urllib.request
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from grab_screen import grab  # noqa: E402

MODEL = "qwen2.5vl:3b"
OLLAMA = "http://127.0.0.1:11434/api/generate"
DEFAULT_QUESTION = (
    "Опиши коротко по-русски, что видно на кадре: что за окно или сцена, "
    "что происходит. Без вступлений, не повторяйся."
)


def camera_frame() -> Path:
    import cv2  # noqa: PLC0415

    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not camera.isOpened():
        raise RuntimeError("камера не открылась")
    ok, frame = camera.read()
    camera.release()
    if not ok:
        raise RuntimeError("кадр с камеры не получен")
    image = Image.fromarray(frame[:, :, ::-1])
    path = Path(os.environ.get("EYES_OUT", "frames")) / "camera.jpg"
    path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(path, format="JPEG", quality=85)
    return path


def ask(image_path: Path, question: str) -> str:
    image = Image.open(image_path)
    if image.width > 800:
        ratio = 800 / image.width
        image = image.resize((800, int(image.height * ratio)))
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=75)
    payload = {
        "model": MODEL,
        "prompt": question,
        "images": [base64.b64encode(buffer.getvalue()).decode("ascii")],
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 120, "repeat_penalty": 1.25},
    }
    request = urllib.request.Request(OLLAMA, data=json.dumps(payload).encode("utf-8"), method="POST")
    request.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(request, timeout=300) as response:
        return str(json.load(response).get("response", "")).strip()


def main() -> None:
    args = sys.argv[1:]
    command = args[0] if args else "shot"

    if command == "shot":
        mode = args[1] if len(args) > 1 else "screen"
        monitor_index = int(args[2]) if len(args) > 2 else 1
        print(grab(mode, monitor_index))
        return

    if command == "camera":
        print(camera_frame())
        return

    if command == "text":
        from ocr_screen import recognize

        mode = args[1] if len(args) > 1 else "screen"
        monitor_index = int(args[2]) if len(args) > 2 else 1
        path = grab(mode, monitor_index)
        print(asyncio.run(recognize(path)).strip() or "(текст не найден)")
        return

    if command == "look":
        source = args[1] if len(args) > 1 else "camera"
        path = camera_frame() if source == "camera" else grab(source)
        print(path)
        print(ask(path, DEFAULT_QUESTION))
        return

    if command == "ask":
        path = Path(args[1])
        question = args[2] if len(args) > 2 else DEFAULT_QUESTION
        print(ask(path, question))
        return

    print(__doc__)


if __name__ == "__main__":
    main()
