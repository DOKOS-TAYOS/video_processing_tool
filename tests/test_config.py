from pathlib import Path

import pytest

from video_processing.config import load_app_config
from video_processing.ffmpeg_io import build_output_path


def test_load_app_config_reads_toml_values(tmp_path: Path) -> None:
    curve_path = tmp_path / "curve.csv"
    curve_path.write_text("frequency_hz,gain_db\n100,0\n1000,1.5\n10000,-2\n", encoding="utf-8")
    config_path = tmp_path / "settings.toml"
    config_path.write_text(
        """
        [app]
        default_output_format = "mp3"
        sample_rate = 44100

        [paths]
        filter_curve_csv = "curve.csv"

        [noise_profile]
        start_seconds = 1.0
        duration_seconds = 1.0

        [noise_reduction]
        reduction_db = 9.0
        sensitivity = 6.0
        smoothing = 3.0

        [loudness]
        target_lufs = -17.0

        [peak_normalization]
        target_peak_db = -1.0

        [compression]
        threshold_db = -18.0
        ratio = 2.5
        attack_ms = 5.0
        release_ms = 100.0
        makeup_gain_db = 1.0

        [sync_detection]
        speech_window_ms = 40
        speech_min_duration_ms = 250
        speech_threshold_dbfs = -30.0
        loud_sound_window_ms = 15
        loud_sound_threshold_dbfs = -12.0

        [silence_editing]
        silence_threshold_dbfs = -36.0
        min_trim_silence_seconds = 0.9
        long_pause_seconds = 2.4
        edge_padding_seconds = 0.15

        [pause_marker]
        beep_frequency_hz = 950.0
        beep_duration_ms = 100
        beep_level_dbfs = -10.0
        fade_ms = 8
        """,
        encoding="utf-8",
    )

    config = load_app_config(config_path)

    assert config.default_output_format == "mp3"
    assert config.sample_rate == 44100
    assert config.paths.filter_curve_csv == curve_path
    assert config.noise_profile.start_seconds == pytest.approx(1.0)
    assert config.compression.ratio == pytest.approx(2.5)
    assert config.sync_detection.speech_window_ms == 40
    assert config.sync_detection.speech_threshold_dbfs == pytest.approx(-30.0)
    assert config.sync_detection.loud_sound_threshold_dbfs == pytest.approx(-12.0)
    assert config.silence_editing.silence_threshold_dbfs == pytest.approx(-36.0)
    assert config.silence_editing.min_trim_silence_seconds == pytest.approx(0.9)
    assert config.pause_marker.beep_frequency_hz == pytest.approx(950.0)
    assert config.pause_marker.beep_duration_ms == 100
    assert config.pause_marker.beep_level_dbfs == pytest.approx(-10.0)


def test_load_app_config_uses_default_sync_detection_when_section_is_missing(
    tmp_path: Path,
) -> None:
    curve_path = tmp_path / "curve.csv"
    curve_path.write_text("frequency_hz,gain_db\n100,0\n1000,1.5\n10000,-2\n", encoding="utf-8")
    config_path = tmp_path / "settings.toml"
    config_path.write_text(
        """
        [app]
        default_output_format = "wav"
        sample_rate = 48000

        [paths]
        filter_curve_csv = "curve.csv"

        [noise_profile]
        start_seconds = 1.0
        duration_seconds = 1.0

        [noise_reduction]
        reduction_db = 9.0
        sensitivity = 6.0
        smoothing = 3.0

        [loudness]
        target_lufs = -17.0

        [peak_normalization]
        target_peak_db = -1.0

        [compression]
        threshold_db = -18.0
        ratio = 2.5
        attack_ms = 5.0
        release_ms = 100.0
        makeup_gain_db = 1.0
        """,
        encoding="utf-8",
    )

    config = load_app_config(config_path)

    assert config.sync_detection.speech_window_ms == 40
    assert config.sync_detection.speech_min_duration_ms == 250
    assert config.sync_detection.speech_threshold_dbfs == pytest.approx(-32.0)
    assert config.sync_detection.loud_sound_window_ms == 15
    assert config.sync_detection.loud_sound_threshold_dbfs == pytest.approx(-12.0)
    assert config.silence_editing.silence_threshold_dbfs == pytest.approx(-38.0)
    assert config.silence_editing.min_trim_silence_seconds == pytest.approx(0.8)
    assert config.silence_editing.long_pause_seconds == pytest.approx(2.0)
    assert config.silence_editing.edge_padding_seconds == pytest.approx(0.1)
    assert config.pause_marker.beep_frequency_hz == pytest.approx(1000.0)
    assert config.pause_marker.beep_duration_ms == 120
    assert config.pause_marker.beep_level_dbfs == pytest.approx(-12.0)
    assert config.pause_marker.fade_ms == 10


def test_build_output_path_adds_processed_suffix_without_overwriting(tmp_path: Path) -> None:
    source_path = tmp_path / "voice.wav"
    source_path.write_bytes(b"dummy")
    output_dir = tmp_path / "exports"
    output_dir.mkdir()
    existing_output = output_dir / "voice__processed.wav"
    existing_output.write_bytes(b"old")

    output_path = build_output_path(
        input_path=source_path, output_dir=output_dir, output_format="wav"
    )

    assert output_path.name == "voice__processed_01.wav"
    assert output_path.parent == output_dir
