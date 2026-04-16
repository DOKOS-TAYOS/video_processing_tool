from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class FilterCurvePaths:
    filter_curve_csv: Path
    default_filter_curve_csv: Path


@dataclass(frozen=True)
class NoiseProfileConfig:
    start_seconds: float
    duration_seconds: float


@dataclass(frozen=True)
class NoiseReductionConfig:
    reduction_db: float
    sensitivity: float
    smoothing: float


@dataclass(frozen=True)
class LoudnessConfig:
    target_lufs: float


@dataclass(frozen=True)
class PeakNormalizationConfig:
    target_peak_db: float


@dataclass(frozen=True)
class CompressionConfig:
    threshold_db: float
    ratio: float
    attack_ms: float
    release_ms: float
    makeup_gain_db: float


@dataclass(frozen=True)
class SyncDetectionConfig:
    speech_window_ms: int
    speech_min_duration_ms: int
    speech_threshold_dbfs: float
    loud_sound_window_ms: int
    loud_sound_threshold_dbfs: float


def get_default_sync_detection_config() -> SyncDetectionConfig:
    return SyncDetectionConfig(
        speech_window_ms=40,
        speech_min_duration_ms=250,
        speech_threshold_dbfs=-32.0,
        loud_sound_window_ms=15,
        loud_sound_threshold_dbfs=-12.0,
    )


@dataclass(frozen=True)
class AppConfig:
    default_output_format: str
    sample_rate: int
    paths: FilterCurvePaths
    noise_profile: NoiseProfileConfig
    noise_reduction: NoiseReductionConfig
    loudness: LoudnessConfig
    peak_normalization: PeakNormalizationConfig
    compression: CompressionConfig
    sync_detection: SyncDetectionConfig = field(default_factory=get_default_sync_detection_config)


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def get_default_config_path() -> Path:
    return get_project_root() / "config" / "settings.toml"


def get_default_curve_path() -> Path:
    return get_project_root() / "config" / "audacity_default_curve.csv"


def _resolve_path(raw_path: str, *, base_dir: Path) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    return (base_dir / candidate).resolve()


def load_app_config(config_path: Path | None = None) -> AppConfig:
    resolved_config_path = config_path or get_default_config_path()
    with resolved_config_path.open("rb") as config_file:
        raw_config = tomllib.load(config_file)

    base_dir = resolved_config_path.parent
    app_section = raw_config["app"]
    paths_section = raw_config["paths"]
    noise_profile_section = raw_config["noise_profile"]
    noise_reduction_section = raw_config["noise_reduction"]
    loudness_section = raw_config["loudness"]
    peak_section = raw_config["peak_normalization"]
    compression_section = raw_config["compression"]
    sync_detection_section = raw_config.get("sync_detection", {})
    default_sync_detection = get_default_sync_detection_config()

    default_curve_raw = paths_section.get("default_filter_curve_csv")
    default_curve_path = (
        _resolve_path(default_curve_raw, base_dir=base_dir)
        if default_curve_raw
        else get_default_curve_path()
    )

    return AppConfig(
        default_output_format=app_section["default_output_format"],
        sample_rate=int(app_section["sample_rate"]),
        paths=FilterCurvePaths(
            filter_curve_csv=_resolve_path(paths_section["filter_curve_csv"], base_dir=base_dir),
            default_filter_curve_csv=default_curve_path,
        ),
        noise_profile=NoiseProfileConfig(
            start_seconds=float(noise_profile_section["start_seconds"]),
            duration_seconds=float(noise_profile_section["duration_seconds"]),
        ),
        noise_reduction=NoiseReductionConfig(
            reduction_db=float(noise_reduction_section["reduction_db"]),
            sensitivity=float(noise_reduction_section["sensitivity"]),
            smoothing=float(noise_reduction_section["smoothing"]),
        ),
        loudness=LoudnessConfig(target_lufs=float(loudness_section["target_lufs"])),
        peak_normalization=PeakNormalizationConfig(
            target_peak_db=float(peak_section["target_peak_db"])
        ),
        compression=CompressionConfig(
            threshold_db=float(compression_section["threshold_db"]),
            ratio=float(compression_section["ratio"]),
            attack_ms=float(compression_section["attack_ms"]),
            release_ms=float(compression_section["release_ms"]),
            makeup_gain_db=float(compression_section["makeup_gain_db"]),
        ),
        sync_detection=SyncDetectionConfig(
            speech_window_ms=int(
                sync_detection_section.get(
                    "speech_window_ms",
                    default_sync_detection.speech_window_ms,
                )
            ),
            speech_min_duration_ms=int(
                sync_detection_section.get(
                    "speech_min_duration_ms",
                    default_sync_detection.speech_min_duration_ms,
                )
            ),
            speech_threshold_dbfs=float(
                sync_detection_section.get(
                    "speech_threshold_dbfs",
                    default_sync_detection.speech_threshold_dbfs,
                )
            ),
            loud_sound_window_ms=int(
                sync_detection_section.get(
                    "loud_sound_window_ms",
                    default_sync_detection.loud_sound_window_ms,
                )
            ),
            loud_sound_threshold_dbfs=float(
                sync_detection_section.get(
                    "loud_sound_threshold_dbfs",
                    default_sync_detection.loud_sound_threshold_dbfs,
                )
            ),
        ),
    )
