from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from video_processing.silence_editing import EditOperation
from video_processing.sync_detection import (
    DetectedAnchor,
    Mode1SyncAnchors,
    SyncAnchor,
    VideoSyncResult,
)


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


def _detected_anchor_to_payload(anchor: DetectedAnchor | None) -> dict[str, float] | None:
    if anchor is None:
        return None

    return {"seconds": anchor.seconds, "confidence": anchor.confidence}


def _video_sync_to_payload(video_sync: VideoSyncResult | None) -> dict[str, Any]:
    if video_sync is None:
        return {
            "external_audio_offset_seconds": None,
            "offset_anchor": None,
            "camera_anchors": None,
        }

    return {
        "external_audio_offset_seconds": video_sync.external_audio_offset_seconds,
        "offset_anchor": video_sync.offset_anchor,
        "camera_anchors": {
            "speech_start": _detected_anchor_to_payload(video_sync.camera_anchors.speech_start),
            "first_loud_sound": _detected_anchor_to_payload(
                video_sync.camera_anchors.first_loud_sound
            ),
        },
    }


def write_edit_plan(
    *,
    input_media_path: Path,
    output_path: Path,
    edit_plan_path: Path,
    sample_rate: int,
    duration_seconds: float,
    recommended_anchor: str | None,
    anchors: Mode1SyncAnchors,
    warnings: list[str],
    input_video_path: Path | None,
    input_external_audio_path: Path | None,
    video_sync: VideoSyncResult | None,
    edits: list[EditOperation],
) -> Path:
    payload = {
        "input_media_path": str(input_media_path),
        "processed_audio_path": str(output_path),
        "sample_rate": sample_rate,
        "duration_seconds": duration_seconds,
        "recommended_anchor": recommended_anchor,
        "anchors": {
            "speech_start": _anchor_to_payload(anchors.speech_start),
            "first_loud_sound": _anchor_to_payload(anchors.first_loud_sound),
        },
        "warnings": warnings,
        "inputs": {
            "input_video_path": str(input_video_path) if input_video_path is not None else None,
            "input_external_audio_path": (
                str(input_external_audio_path) if input_external_audio_path is not None else None
            ),
        },
        "video_sync": _video_sync_to_payload(video_sync),
        "edits": edits,
    }
    edit_plan_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return edit_plan_path


__all__ = ["build_edit_plan_path", "write_edit_plan"]
