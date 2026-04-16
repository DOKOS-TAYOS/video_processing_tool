from pathlib import Path

import numpy as np
import soundfile as sf

from video_processing.config import load_app_config
from video_processing.ffmpeg_io import FFmpegNotAvailableError
from video_processing.processing import process_audio_job


def create_test_wave(path: Path, sample_rate: int = 48000, seconds: int = 3) -> None:
    timeline = np.linspace(0, seconds, sample_rate * seconds, endpoint=False)
    signal = (0.05 * np.sin(2 * np.pi * 220 * timeline)).astype(np.float32)
    sf.write(path, signal, sample_rate)


def test_process_audio_job_uses_default_curve_when_custom_curve_is_missing(tmp_path: Path) -> None:
    input_path = tmp_path / "input.wav"
    create_test_wave(input_path)
    default_curve = tmp_path / "default_curve.csv"
    default_curve.write_text("frequency_hz,gain_db\n20,0\n1000,0\n20000,0\n", encoding="utf-8")
    config_path = tmp_path / "settings.toml"
    config_path.write_text(
        f"""
        [app]
        default_output_format = "wav"
        sample_rate = 48000

        [paths]
        filter_curve_csv = "missing_curve.csv"
        default_filter_curve_csv = "{default_curve.as_posix()}"

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

    result = process_audio_job(
        input_path=input_path,
        output_dir=tmp_path / "out",
        output_format="wav",
        config=load_app_config(config_path),
    )

    assert result.output_path.exists()
    assert result.used_curve_path == default_curve
    assert result.warnings == [
        "No se encontro la curva configurada. Se usara la curva por defecto del proyecto."
    ]


def test_process_audio_job_exports_mp3_when_requested(tmp_path: Path) -> None:
    input_path = tmp_path / "input.wav"
    create_test_wave(input_path)
    curve_path = tmp_path / "curve.csv"
    curve_path.write_text("frequency_hz,gain_db\n20,0\n1000,0\n20000,0\n", encoding="utf-8")
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
        """,
        encoding="utf-8",
    )

    result = process_audio_job(
        input_path=input_path,
        output_dir=tmp_path / "out",
        output_format="mp3",
        config=load_app_config(config_path),
    )

    assert result.output_path.suffix == ".mp3"
    assert result.output_path.exists()


def test_process_audio_job_fails_clearly_when_ffmpeg_is_missing(
    tmp_path: Path, monkeypatch
) -> None:
    input_path = tmp_path / "input.wav"
    create_test_wave(input_path)
    curve_path = tmp_path / "curve.csv"
    curve_path.write_text("frequency_hz,gain_db\n20,0\n1000,0\n20000,0\n", encoding="utf-8")
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
        """,
        encoding="utf-8",
    )
    monkeypatch.setattr("video_processing.ffmpeg_io.shutil.which", lambda _: None)

    try:
        process_audio_job(
            input_path=input_path,
            output_dir=tmp_path / "out",
            output_format="wav",
            config=load_app_config(config_path),
        )
    except FFmpegNotAvailableError as exc:
        assert (
            str(exc)
            == "FFmpeg no esta disponible en el sistema. Instala ffmpeg y vuelve a intentarlo."
        )
    else:
        raise AssertionError("Se esperaba FFmpegNotAvailableError")
