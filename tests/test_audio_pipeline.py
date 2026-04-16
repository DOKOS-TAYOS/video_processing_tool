from pathlib import Path

import numpy as np
import pyloudnorm as pyln
import pytest

from video_processing.audio_pipeline import (
    apply_peak_normalization,
    extract_noise_sample,
    normalize_loudness,
    run_audio_pipeline,
)
from video_processing.config import (
    AppConfig,
    CompressionConfig,
    FilterCurvePaths,
    LoudnessConfig,
    NoiseProfileConfig,
    NoiseReductionConfig,
    PeakNormalizationConfig,
)


def build_config(curve_path: Path) -> AppConfig:
    return AppConfig(
        default_output_format="wav",
        sample_rate=48000,
        paths=FilterCurvePaths(filter_curve_csv=curve_path, default_filter_curve_csv=curve_path),
        noise_profile=NoiseProfileConfig(start_seconds=1.0, duration_seconds=1.0),
        noise_reduction=NoiseReductionConfig(reduction_db=9.0, sensitivity=6.0, smoothing=3.0),
        loudness=LoudnessConfig(target_lufs=-17.0),
        peak_normalization=PeakNormalizationConfig(target_peak_db=-1.0),
        compression=CompressionConfig(
            threshold_db=-18.0,
            ratio=2.5,
            attack_ms=5.0,
            release_ms=100.0,
            makeup_gain_db=1.0,
        ),
    )


def test_extract_noise_sample_uses_interval_between_one_and_two_seconds() -> None:
    sample_rate = 10
    audio = np.arange(40, dtype=np.float32)

    noise_sample = extract_noise_sample(
        audio=audio,
        sample_rate=sample_rate,
        start_seconds=1.0,
        duration_seconds=1.0,
    )

    assert np.array_equal(noise_sample, np.arange(10, 20, dtype=np.float32))


def test_apply_peak_normalization_targets_minus_one_dbfs() -> None:
    audio = np.array([0.1, -0.1, 0.5, -0.5], dtype=np.float32)

    normalized = apply_peak_normalization(audio=audio, target_peak_db=-1.0)

    expected_peak = 10 ** (-1.0 / 20.0)
    assert np.max(np.abs(normalized)) == pytest.approx(expected_peak, rel=1e-3)


def test_run_audio_pipeline_preserves_stage_order(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    curve_path = tmp_path / "curve.csv"
    curve_path.write_text("frequency_hz,gain_db\n20,0\n1000,0\n20000,0\n", encoding="utf-8")
    config = build_config(curve_path)
    audio = np.ones(48000, dtype=np.float32) * 0.1
    order: list[str] = []

    def fake_reduce(
        audio_in: np.ndarray,
        noise_sample: np.ndarray,
        sample_rate: int,
        config: object,
    ) -> np.ndarray:
        order.append("noise_reduction")
        return audio_in

    def fake_normalize(audio_in: np.ndarray, sample_rate: int, target_lufs: float) -> np.ndarray:
        order.append("loudness")
        return audio_in

    def fake_curve(audio_in: np.ndarray, sample_rate: int, curve_csv_path: Path) -> np.ndarray:
        order.append("filter_curve")
        return audio_in

    def fake_peak(audio_in: np.ndarray, target_peak_db: float) -> np.ndarray:
        order.append("peak")
        return audio_in

    def fake_compress(audio_in: np.ndarray, sample_rate: int, config: object) -> np.ndarray:
        order.append("compression")
        return audio_in

    monkeypatch.setattr("video_processing.audio_pipeline.reduce_noise_profiled", fake_reduce)
    monkeypatch.setattr("video_processing.audio_pipeline.normalize_loudness", fake_normalize)
    monkeypatch.setattr("video_processing.audio_pipeline.apply_filter_curve", fake_curve)
    monkeypatch.setattr("video_processing.audio_pipeline.apply_peak_normalization", fake_peak)
    monkeypatch.setattr("video_processing.audio_pipeline.compress_audio", fake_compress)

    result = run_audio_pipeline(
        audio=audio,
        sample_rate=48000,
        config=config,
        curve_csv_path=curve_path,
    )

    assert order == ["noise_reduction", "loudness", "filter_curve", "peak", "compression"]
    assert result.shape == audio.shape


def test_normalize_loudness_targets_requested_lufs(tmp_path: Path) -> None:
    curve_path = tmp_path / "curve.csv"
    curve_path.write_text("frequency_hz,gain_db\n20,0\n1000,0\n20000,0\n", encoding="utf-8")
    config = build_config(curve_path)
    seconds = 3
    timeline = np.linspace(0, seconds, config.sample_rate * seconds, endpoint=False)
    audio = (0.02 * np.sin(2 * np.pi * 220 * timeline)).astype(np.float32)

    processed = normalize_loudness(
        audio=audio,
        sample_rate=config.sample_rate,
        target_lufs=config.loudness.target_lufs,
    )
    meter = pyln.Meter(config.sample_rate)
    loudness = meter.integrated_loudness(processed.astype(np.float64))

    assert loudness == pytest.approx(config.loudness.target_lufs, abs=0.3)
