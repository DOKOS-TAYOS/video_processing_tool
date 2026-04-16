from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from scipy import signal

AudioArray = NDArray[np.float32]


def _load_curve_points(curve_csv_path: Path) -> tuple[np.ndarray, np.ndarray]:
    frequencies: list[float] = []
    gains_db: list[float] = []

    with curve_csv_path.open("r", encoding="utf-8", newline="") as curve_file:
        reader = csv.DictReader(curve_file)
        for row in reader:
            frequencies.append(float(row["frequency_hz"]))
            gains_db.append(float(row["gain_db"]))

    return np.asarray(frequencies, dtype=np.float64), np.asarray(gains_db, dtype=np.float64)


def _design_filter(sample_rate: int, curve_csv_path: Path) -> NDArray[np.float64]:
    frequencies, gains_db = _load_curve_points(curve_csv_path)
    nyquist = sample_rate / 2.0

    clipped_frequencies = np.clip(frequencies, 0.0, nyquist)
    if clipped_frequencies.size == 0:
        return np.asarray([1.0], dtype=np.float64)

    if clipped_frequencies[0] > 0.0:
        clipped_frequencies = np.insert(clipped_frequencies, 0, 0.0)
        gains_db = np.insert(gains_db, 0, gains_db[0])
    if clipped_frequencies[-1] < nyquist:
        clipped_frequencies = np.append(clipped_frequencies, nyquist)
        gains_db = np.append(gains_db, gains_db[-1])

    normalized_frequency = clipped_frequencies / nyquist if nyquist else clipped_frequencies
    gains_linear = np.power(10.0, gains_db / 20.0)
    return signal.firwin2(numtaps=513, freq=normalized_frequency, gain=gains_linear)


def _apply_filter_to_channel(
    audio: NDArray[np.float32],
    taps: NDArray[np.float64],
) -> NDArray[np.float32]:
    if taps.size == 1:
        return audio.astype(np.float32)

    pad_length = 3 * (taps.size - 1)
    if audio.shape[0] <= pad_length:
        filtered = signal.lfilter(taps, [1.0], audio)
    else:
        filtered = signal.filtfilt(taps, [1.0], audio)
    return np.asarray(filtered, dtype=np.float32)


def apply_filter_curve(audio: AudioArray, sample_rate: int, curve_csv_path: Path) -> AudioArray:
    taps = _design_filter(sample_rate, curve_csv_path)

    if audio.ndim == 1:
        return _apply_filter_to_channel(audio, taps)

    channels = [
        _apply_filter_to_channel(audio[:, channel_index], taps)
        for channel_index in range(audio.shape[1])
    ]
    return np.stack(channels, axis=1).astype(np.float32)
