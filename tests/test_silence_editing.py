import numpy as np
import pytest

from video_processing.config import PauseMarkerConfig, SilenceEditingConfig
from video_processing.silence_editing import apply_silence_edits


def build_silence_config() -> SilenceEditingConfig:
    return SilenceEditingConfig(
        silence_threshold_dbfs=-38.0,
        min_trim_silence_seconds=0.8,
        long_pause_seconds=2.0,
        edge_padding_seconds=0.1,
    )


def build_pause_marker_config() -> PauseMarkerConfig:
    return PauseMarkerConfig(
        beep_frequency_hz=1000.0,
        beep_duration_ms=120,
        beep_level_dbfs=-12.0,
        fade_ms=10,
    )


def test_apply_silence_edits_trims_regular_silence_with_edge_padding() -> None:
    sample_rate = 1000
    audio = np.concatenate(
        [
            np.ones(500, dtype=np.float32) * 0.4,
            np.zeros(1000, dtype=np.float32),
            np.ones(500, dtype=np.float32) * 0.4,
        ]
    )

    edited_audio, edits = apply_silence_edits(
        audio=audio,
        sample_rate=sample_rate,
        silence_config=build_silence_config(),
        pause_marker_config=build_pause_marker_config(),
    )

    assert edited_audio.shape[0] == 1200
    assert edits == [
        {
            "kind": "trim_silence",
            "source_start_seconds": pytest.approx(0.5, abs=0.01),
            "source_end_seconds": pytest.approx(1.5, abs=0.01),
            "output_start_seconds": pytest.approx(0.5, abs=0.01),
            "output_end_seconds": pytest.approx(0.7, abs=0.01),
            "margin_seconds": pytest.approx(0.1, abs=0.001),
        }
    ]


def test_apply_silence_edits_replaces_long_pause_with_beep_marker() -> None:
    sample_rate = 1000
    audio = np.concatenate(
        [
            np.ones(500, dtype=np.float32) * 0.4,
            np.zeros(2500, dtype=np.float32),
            np.ones(500, dtype=np.float32) * 0.4,
        ]
    )

    edited_audio, edits = apply_silence_edits(
        audio=audio,
        sample_rate=sample_rate,
        silence_config=build_silence_config(),
        pause_marker_config=build_pause_marker_config(),
    )

    assert edited_audio.shape[0] == 1320
    assert np.max(np.abs(edited_audio[580:740])) > 0.0
    assert edits == [
        {
            "kind": "pause_marker",
            "source_start_seconds": pytest.approx(0.5, abs=0.01),
            "source_end_seconds": pytest.approx(3.0, abs=0.01),
            "output_start_seconds": pytest.approx(0.5, abs=0.01),
            "output_end_seconds": pytest.approx(0.82, abs=0.01),
            "margin_seconds": pytest.approx(0.1, abs=0.001),
            "beep_duration_seconds": pytest.approx(0.12, abs=0.001),
            "beep_frequency_hz": pytest.approx(1000.0, abs=0.001),
        }
    ]
