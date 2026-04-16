from pathlib import Path

import pytest

from video_processing.ffmpeg_io import (
    FFmpegCommandError,
    FFmpegNoAudioStreamError,
    decode_audio_file,
)


def test_decode_audio_file_reports_missing_audio_stream_clearly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_path = tmp_path / "input.mp4"
    input_path.write_bytes(b"video")
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()

    monkeypatch.setattr(
        "video_processing.ffmpeg_io._run_ffmpeg",
        lambda command: (_ for _ in ()).throw(
            FFmpegCommandError("Output file #0 does not contain any stream")
        ),
    )

    with pytest.raises(FFmpegNoAudioStreamError) as exc_info:
        decode_audio_file(input_path=input_path, sample_rate=48000, runtime_dir=runtime_dir)

    assert str(exc_info.value) == (
        "El archivo no contiene una pista de audio utilizable para el modo 1."
    )
