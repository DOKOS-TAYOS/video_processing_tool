from __future__ import annotations

from dataclasses import dataclass
from math import ceil

import numpy as np
from numpy.typing import NDArray

from video_processing.config import SyncDetectionConfig

AudioArray = NDArray[np.float32]


@dataclass(frozen=True)
class DetectedAnchor:
    seconds: float
    confidence: float


@dataclass(frozen=True)
class SyncAnchor:
    source_seconds: float
    processed_seconds: float
    confidence: float


@dataclass(frozen=True)
class Mode1SyncAnchors:
    speech_start: SyncAnchor | None
    first_loud_sound: SyncAnchor | None


def mix_to_mono(audio: AudioArray) -> AudioArray:
    if audio.ndim == 1:
        return np.asarray(audio, dtype=np.float32)
    return np.asarray(audio.mean(axis=1), dtype=np.float32)


def _dbfs_to_linear(level_dbfs: float) -> float:
    return float(10 ** (level_dbfs / 20.0))


def _normalized_confidence(measured_level: float, threshold_level: float) -> float:
    scale = max(threshold_level, 1e-6)
    margin = max(0.0, measured_level - threshold_level)
    return float(min(1.0, margin / scale))


def _window_size_samples(window_ms: int, sample_rate: int) -> int:
    return max(1, int(round((window_ms / 1000.0) * sample_rate)))


def detect_speech_start(
    audio: AudioArray,
    sample_rate: int,
    config: SyncDetectionConfig,
) -> DetectedAnchor | None:
    mono_audio = mix_to_mono(audio)
    window_size = _window_size_samples(config.speech_window_ms, sample_rate)
    required_windows = max(1, ceil(config.speech_min_duration_ms / config.speech_window_ms))
    threshold_level = _dbfs_to_linear(config.speech_threshold_dbfs)

    if mono_audio.size < window_size:
        return None

    window_rms: list[float] = []
    window_starts: list[int] = []
    for start_index in range(0, mono_audio.size - window_size + 1, window_size):
        window = mono_audio[start_index : start_index + window_size]
        rms = float(np.sqrt(np.mean(np.square(window, dtype=np.float32), dtype=np.float32)))
        window_rms.append(rms)
        window_starts.append(start_index)

    if len(window_rms) < required_windows:
        return None

    for index in range(len(window_rms) - required_windows + 1):
        candidate = window_rms[index : index + required_windows]
        if all(rms >= threshold_level for rms in candidate):
            mean_rms = float(np.mean(candidate, dtype=np.float32))
            return DetectedAnchor(
                seconds=window_starts[index] / sample_rate,
                confidence=_normalized_confidence(mean_rms, threshold_level),
            )

    return None


def detect_first_loud_sound(
    audio: AudioArray,
    sample_rate: int,
    config: SyncDetectionConfig,
) -> DetectedAnchor | None:
    mono_audio = mix_to_mono(audio)
    window_size = _window_size_samples(config.loud_sound_window_ms, sample_rate)
    threshold_level = _dbfs_to_linear(config.loud_sound_threshold_dbfs)

    if mono_audio.size == 0:
        return None

    kernel = np.ones(window_size, dtype=np.float32) / float(window_size)
    envelope = np.convolve(np.abs(mono_audio), kernel, mode="same")
    indices = np.flatnonzero(envelope >= threshold_level)
    if indices.size == 0:
        return None

    first_index = int(indices[0])
    measured_level = float(envelope[first_index])
    return DetectedAnchor(
        seconds=first_index / sample_rate,
        confidence=_normalized_confidence(measured_level, threshold_level),
    )


def _pair_anchor(
    source_anchor: DetectedAnchor | None,
    processed_anchor: DetectedAnchor | None,
) -> SyncAnchor | None:
    if source_anchor is None or processed_anchor is None:
        return None

    return SyncAnchor(
        source_seconds=source_anchor.seconds,
        processed_seconds=processed_anchor.seconds,
        confidence=min(source_anchor.confidence, processed_anchor.confidence),
    )


def recommend_anchor_name(
    speech_start: SyncAnchor | None,
    first_loud_sound: SyncAnchor | None,
) -> str | None:
    if speech_start is not None:
        return "speech_start"
    if first_loud_sound is not None:
        return "first_loud_sound"
    return None


def detect_mode_1_anchors(
    source_audio: AudioArray,
    processed_audio: AudioArray,
    sample_rate: int,
    config: SyncDetectionConfig,
) -> tuple[Mode1SyncAnchors, str | None, list[str]]:
    source_speech = detect_speech_start(source_audio, sample_rate, config)
    processed_speech = detect_speech_start(processed_audio, sample_rate, config)
    source_loud_sound = detect_first_loud_sound(source_audio, sample_rate, config)
    processed_loud_sound = detect_first_loud_sound(processed_audio, sample_rate, config)

    speech_start = _pair_anchor(source_speech, processed_speech)
    first_loud_sound = _pair_anchor(source_loud_sound, processed_loud_sound)
    warnings: list[str] = []

    if speech_start is None:
        warnings.append("No se detecto un inicio de habla fiable.")
    if first_loud_sound is None:
        warnings.append("No se detecto un primer sonido fuerte fiable.")

    anchors = Mode1SyncAnchors(
        speech_start=speech_start,
        first_loud_sound=first_loud_sound,
    )
    return anchors, recommend_anchor_name(speech_start, first_loud_sound), warnings


__all__ = [
    "DetectedAnchor",
    "Mode1SyncAnchors",
    "SyncAnchor",
    "detect_first_loud_sound",
    "detect_mode_1_anchors",
    "detect_speech_start",
    "mix_to_mono",
    "recommend_anchor_name",
]
