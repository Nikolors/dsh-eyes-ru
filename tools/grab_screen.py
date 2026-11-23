"""Снимок экрана в трёх режимах: весь экран, активное окно, один монитор.

Пишет JPEG в C:\\work\\workspace\\.tmp\\экраны\\ и печатает путь.

    python tools\\grab_screen.py screen
    python tools\\grab_screen.py window
    python tools\\grab_screen.py monitor 1
    python tools\\grab_screen.py monitors        # список мониторов
"""

from __future__ import annotations

import ctypes
import os
import sys
import time
from ctypes import wintypes
from pathlib import Path

from PIL import ImageGrab

OUT = Path(os.environ.get("EYES_OUT", "frames"))
OUT.mkdir(parents=True, exist_ok=True)
MAX_WIDTH = 1280
QUALITY = 70

user32 = ctypes.windll.user32
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:  # noqa: BLE001
    pass


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


def monitors() -> list[tuple[int, int, int, int]]:
    """Прямоугольники мониторов (left, top, right, bottom)."""
    result: list[tuple[int, int, int, int]] = []
    MonitorEnumProc = ctypes.WINFUNCTYPE(
        ctypes.c_int, wintypes.HMONITOR, wintypes.HDC,
        ctypes.POINTER(RECT), wintypes.LPARAM,
    )

    def callback(_monitor, _hdc, rect, _data):
        result.append((rect.contents.left, rect.contents.top,
                       rect.contents.right, rect.contents.bottom))
        return 1

    user32.EnumDisplayMonitors(None, None, MonitorEnumProc(callback), 0)
    return result


def active_window_rect() -> tuple[int, int, int, int] | None:
    handle = user32.GetForegroundWindow()
    if not handle:
        return None
    rect = RECT()
    if not user32.GetWindowRect(handle, ctypes.byref(rect)):
        return None
    if rect.right <= rect.left or rect.bottom <= rect.top:
        return None
    return rect.left, rect.top, rect.right, rect.bottom


def find_window(fragment: str) -> int | None:
    """Ищет видимое окно, в заголовке которого есть текст."""
    result: list[int] = []
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_int, wintypes.HWND, wintypes.LPARAM)
    get_text = user32.GetWindowTextW
    get_len = user32.GetWindowTextLengthW
    is_visible = user32.IsWindowVisible

    def callback(hwnd, _data):
        if not is_visible(hwnd):
            return 1
        length = get_len(hwnd)
        if length <= 0:
            return 1
        buffer = ctypes.create_unicode_buffer(length + 1)
        get_text(hwnd, buffer, length + 1)
        if fragment.lower() in buffer.value.lower():
            result.append(hwnd)
            return 0
        return 1

    user32.EnumWindows(EnumWindowsProc(callback), 0)
    return result[0] if result else None


def window_rect(hwnd: int) -> tuple[int, int, int, int] | None:
    rect = RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None
    if rect.right <= rect.left or rect.bottom <= rect.top:
        return None
    return rect.left, rect.top, rect.right, rect.bottom


def grab(mode: str, monitor_index: int = 1) -> Path:
    if mode.startswith("title:"):
        hwnd = find_window(mode[6:])
        if hwnd is None:
            raise RuntimeError(f"окно с «{mode[6:]}» не найдено")
        bbox = window_rect(hwnd)
        if bbox is None:
            raise RuntimeError("у окна нет размеров")
        image = ImageGrab.grab(bbox=bbox, all_screens=True)
    elif mode == "window":
        bbox = active_window_rect()
        if bbox is None:
            raise RuntimeError("активное окно не найдено")
        image = ImageGrab.grab(bbox=bbox, all_screens=True)
    elif mode == "monitor":
        screens = monitors()
        if not screens:
            raise RuntimeError("мониторы не найдены")
        index = max(1, min(monitor_index, len(screens))) - 1
        image = ImageGrab.grab(bbox=screens[index], all_screens=True)
    else:
        image = ImageGrab.grab(all_screens=True)

    if image.width > MAX_WIDTH:
        ratio = MAX_WIDTH / image.width
        image = image.resize((MAX_WIDTH, int(image.height * ratio)))
    path = OUT / f"снимок-{time.strftime('%H%M%S')}-{time.time_ns() % 1000:03d}.jpg"
    image.convert("RGB").save(path, format="JPEG", quality=QUALITY)
    return path


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "screen"
    if mode == "monitors":
        for number, box in enumerate(monitors(), start=1):
            print(f"{number}: {box}")
        return
    monitor_index = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    path = grab(mode, monitor_index)
    print(path)


if __name__ == "__main__":
    main()
