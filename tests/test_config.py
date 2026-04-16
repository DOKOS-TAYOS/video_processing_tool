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
        """,
        encoding="utf-8",
    )

    config = load_app_config(config_path)

    assert config.default_output_format == "mp3"
    assert config.sample_rate == 44100
    assert config.paths.filter_curve_csv == curve_path
    assert config.noise_profile.start_seconds == pytest.approx(1.0)
    assert config.compression.ratio == pytest.approx(2.5)


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
