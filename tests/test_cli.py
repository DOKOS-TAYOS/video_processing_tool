from pathlib import Path

import pytest
from typer.testing import CliRunner

from video_processing.cli import app
from video_processing.ffmpeg_io import FFmpegNoAudioStreamError


def test_cli_asks_for_dialogs_when_paths_are_missing(tmp_path, monkeypatch) -> None:
    runner = CliRunner()
    chosen_input = tmp_path / "input.wav"
    chosen_input.write_bytes(b"audio")
    chosen_output = tmp_path / "output"
    chosen_output.mkdir()

    monkeypatch.setattr("video_processing.cli.pick_input_file", lambda: chosen_input)
    monkeypatch.setattr("video_processing.cli.pick_output_directory", lambda: chosen_output)
    monkeypatch.setattr(
        "video_processing.cli.process_audio_job",
        lambda input_path, output_dir, output_format, config: None,
    )

    result = runner.invoke(app, ["process-audio"])

    assert result.exit_code == 0
    assert "Abriendo selector de archivo" in result.stdout
    assert "Abriendo selector de carpeta de salida" in result.stdout


def test_cli_uses_explicit_paths_without_opening_dialogs(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    input_path = tmp_path / "voice.wav"
    input_path.write_bytes(b"audio")
    output_dir = tmp_path / "out"
    received: dict[str, Path | str] = {}

    monkeypatch.setattr(
        "video_processing.cli.pick_input_file",
        lambda: (_ for _ in ()).throw(AssertionError("No deberia abrir selector de archivo")),
    )
    monkeypatch.setattr(
        "video_processing.cli.pick_output_directory",
        lambda: (_ for _ in ()).throw(AssertionError("No deberia abrir selector de carpeta")),
    )

    def fake_process_audio_job(
        input_path: Path, output_dir: Path, output_format: str, config: object
    ) -> None:
        received["input"] = input_path
        received["output_dir"] = output_dir
        received["format"] = output_format

    monkeypatch.setattr("video_processing.cli.process_audio_job", fake_process_audio_job)

    result = runner.invoke(
        app,
        [
            "process-audio",
            "--input",
            str(input_path),
            "--output-dir",
            str(output_dir),
            "--format",
            "mp3",
        ],
    )

    assert result.exit_code == 0
    assert received == {"input": input_path, "output_dir": output_dir, "format": "mp3"}


def test_cli_mode_1_uses_explicit_paths_without_opening_dialogs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = CliRunner()
    input_path = tmp_path / "clip.mp4"
    input_path.write_bytes(b"video")
    output_dir = tmp_path / "out"
    received: dict[str, Path | str] = {}

    monkeypatch.setattr(
        "video_processing.cli.pick_input_file",
        lambda: (_ for _ in ()).throw(AssertionError("No deberia abrir selector de archivo")),
    )
    monkeypatch.setattr(
        "video_processing.cli.pick_output_directory",
        lambda: (_ for _ in ()).throw(AssertionError("No deberia abrir selector de carpeta")),
    )

    def fake_process_mode_1_job(
        input_path: Path, output_dir: Path, output_format: str, config: object
    ) -> None:
        received["input"] = input_path
        received["output_dir"] = output_dir
        received["format"] = output_format

    monkeypatch.setattr("video_processing.cli.process_mode_1_job", fake_process_mode_1_job)

    result = runner.invoke(
        app,
        [
            "mode-1",
            "--input",
            str(input_path),
            "--output-dir",
            str(output_dir),
            "--format",
            "mp3",
        ],
    )

    assert result.exit_code == 0
    assert received == {"input": input_path, "output_dir": output_dir, "format": "mp3"}


def test_cli_mode_1_shows_clear_message_when_media_has_no_audio(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = CliRunner()
    input_path = tmp_path / "clip.mp4"
    input_path.write_bytes(b"video")
    output_dir = tmp_path / "out"

    monkeypatch.setattr(
        "video_processing.cli.process_mode_1_job",
        lambda input_path, output_dir, output_format, config: (_ for _ in ()).throw(
            FFmpegNoAudioStreamError(
                "El archivo no contiene una pista de audio utilizable para el modo 1."
            )
        ),
    )

    result = runner.invoke(
        app,
        ["mode-1", "--input", str(input_path), "--output-dir", str(output_dir)],
    )

    assert result.exit_code == 1
    assert "El archivo no contiene una pista de audio utilizable para el modo 1." in result.stdout
