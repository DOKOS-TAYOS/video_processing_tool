from __future__ import annotations

import numpy as np
import pyloudnorm as pyln
from numpy.typing import NDArray

AudioArray = NDArray[np.float32]


def normalize_loudness(audio: AudioArray, sample_rate: int, target_lufs: float) -> AudioArray:
    audio_float64 = audio.astype(np.float64)
    meter = pyln.Meter(sample_rate)
    measured_loudness = meter.integrated_loudness(audio_float64)

    if not np.isfinite(measured_loudness):
        return audio.astype(np.float32)

    normalized = pyln.normalize.loudness(audio_float64, measured_loudness, target_lufs)
    return np.asarray(normalized, dtype=np.float32)
