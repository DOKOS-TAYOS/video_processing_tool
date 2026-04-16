import numpy as np
import pytest

from video_processing.config import SyncDetectionConfig
from video_processing.sync_detection import (
    SyncAnchor,
    detect_first_loud_sound,
    detect_mode_1_anchors,
    detect_speech_start,
    mix_to_mono,
)


def build_sync_config() -> SyncDetectionConfig:
    return SyncDetectionConfig(
        speech_window_ms=40,
        speech_min_duration_ms=250,
        speech_threshold_dbfs=-32.0,
        loud_sound_window_ms=15,
        loud_sound_threshold_dbfs=-12.0,
    )


def test_mix_to_mono_averages_channels() -> None:
    audio = np.array([[1.0, -1.0], [0.5, 0.0]], dtype=np.float32)

    mono = mix_to_mono(audio)

    assert mono.ndim == 1
    assert np.allclose(mono, np.array([0.0, 0.25], dtype=np.float32))


def test_detect_speech_start_finds_first_sustained_energy_block() -> None:
    sample_rate = 1000
    silence = np.zeros(1000, dtype=np.float32)
    voice = np.ones(300, dtype=np.float32) * 0.08
    tail = np.zeros(200, dtype=np.float32)
    audio = np.concatenate([silence, voice, tail])

    detected = detect_speech_start(audio, sample_rate, build_sync_config())

    assert detected is not None
    assert detected.seconds == pytest.approx(1.0, abs=0.05)
    assert detected.confidence > 0.0


def test_detect_first_loud_sound_finds_first_peak() -> None:
    sample_rate = 1000
    audio = np.zeros(2000, dtype=np.float32)
    audio[700:710] = 0.95
    audio[1200:1210] = 0.95

    detected = detect_first_loud_sound(audio, sample_rate, build_sync_config())

    assert detected is not None
    assert detected.seconds == pytest.approx(0.7, abs=0.03)
    assert detected.confidence > 0.0


def test_detect_mode_1_anchors_returns_warning_when_no_anchor_is_detected() -> None:
    audio = np.zeros(2000, dtype=np.float32)

    anchors, recommended_anchor, warnings = detect_mode_1_anchors(
        source_audio=audio,
        processed_audio=audio,
        sample_rate=1000,
        config=build_sync_config(),
    )

    assert recommended_anchor is None
    assert anchors.speech_start is None
    assert anchors.first_loud_sound is None
    assert warnings == [
        "No se detecto un inicio de habla fiable.",
        "No se detecto un primer sonido fuerte fiable.",
    ]


def test_detect_mode_1_anchors_prefers_speech_start_when_both_are_available() -> None:
    source_audio = np.zeros(3000, dtype=np.float32)
    source_audio[1000:1300] = 0.08
    source_audio[1800:1810] = 0.95
    processed_audio = source_audio.copy()

    anchors, recommended_anchor, warnings = detect_mode_1_anchors(
        source_audio=source_audio,
        processed_audio=processed_audio,
        sample_rate=1000,
        config=build_sync_config(),
    )

    assert warnings == []
    assert recommended_anchor == "speech_start"
    assert anchors.speech_start == SyncAnchor(
        source_seconds=pytest.approx(1.0, abs=0.05),  # type: ignore[arg-type]
        processed_seconds=pytest.approx(1.0, abs=0.05),  # type: ignore[arg-type]
        confidence=pytest.approx(anchors.speech_start.confidence, abs=1e-6),  # type: ignore[union-attr]
    )
    assert anchors.first_loud_sound is not None
