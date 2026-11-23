"""Проверка детектора конца реплики: Smart Turn v3.2 на onnxruntime."""

from __future__ import annotations

import sys
import wave
from pathlib import Path

import numpy as np
import onnxruntime as ort
from transformers import WhisperFeatureExtractor

MODEL = Path(r"C:\work\workspace\tools\smart-turn\smart-turn-v3.2-cpu.onnx")
SESSION = ort.InferenceSession(str(MODEL), providers=["CPUExecutionProvider"])
FEATURES = WhisperFeatureExtractor(chunk_length=8)


def predict(audio: np.ndarray) -> float:
    """Вероятность, что реплика закончена (0..1). Вход — 16 кГц моно float32."""
    audio = audio[-8 * 16000 :]
    inputs = FEATURES(
        audio,
        sampling_rate=16000,
        return_tensors="np",
        padding="max_length",
        max_length=8 * 16000,
        truncation=True,
        do_normalize=True,
    )
    feats = inputs.input_features.squeeze(0).astype(np.float32)
    feats = np.expand_dims(feats, axis=0)
    out = SESSION.run(None, {"input_features": feats})[0]
    return float(np.asarray(out).reshape(-1)[0])


def read(path: str) -> np.ndarray:
    with wave.open(path, "rb") as handle:
        rate = handle.getframerate()
        data = np.frombuffer(handle.readframes(handle.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    if rate != 16000:
        idx = np.linspace(0, len(data) - 1, int(len(data) * 16000 / rate)).astype(np.int32)
        data = data[idx]
    return data


if __name__ == "__main__":
    print("вход:", SESSION.get_inputs()[0].name, SESSION.get_inputs()[0].shape)
    for path in sys.argv[1:]:
        audio = read(path)
        print(f"{Path(path).name}: {len(audio)/16000:.1f} с -> закончено {predict(audio):.3f}")
