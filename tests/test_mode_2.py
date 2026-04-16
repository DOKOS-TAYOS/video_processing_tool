import json
from pathlib import Path

import numpy as np
import pytest

from video_processing.config import load_app_config
from video_processing.mode_2 import process_mode_2_job


def write_config(tmp_path: Path, curve_path: Path) -> Path:
    config_path = tmp_path / "settings.toml"
    config_path.write_text(
        f"""
        [app]
        default_output_format = "wav"
        sample_rate = 1000

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

        [silence_editing]
        silence_threshold_dbfs = -38.0
        min_trim_silence_seconds = 0.8
        long_pause_seconds = 2.0
        edge_padding_seconds = 0.1

        [pause_marker]
        beep_frequency_hz = 1000.0
        beep_duration_ms = 120
        beep_level_dbfs = -12.0
        fade_ms = 10
        """,
        encoding="utf-8",
    )
    return config_path


def test_process_mode_2_job_writes_processed_audio_and_extended_edit_plan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    video_path = tmp_path / "clip.mp4"
    audio_path = tmp_path / "voice.wav"
    video_path.write_bytes(b"video")
    audio_path.write_bytes(b"audio")
    curve_path = tmp_path / "curve.csv"
    curve_path.write_text("frequency_hz,gain_db\n20,0\n1000,0\n20000,0\n", encoding="utf-8")
    config = load_app_config(write_config(tmp_path, curve_path))
    output_dir = tmp_path / "out"
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()

    external_audio = np.zeros(3000, dtype=np.float32)
    external_audio[1000:1300] = 0.08
    external_audio[1800:1810] = 0.95
    camera_audio = np.zeros(3000, dtype=np.float32)
    camera_audio[500:800] = 0.08
    camera_audio[700:710] = 0.95

    monkeypatch.setattr("video_processing.mode_2.ensure_ffmpeg_available", lambda: None)
    monkeypatch.setattr("video_processing.mode_2.create_runtime_directory", lambda _: runtime_dir)
    monkeypatch.setattr("video_processing.mode_2.remove_runtime_directory", lambda _: None)

    def fake_decode_audio_file(
        input_path: Path,
        sample_rate: int,
        runtime_dir: Path,
        missing_audio_message: str | None = None,
    ) -> tuple[np.ndarray, int]:
        if input_path == video_path:
            return camera_audio, sample_rate
        if input_path == audio_path:
            return external_audio, sample_rate
        raise AssertionError(f"Ruta inesperada: {input_path}")

    monkeypatch.setattr("video_processing.mode_2.decode_audio_file", fake_decode_audio_file)
    monkeypatch.setattr(
        "video_processing.mode_2.run_audio_pipeline",
        lambda audio, sample_rate, config, curve_csv_path: audio.copy(),
    )
    monkeypatch.setattr(
        "video_processing.mode_2.encode_audio_file",
        lambda audio, sample_rate, output_path, runtime_dir: (
            output_path.write_bytes(b"audio") or output_path
        ),
    )
    monkeypatch.setattr(
        "video_processing.mode_2.apply_silence_edits",
        lambda audio, sample_rate, silence_config, pause_marker_config: (audio, []),
    )

    result = process_mode_2_job(
        video_path=video_path,
        audio_path=audio_path,
        output_dir=output_dir,
        output_format="wav",
        config=config,
    )

    assert result.output_path.exists()
    assert result.edit_plan_path.exists()
    with result.edit_plan_path.open("r", encoding="utf-8") as edit_plan_file:
        payload = json.load(edit_plan_file)
    assert payload["input_media_path"] == str(audio_path)
    assert payload["inputs"] == {
        "input_video_path": str(video_path),
        "input_external_audio_path": str(audio_path),
    }
    assert payload["video_sync"]["external_audio_offset_seconds"] == pytest.approx(0.5, abs=0.05)
    assert payload["video_sync"]["offset_anchor"] == "speech_start"
    assert payload["edits"] == []
    assert payload["anchors"]["speech_start"]["source_seconds"] == pytest.approx(1.0, abs=0.05)


def test_process_mode_2_job_exports_null_offset_and_warning_when_no_anchor_is_shared(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    video_path = tmp_path / "clip.mp4"
    audio_path = tmp_path / "voice.wav"
    video_path.write_bytes(b"video")
    audio_path.write_bytes(b"audio")
    curve_path = tmp_path / "curve.csv"
    curve_path.write_text("frequency_hz,gain_db\n20,0\n1000,0\n20000,0\n", encoding="utf-8")
    config = load_app_config(write_config(tmp_path, curve_path))
    output_dir = tmp_path / "out"
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()

    external_audio = np.zeros(3000, dtype=np.float32)
    external_audio[1000:1300] = 0.08
    camera_audio = np.zeros(3000, dtype=np.float32)

    monkeypatch.setattr("video_processing.mode_2.ensure_ffmpeg_available", lambda: None)
    monkeypatch.setattr("video_processing.mode_2.create_runtime_directory", lambda _: runtime_dir)
    monkeypatch.setattr("video_processing.mode_2.remove_runtime_directory", lambda _: None)

    def fake_decode_audio_file(
        input_path: Path,
        sample_rate: int,
        runtime_dir: Path,
        missing_audio_message: str | None = None,
    ) -> tuple[np.ndarray, int]:
        if input_path == video_path:
            return camera_audio, sample_rate
        if input_path == audio_path:
            return external_audio, sample_rate
        raise AssertionError(f"Ruta inesperada: {input_path}")

    monkeypatch.setattr("video_processing.mode_2.decode_audio_file", fake_decode_audio_file)
    monkeypatch.setattr(
        "video_processing.mode_2.run_audio_pipeline",
        lambda audio, sample_rate, config, curve_csv_path: audio.copy(),
    )
    monkeypatch.setattr(
        "video_processing.mode_2.encode_audio_file",
        lambda audio, sample_rate, output_path, runtime_dir: (
            output_path.write_bytes(b"audio") or output_path
        ),
    )
    monkeypatch.setattr(
        "video_processing.mode_2.apply_silence_edits",
        lambda audio, sample_rate, silence_config, pause_marker_config: (audio, []),
    )

    result = process_mode_2_job(
        video_path=video_path,
        audio_path=audio_path,
        output_dir=output_dir,
        output_format="wav",
        config=config,
    )

    assert result.recommended_anchor == "speech_start"
    assert (
        "No se pudo calcular un offset fiable entre el audio externo y el audio de camara."
        in result.warnings
    )
    with result.edit_plan_path.open("r", encoding="utf-8") as edit_plan_file:
        payload = json.load(edit_plan_file)
    assert payload["video_sync"]["external_audio_offset_seconds"] is None
    assert payload["video_sync"]["offset_anchor"] is None
