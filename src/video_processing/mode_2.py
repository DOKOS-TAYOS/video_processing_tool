from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from video_processing.audio_pipeline import run_audio_pipeline
from video_processing.config import AppConfig, get_project_root
from video_processing.edit_plan import build_edit_plan_path, write_edit_plan
from video_processing.ffmpeg_io import (
    build_output_path,
    create_runtime_directory,
    decode_audio_file,
    encode_audio_file,
    ensure_ffmpeg_available,
    remove_runtime_directory,
)
from video_processing.processing import resolve_curve_path
from video_processing.silence_editing import EditOperation, apply_silence_edits
from video_processing.sync_detection import (
    Mode1SyncAnchors,
    VideoSyncResult,
    calculate_video_sync,
    detect_mode_1_anchors,
)


@dataclass(frozen=True)
class Mode2Result:
    output_path: Path
    edit_plan_path: Path
    used_curve_path: Path
    warnings: list[str]
    sample_rate: int
    duration_seconds: float
    recommended_anchor: str | None
    anchors: Mode1SyncAnchors
    edits: list[EditOperation]
    video_sync: VideoSyncResult


def process_mode_2_job(
    video_path: Path,
    audio_path: Path,
    output_dir: Path,
    output_format: str,
    config: AppConfig,
) -> Mode2Result:
    ensure_ffmpeg_available()
    output_dir.mkdir(parents=True, exist_ok=True)
    curve_path, warnings = resolve_curve_path(config)
    runtime_dir = create_runtime_directory(get_project_root())

    try:
        camera_audio, sample_rate = decode_audio_file(
            input_path=video_path,
            sample_rate=config.sample_rate,
            runtime_dir=runtime_dir,
            missing_audio_message=(
                "El archivo no contiene una pista de audio utilizable para el modo 2."
            ),
        )
        external_audio, sample_rate = decode_audio_file(
            input_path=audio_path,
            sample_rate=config.sample_rate,
            runtime_dir=runtime_dir,
            missing_audio_message=(
                "El archivo no contiene una pista de audio utilizable para el modo 2."
            ),
        )
        processed_audio = run_audio_pipeline(
            audio=external_audio,
            sample_rate=sample_rate,
            config=config,
            curve_csv_path=curve_path,
        )
        edited_audio, edits = apply_silence_edits(
            audio=processed_audio,
            sample_rate=sample_rate,
            silence_config=config.silence_editing,
            pause_marker_config=config.pause_marker,
        )
        output_path = build_output_path(
            input_path=audio_path,
            output_dir=output_dir,
            output_format=output_format,
        )
        encode_audio_file(
            audio=edited_audio,
            sample_rate=sample_rate,
            output_path=output_path,
            runtime_dir=runtime_dir,
        )
        anchors, recommended_anchor, sync_warnings = detect_mode_1_anchors(
            source_audio=external_audio,
            processed_audio=edited_audio,
            sample_rate=sample_rate,
            config=config.sync_detection,
        )
        video_sync = calculate_video_sync(
            external_audio=external_audio,
            camera_audio=camera_audio,
            sample_rate=sample_rate,
            config=config.sync_detection,
        )
        combined_warnings = [*warnings, *sync_warnings, *video_sync.warnings]
        edit_plan_path = build_edit_plan_path(input_path=audio_path, output_dir=output_dir)
        duration_seconds = float(edited_audio.shape[0]) / float(sample_rate)
        write_edit_plan(
            input_media_path=audio_path,
            output_path=output_path,
            edit_plan_path=edit_plan_path,
            sample_rate=sample_rate,
            duration_seconds=duration_seconds,
            recommended_anchor=recommended_anchor,
            anchors=anchors,
            warnings=combined_warnings,
            input_video_path=video_path,
            input_external_audio_path=audio_path,
            video_sync=video_sync,
            edits=edits,
        )
    finally:
        remove_runtime_directory(runtime_dir)

    return Mode2Result(
        output_path=output_path,
        edit_plan_path=edit_plan_path,
        used_curve_path=curve_path,
        warnings=combined_warnings,
        sample_rate=sample_rate,
        duration_seconds=duration_seconds,
        recommended_anchor=recommended_anchor,
        anchors=anchors,
        edits=edits,
        video_sync=video_sync,
    )
