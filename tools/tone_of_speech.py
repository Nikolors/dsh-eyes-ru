"""Характер речи по звуку: громкость, темп, паузы, высота голоса.

    python tools\\tone_of_speech.py путь.wav

Печатает короткий ярлык вроде «[громко, быстро, голос высокий]» и подробности.
Используется как основа для разметки реплик в слуховом режиме.
"""

from __future__ import annotations

import statistics
import sys
from pathlib import Path

import numpy as np
import opensmile
import soundfile as sf


def describe(path: Path) -> tuple[str, dict]:
    audio, rate = sf.read(str(path), dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if rate != 16000:
        # простое приведение по индексам, точность тут не критична
        idx = np.linspace(0, len(audio) - 1, int(len(audio) * 16000 / rate)).astype(np.int32)
        audio = audio[idx]
        rate = 16000

    duration = len(audio) / rate
    peak = float(np.max(np.abs(audio))) if len(audio) else 0.0
    rms = float(np.sqrt(np.mean(audio ** 2))) if len(audio) else 0.0

    smile = opensmile.Smile(
        feature_set=opensmile.FeatureSet.eGeMAPSv02,
        feature_level=opensmile.FeatureLevel.Functionals,
    )
    features = smile.process_signal(audio, rate)
    row = features.iloc[0].to_dict()

    f0 = row.get("F0semitoneFrom27.5Hz_sma3nz_amean")
    loudness = row.get("loudness_sma3_amean")
    speaking_rate = row.get("loudness_sma3_stddevNorm")

    tags: list[str] = []
    if rms > 0.12:
        tags.append("громко")
    elif rms < 0.03:
        tags.append("тихо")

    # высота голоса: выше 30 полутонов — высокий голос
    if isinstance(f0, (int, float)) and not np.isnan(f0):
        if f0 > 30:
            tags.append("голос высокий")
        elif f0 < 20:
            tags.append("голос низкий")

    if isinstance(loudness, (int, float)) and not np.isnan(loudness):
        if loudness > 1.5:
            tags.append("выразительно")

    detail = {
        "длительность": round(duration, 2),
        "пик": round(peak, 3),
        "средняя громкость": round(rms, 4),
        "F0": round(float(f0), 2) if isinstance(f0, (int, float)) and not np.isnan(f0) else None,
        "loudness": round(float(loudness), 3) if isinstance(loudness, (int, float)) and not np.isnan(loudness) else None,
    }
    return "[" + ", ".join(tags) + "]" if tags else "[спокойно]", detail


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(0)
    label, info = describe(Path(sys.argv[1]))
    print(label)
    print(info)
