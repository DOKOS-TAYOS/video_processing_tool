from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray

from video_processing.config import PauseMarkerConfig, SilenceEditingConfig
from video_processing.sync_detection import mix_to_mono

AudioArray = NDArray[np.float32]
type EditOperation = dict[str, str | float]


def _dbfs_to_linear(level_dbfs: float) -> float:
    return float(10 ** (level_dbfs / 20.0))


def _frame_size_samples(sample_rate: int) -> int:
    return max(1, int(round(sample_rate * 0.01)))


def _find_silence_ranges(
    audio: AudioArray,
    sample_rate: int,
    config: SilenceEditingConfig,
) -> list[tuple[int, int]]:
    mono_audio = mix_to_mono(audio)
    frame_size = _frame_size_samples(sample_rate)
    padding = (-mono_audio.shape[0]) % frame_size
    if padding > 0:
        mono_audio = np.pad(mono_audio, (0, padding))

    frames = mono_audio.reshape(-1, frame_size)
    frame_rms = np.sqrt(np.mean(np.square(frames), axis=1))
    silence_mask = frame_rms <= _dbfs_to_linear(config.silence_threshold_dbfs)

    silence_ranges: list[tuple[int, int]] = []
    run_start: int | None = None
    for index, is_silence in enumerate(silence_mask):
        if is_silence and run_start is None:
            run_start = index
        elif not is_silence and run_start is not None:
            silence_ranges.append((run_start * frame_size, index * frame_size))
            run_start = None

    if run_start is not None:
        silence_ranges.append((run_start * frame_size, silence_mask.shape[0] * frame_size))

    min_trim_samples = int(round(config.min_trim_silence_seconds * sample_rate))
    return [
        (start_index, min(end_index, audio.shape[0]))
        for start_index, end_index in silence_ranges
        if end_index - start_index >= min_trim_samples
    ]


def _build_silence(samples: int, audio: AudioArray) -> AudioArray:
    if audio.ndim == 1:
        return np.zeros(samples, dtype=np.float32)
    return np.zeros((samples, audio.shape[1]), dtype=np.float32)


def _tile_across_channels(signal: AudioArray, channels: int) -> AudioArray:
    return np.repeat(signal[:, np.newaxis], channels, axis=1).astype(np.float32)


def _build_beep(
    sample_rate: int,
    config: PauseMarkerConfig,
    audio: AudioArray,
) -> AudioArray:
    beep_samples = max(1, int(round((config.beep_duration_ms / 1000.0) * sample_rate)))
    timeline = np.arange(beep_samples, dtype=np.float32) / float(sample_rate)
    amplitude = _dbfs_to_linear(config.beep_level_dbfs)
    beep = amplitude * np.sin(2.0 * np.pi * config.beep_frequency_hz * timeline)

    fade_samples = min(beep_samples // 2, int(round((config.fade_ms / 1000.0) * sample_rate)))
    if fade_samples > 0:
        fade_curve = np.linspace(0.0, 1.0, fade_samples, dtype=np.float32)
        beep[:fade_samples] *= fade_curve
        beep[-fade_samples:] *= fade_curve[::-1]

    if audio.ndim == 1:
        return np.asarray(beep, dtype=np.float32)
    return _tile_across_channels(np.asarray(beep, dtype=np.float32), audio.shape[1])


def _concatenate_segments(segments: Sequence[AudioArray], audio: AudioArray) -> AudioArray:
    if not segments:
        return _build_silence(0, audio)
    return np.concatenate(segments, axis=0).astype(np.float32)


def apply_silence_edits(
    audio: AudioArray,
    sample_rate: int,
    silence_config: SilenceEditingConfig,
    pause_marker_config: PauseMarkerConfig,
) -> tuple[AudioArray, list[EditOperation]]:
    silence_ranges = _find_silence_ranges(audio, sample_rate, silence_config)
    if not silence_ranges:
        return np.asarray(audio, dtype=np.float32), []

    padding_samples = int(round(silence_config.edge_padding_seconds * sample_rate))
    beep = _build_beep(sample_rate, pause_marker_config, audio)
    segments: list[AudioArray] = []
    edits: list[EditOperation] = []
    cursor = 0
    output_cursor = 0

    for silence_start, silence_end in silence_ranges:
        if silence_start < cursor:
            continue

        segments.append(np.asarray(audio[cursor:silence_start], dtype=np.float32))
        output_cursor += silence_start - cursor

        silence_duration_samples = silence_end - silence_start
        silence_duration_seconds = silence_duration_samples / float(sample_rate)

        if silence_duration_seconds > silence_config.long_pause_seconds:
            replacement = _concatenate_segments(
                [
                    _build_silence(padding_samples, audio),
                    beep,
                    _build_silence(padding_samples, audio),
                ],
                audio,
            )
            kind = "pause_marker"
        else:
            replacement = _build_silence(padding_samples * 2, audio)
            kind = "trim_silence"

        replacement_length = replacement.shape[0]
        segments.append(replacement)
        edit: EditOperation = {
            "kind": kind,
            "source_start_seconds": silence_start / float(sample_rate),
            "source_end_seconds": silence_end / float(sample_rate),
            "output_start_seconds": output_cursor / float(sample_rate),
            "output_end_seconds": (output_cursor + replacement_length) / float(sample_rate),
            "margin_seconds": silence_config.edge_padding_seconds,
        }
        if kind == "pause_marker":
            edit["beep_duration_seconds"] = pause_marker_config.beep_duration_ms / 1000.0
            edit["beep_frequency_hz"] = pause_marker_config.beep_frequency_hz
        edits.append(edit)

        output_cursor += replacement_length
        cursor = silence_end

    segments.append(np.asarray(audio[cursor:], dtype=np.float32))
    return _concatenate_segments(segments, audio), edits


__all__ = ["EditOperation", "apply_silence_edits"]
