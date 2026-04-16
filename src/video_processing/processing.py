from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from video_processing.audio_pipeline import run_audio_pipeline
from video_processing.config import AppConfig, get_project_root
from video_processing.ffmpeg_io import (
    build_output_path,
    create_runtime_directory,
    decode_audio_file,
    encode_audio_file,
    ensure_ffmpeg_available,
    remove_runtime_directory,
)


@dataclass(frozen=True)
class ProcessResult:
    output_path: Path
    used_curve_path: Path
    warnings: list[str]
    sample_rate: int


def resolve_curve_path(config: AppConfig) -> tuple[Path, list[str]]:
    if config.paths.filter_curve_csv.exists():
        return config.paths.filter_curve_csv, []

    warning = "No se encontro la curva configurada. Se usara la curva por defecto del proyecto."
    return config.paths.default_filter_curve_csv, [warning]


def process_audio_job(
    input_path: Path,
    output_dir: Path,
    output_format: str,
    config: AppConfig,
) -> ProcessResult:
    ensure_ffmpeg_available()
    output_dir.mkdir(parents=True, exist_ok=True)
    curve_path, warnings = resolve_curve_path(config)
    runtime_dir = create_runtime_directory(get_project_root())

    try:
        audio, sample_rate = decode_audio_file(
            input_path=input_path,
            sample_rate=config.sample_rate,
            runtime_dir=runtime_dir,
        )
        processed_audio = run_audio_pipeline(
            audio=audio,
            sample_rate=sample_rate,
            config=config,
            curve_csv_path=curve_path,
        )
        output_path = build_output_path(
            input_path=input_path,
            output_dir=output_dir,
            output_format=output_format,
        )
        encode_audio_file(
            audio=processed_audio,
            sample_rate=sample_rate,
            output_path=output_path,
            runtime_dir=runtime_dir,
        )
    finally:
        remove_runtime_directory(runtime_dir)

    return ProcessResult(
        output_path=output_path,
        used_curve_path=curve_path,
        warnings=warnings,
        sample_rate=sample_rate,
    )
