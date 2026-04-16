from __future__ import annotations

import math

import numpy as np
from numpy.typing import NDArray

from video_processing.config import CompressionConfig

AudioArray = NDArray[np.float32]


def apply_peak_normalization(audio: AudioArray, target_peak_db: float) -> AudioArray:
    current_peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if current_peak <= 0.0:
        return audio.astype(np.float32)

    target_peak = 10 ** (target_peak_db / 20.0)
    gain = target_peak / current_peak
    return np.asarray(audio * gain, dtype=np.float32)


def _compress_channel(
    audio: NDArray[np.float32],
    sample_rate: int,
    config: CompressionConfig,
) -> NDArray[np.float32]:
    threshold_linear = 10 ** (config.threshold_db / 20.0)
    attack_seconds = max(config.attack_ms / 1000.0, 1e-4)
    release_seconds = max(config.release_ms / 1000.0, 1e-4)
    attack_coefficient = math.exp(-1.0 / (sample_rate * attack_seconds))
    release_coefficient = math.exp(-1.0 / (sample_rate * release_seconds))
    makeup_gain = 10 ** (config.makeup_gain_db / 20.0)

    envelope = 0.0
    compressed = np.zeros_like(audio, dtype=np.float32)

    for index, sample in enumerate(audio):
        absolute_sample = abs(float(sample))
        coefficient = attack_coefficient if absolute_sample > envelope else release_coefficient
        envelope = coefficient * envelope + (1.0 - coefficient) * absolute_sample

        if envelope <= threshold_linear or envelope <= 0.0:
            gain = makeup_gain
        else:
            level_db = 20.0 * math.log10(envelope)
            compressed_db = config.threshold_db + (level_db - config.threshold_db) / config.ratio
            gain_reduction_db = compressed_db - level_db
            gain = makeup_gain * (10 ** (gain_reduction_db / 20.0))

        compressed[index] = np.float32(sample * gain)

    return compressed


def compress_audio(audio: AudioArray, sample_rate: int, config: CompressionConfig) -> AudioArray:
    if audio.ndim == 1:
        return _compress_channel(audio, sample_rate, config)

    channels = [
        _compress_channel(audio[:, channel_index], sample_rate, config)
        for channel_index in range(audio.shape[1])
    ]
    return np.stack(channels, axis=1).astype(np.float32)
