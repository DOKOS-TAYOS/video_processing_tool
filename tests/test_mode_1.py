import json
from pathlib import Path

import numpy as np
import pytest

from video_processing.config import load_app_config
from video_processing.mode_1 import process_mode_1_job
from video_processing.sync_detection import Mode1SyncAnchors, SyncAnchor


def write_config(tmp_path: Path, curve_path: Path) -> Path:
    config_path = tmp_path / "settings.toml"
    config_path.write_text(
        f"""
        [app]
        default_output_format = "wav"
        sample_rate = 48000

        [paths]
        filter_curve_csv = "{curve_path.as_posix()}"
        default_filter_curve_csv = "{curve_path.as_posix()}"

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
        speech_threshold_dbfs = -32.0
        loud_sound_window_ms = 15
        loud_sound_threshold_dbfs = -12.0
        """,
        encoding="utf-8",
    )
    return config_path


def test_process_mode_1_job_writes_processed_audio_and_edit_plan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_path = tmp_path / "clip.mp4"
    input_path.write_bytes(b"video")
    curve_path = tmp_path / "curve.csv"
    curve_path.write_text("frequency_hz,gain_db\n20,0\n1000,0\n20000,0\n", encoding="utf-8")
    config = load_app_config(write_config(tmp_path, curve_path))
    output_dir = tmp_path / "out"
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()
    source_audio = np.ones(4800, dtype=np.float32) * 0.05
    processed_audio = np.ones(4800, dtype=np.float32) * 0.08

    monkeypatch.setattr("video_processing.mode_1.ensure_ffmpeg_available", lambda: None)
    monkeypatch.setattr("video_processing.mode_1.create_runtime_directory", lambda _: runtime_dir)
    monkeypatch.setattr("video_processing.mode_1.remove_runtime_directory", lambda _: None)
    monkeypatch.setattr(
        "video_processing.mode_1.decode_audio_file",
        lambda input_path, sample_rate, runtime_dir: (source_audio, sample_rate),
    )
    monkeypatch.setattr(
        "video_processing.mode_1.run_audio_pipeline",
        lambda audio, sample_rate, config, curve_csv_path: processed_audio,
    )
    monkeypatch.setattr(
        "video_processing.mode_1.encode_audio_file",
        lambda audio, sample_rate, output_path, runtime_dir: (
            output_path.write_bytes(b"audio") or output_path
        ),
    )
    monkeypatch.setattr(
        "video_processing.mode_1.detect_mode_1_anchors",
        lambda source_audio, processed_audio, sample_rate, config: (
            Mode1SyncAnchors(
                speech_start=SyncAnchor(
                    source_seconds=0.5,
                    processed_seconds=0.5,
                    confidence=0.8,
                ),
                first_loud_sound=SyncAnchor(
                    source_seconds=1.1,
                    processed_seconds=1.1,
                    confidence=0.9,
                ),
            ),
            "speech_start",
            [],
        ),
    )

    result = process_mode_1_job(
        input_path=input_path,
        output_dir=output_dir,
        output_format="wav",
        config=config,
    )

    assert result.output_path.exists()
    assert result.edit_plan_path.exists()
    assert result.recommended_anchor == "speech_start"
    with result.edit_plan_path.open("r", encoding="utf-8") as edit_plan_file:
        payload = json.load(edit_plan_file)
    assert payload["input_media_path"] == str(input_path)
    assert payload["processed_audio_path"] == str(result.output_path)
    assert payload["recommended_anchor"] == "speech_start"
    assert payload["anchors"]["speech_start"]["source_seconds"] == pytest.approx(0.5)
    assert payload["anchors"]["first_loud_sound"]["processed_seconds"] == pytest.approx(1.1)
