from __future__ import annotations

import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Final

import numpy as np
import soundfile as sf
from numpy.typing import NDArray


class FFmpegNotAvailableError(RuntimeError):
    """Raised when FFmpeg cannot be found."""


class FFmpegCommandError(RuntimeError):
    """Raised when an FFmpeg command fails."""


AudioArray = NDArray[np.float32]
PCM_SUBTYPE: Final[str] = "PCM_16"


def ensure_ffmpeg_available() -> None:
    if shutil.which("ffmpeg") is None:
        message = "FFmpeg no esta disponible en el sistema. Instala ffmpeg y vuelve a intentarlo."
        raise FFmpegNotAvailableError(message)


def build_output_path(input_path: Path, output_dir: Path, output_format: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = f".{output_format.lower()}"
    base_name = f"{input_path.stem}__processed"
    candidate = output_dir / f"{base_name}{suffix}"

    if candidate.resolve() != input_path.resolve() and not candidate.exists():
        return candidate

    index = 1
    while True:
        alternative = output_dir / f"{base_name}_{index:02d}{suffix}"
        if alternative.resolve() != input_path.resolve() and not alternative.exists():
            return alternative
        index += 1


def create_runtime_directory(base_dir: Path) -> Path:
    runtime_root = base_dir / ".tmp" / "runtime"
    runtime_root.mkdir(parents=True, exist_ok=True)
    job_dir = runtime_root / uuid.uuid4().hex
    job_dir.mkdir(parents=True, exist_ok=True)
    return job_dir


def remove_runtime_directory(runtime_dir: Path) -> None:
    shutil.rmtree(runtime_dir, ignore_errors=True)


def _run_ffmpeg(command: list[str]) -> None:
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        stderr = completed.stderr.strip() or "FFmpeg ha fallado sin mensaje detallado."
        raise FFmpegCommandError(stderr)


def decode_audio_file(
    input_path: Path,
    sample_rate: int,
    runtime_dir: Path,
) -> tuple[AudioArray, int]:
    decoded_path = runtime_dir / "decoded.wav"
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-vn",
        "-ar",
        str(sample_rate),
        "-acodec",
        "pcm_s16le",
        str(decoded_path),
    ]
    _run_ffmpeg(command)
    audio, detected_sample_rate = sf.read(decoded_path, dtype="float32", always_2d=False)
    return np.asarray(audio, dtype=np.float32), int(detected_sample_rate)


def encode_audio_file(
    audio: AudioArray,
    sample_rate: int,
    output_path: Path,
    runtime_dir: Path,
) -> Path:
    intermediate_path = runtime_dir / "processed.wav"
    sf.write(intermediate_path, audio, sample_rate, subtype=PCM_SUBTYPE)

    if output_path.suffix.lower() == ".mp3":
        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(intermediate_path),
            "-codec:a",
            "libmp3lame",
            "-q:a",
            "2",
            str(output_path),
        ]
    else:
        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(intermediate_path),
            "-acodec",
            "pcm_s16le",
            str(output_path),
        ]

    _run_ffmpeg(command)
    return output_path
