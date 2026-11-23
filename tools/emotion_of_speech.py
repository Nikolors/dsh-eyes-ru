"""Эмоция в речи: русская модель на базе HuBERT (датасет DUSHA).

    python tools\\emotion_of_speech.py путь.wav

Печатает метку эмоции и вероятности. Модель скачивается один раз (~1,2 ГБ).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from transformers import AutoFeatureExtractor, AutoModelForAudioClassification

MODEL_ID = "xbgoose/hubert-large-speech-emotion-recognition-russian-dusha-finetuned"
_cache: dict[str, object] = {}


def load():
    if "model" not in _cache:
        extractor = AutoFeatureExtractor.from_pretrained(MODEL_ID)
        model = AutoModelForAudioClassification.from_pretrained(MODEL_ID)
        model.eval()
        _cache["extractor"] = extractor
        _cache["model"] = model
        _cache["labels"] = model.config.id2label
    return _cache["extractor"], _cache["model"], _cache["labels"]


def analyze(path: Path) -> tuple[str, dict]:
    extractor, model, labels = load()
    audio, rate = sf.read(str(path), dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if rate != 16000:
        idx = np.linspace(0, len(audio) - 1, int(len(audio) * 16000 / rate)).astype(np.int32)
        audio = audio[idx]
        rate = 16000
    # модель обучена на коротких фрагментах — берём середину, если запись длинная
    limit = 16000 * 8
    if len(audio) > limit:
        start = (len(audio) - limit) // 2
        audio = audio[start:start + limit]
    inputs = extractor(audio, sampling_rate=16000, return_tensors="pt", padding=True)
    with torch.no_grad():
        logits = model(**inputs).logits
    probs = torch.softmax(logits, dim=-1)[0].numpy()
    order = np.argsort(probs)[::-1]
    top = labels[int(order[0])]
    table = {labels[int(i)]: round(float(probs[i]) * 100, 1) for i in order[:4]}
    return top, table


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(0)
    label, table = analyze(Path(sys.argv[1]))
    print(label)
    print(table)
