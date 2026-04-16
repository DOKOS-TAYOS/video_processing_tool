from __future__ import annotations

import json
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
from video_processing.processing import resolve_curve_path
from video_processing.sync_detection import Mode1SyncAnchors, SyncAnchor, detect_mode_1_anchors


@dataclass(frozen=True)
class Mode1Result:
    output_path: Path
    edit_plan_path: Path
    used_curve_path: Path
    warnings: list[str]
    sample_rate: int
    duration_seconds: float
    recommended_anchor: str | None
    anchors: Mode1SyncAnchors


def build_edit_plan_path(input_path: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    base_name = f"{input_path.stem}__edit_plan"
    candidate = output_dir / f"{base_name}.json"

    if candidate.resolve() != input_path.resolve() and not candidate.exists():
        return candidate

    index = 1
    while True:
        alternative = output_dir / f"{base_name}_{index:02d}.json"
        if alternative.resolve() != input_path.resolve() and not alternative.exists():
            return alternative
        index += 1


def _anchor_to_payload(anchor: SyncAnchor | None) -> dict[str, float] | None:
    if anchor is None:
        return None

    return {
        "source_seconds": anchor.source_seconds,
        "processed_seconds": anchor.processed_seconds,
        "confidence": anchor.confidence,
    }


def write_edit_plan(
    *,
    input_path: Path,
    output_path: Path,
    edit_plan_path: Path,
    sample_rate: int,
    duration_seconds: float,
    recommended_anchor: str | None,
    anchors: Mode1SyncAnchors,
    warnings: list[str],
) -> Path:
    payload = {
        "input_media_path": str(input_path),
        "processed_audio_path": str(output_path),
        "sample_rate": sample_rate,
        "duration_seconds": duration_seconds,
        "recommended_anchor": recommended_anchor,
        "anchors": {
            "speech_start": _anchor_to_payload(anchors.speech_start),
            "first_loud_sound": _anchor_to_payload(anchors.first_loud_sound),
        },
        "warnings": warnings,
    }
    edit_plan_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return edit_plan_path


def process_mode_1_job(
    input_path: Path,
    output_dir: Path,
    output_format: str,
    config: AppConfig,
) -> Mode1Result:
    ensure_ffmpeg_available()
    output_dir.mkdir(parents=True, exist_ok=True)
    curve_path, warnings = resolve_curve_path(config)
    runtime_dir = create_runtime_directory(get_project_root())

    try:
        source_audio, sample_rate = decode_audio_file(
            input_path=input_path,
            sample_rate=config.sample_rate,
            runtime_dir=runtime_dir,
        )
        processed_audio = run_audio_pipeline(
            audio=source_audio,
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
        anchors, recommended_anchor, sync_warnings = detect_mode_1_anchors(
            source_audio=source_audio,
            processed_audio=processed_audio,
            sample_rate=sample_rate,
            config=config.sync_detection,
        )
        combined_warnings = [*warnings, *sync_warnings]
        edit_plan_path = build_edit_plan_path(input_path=input_path, output_dir=output_dir)
        duration_seconds = float(source_audio.shape[0]) / float(sample_rate)
        write_edit_plan(
            input_path=input_path,
            output_path=output_path,
            edit_plan_path=edit_plan_path,
            sample_rate=sample_rate,
            duration_seconds=duration_seconds,
            recommended_anchor=recommended_anchor,
            anchors=anchors,
            warnings=combined_warnings,
        )
    finally:
        remove_runtime_directory(runtime_dir)

    return Mode1Result(
        output_path=output_path,
        edit_plan_path=edit_plan_path,
        used_curve_path=curve_path,
        warnings=combined_warnings,
        sample_rate=sample_rate,
        duration_seconds=duration_seconds,
        recommended_anchor=recommended_anchor,
        anchors=anchors,
    )
