from __future__ import annotations

from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from video_processing.audio_pipeline.dynamics import apply_peak_normalization, compress_audio
from video_processing.audio_pipeline.filter_curve import apply_filter_curve
from video_processing.audio_pipeline.loudness import normalize_loudness
from video_processing.audio_pipeline.noise import extract_noise_sample, reduce_noise_profiled
from video_processing.config import AppConfig

AudioArray = NDArray[np.float32]


def run_audio_pipeline(
    audio: AudioArray,
    sample_rate: int,
    config: AppConfig,
    curve_csv_path: Path,
) -> AudioArray:
    noise_sample = extract_noise_sample(
        audio=audio,
        sample_rate=sample_rate,
        start_seconds=config.noise_profile.start_seconds,
        duration_seconds=config.noise_profile.duration_seconds,
    )
    reduced_audio = reduce_noise_profiled(audio, noise_sample, sample_rate, config.noise_reduction)
    loudness_normalized_audio = normalize_loudness(
        reduced_audio,
        sample_rate,
        config.loudness.target_lufs,
    )
    curve_applied_audio = apply_filter_curve(
        loudness_normalized_audio,
        sample_rate,
        curve_csv_path,
    )
    peak_normalized_audio = apply_peak_normalization(
        curve_applied_audio,
        config.peak_normalization.target_peak_db,
    )
    compressed_audio = compress_audio(peak_normalized_audio, sample_rate, config.compression)
    return np.asarray(compressed_audio, dtype=np.float32)


__all__ = [
    "apply_filter_curve",
    "apply_peak_normalization",
    "compress_audio",
    "extract_noise_sample",
    "normalize_loudness",
    "reduce_noise_profiled",
    "run_audio_pipeline",
]
