import sys
from pathlib import Path

from video_processing.config import get_project_root
from video_processing.ffmpeg_io import create_runtime_directory


def test_get_project_root_uses_pyinstaller_bundle_directory(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    assert get_project_root() == tmp_path


def test_create_runtime_directory_uses_temp_directory_when_frozen(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr("video_processing.ffmpeg_io.tempfile.gettempdir", lambda: str(tmp_path))

    runtime_dir = create_runtime_directory(Path("ignored"))

    assert runtime_dir.parent == tmp_path / "video-processing" / "runtime"
