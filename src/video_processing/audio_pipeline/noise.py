from __future__ import annotations

from collections.abc import Callable

import noisereduce as nr
import numpy as np
from numpy.typing import NDArray

from video_processing.config import NoiseReductionConfig

AudioArray = NDArray[np.float32]


def extract_noise_sample(
    audio: AudioArray,
    sample_rate: int,
    start_seconds: float,
    duration_seconds: float,
) -> AudioArray:
    start_index = max(0, int(start_seconds * sample_rate))
    end_index = min(audio.shape[0], start_index + int(duration_seconds * sample_rate))

    if start_index >= audio.shape[0] or end_index <= start_index:
        fallback_end = min(audio.shape[0], int(duration_seconds * sample_rate))
        return audio[:fallback_end].copy()

    return audio[start_index:end_index].copy()


def _reduce_noise_channel(
    audio: NDArray[np.float32],
    noise_sample: NDArray[np.float32],
    sample_rate: int,
    config: NoiseReductionConfig,
) -> NDArray[np.float32]:
    kwargs: dict[str, float | int | bool | NDArray[np.float32]] = {
        "y": audio,
        "sr": sample_rate,
        "y_noise": noise_sample,
        "stationary": True,
        "prop_decrease": min(max(config.reduction_db / 12.0, 0.0), 1.0),
    }
    extended_kwargs: dict[str, float | int | bool | NDArray[np.float32]] = {
        **kwargs,
        "n_std_thresh_stationary": max(0.5, config.sensitivity / 3.0),
        "freq_mask_smooth_hz": max(1.0, config.smoothing * 150.0),
    }

    reduce_fn: Callable[..., NDArray[np.float32]] = nr.reduce_noise
    try:
        reduced = reduce_fn(**extended_kwargs)
    except TypeError:
        reduced = reduce_fn(**kwargs)
    return np.asarray(reduced, dtype=np.float32)


def reduce_noise_profiled(
    audio: AudioArray,
    noise_sample: AudioArray,
    sample_rate: int,
    config: NoiseReductionConfig,
) -> AudioArray:
    if audio.ndim == 1:
        return _reduce_noise_channel(audio, noise_sample, sample_rate, config)

    channels: list[NDArray[np.float32]] = []
    for channel_index in range(audio.shape[1]):
        channels.append(
            _reduce_noise_channel(
                audio[:, channel_index],
                noise_sample[:, channel_index],
                sample_rate,
                config,
            )
        )
    return np.stack(channels, axis=1).astype(np.float32)
