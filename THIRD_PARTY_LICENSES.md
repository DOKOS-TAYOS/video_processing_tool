# Third-party licenses

This file lists **runtime** Python dependencies declared in `pyproject.toml`
(`[project].dependencies`), plus the external FFmpeg runtime used by this
project. It does **not** inventory development or packaging tooling from
`[project.optional-dependencies]` (for example `pytest`, `ruff`, `pyinstaller`).

License names use SPDX-style identifiers where a clear mapping exists.
Exact terms are those of each upstream project; consult the linked project
pages or the license text shipped with each package for the authoritative
text. Version constraints below come from `pyproject.toml` and are not
pinned lockfile versions.

## Python runtime dependencies

| Package     | Constraint (pyproject) | SPDX-style license | Project URL                                      |
|-------------|------------------------|--------------------|--------------------------------------------------|
| numpy       | >=2.1,<3.0             | BSD-3-Clause       | https://numpy.org/                               |
| scipy       | >=1.14,<2.0            | BSD-3-Clause       | https://scipy.org/                               |
| soundfile   | >=0.12,<1.0            | BSD-3-Clause       | https://python-soundfile.readthedocs.io/         |
| pyloudnorm  | >=0.1.1,<0.3           | MIT                | https://github.com/csteinmetz1/pyloudnorm        |
| noisereduce | >=3.0,<4.0             | MIT                | https://github.com/timsainb/noisereduce          |
| typer       | >=0.12,<1.0            | MIT                | https://typer.tiangolo.com/                      |

Notes:

- `numpy` and `scipy` distribute multiple components; the SPDX identifiers
  above reflect the primary upstream license. Installed wheels may report
  compound license expressions—use the texts inside each package's
  `.dist-info` as the source of truth when redistributing.
- Transitive runtime dependencies pulled in by the packages above are
  distributed under their own upstream licenses (`pip show <package>` or
  license files inside each wheel/sdist).

## External runtime (not bundled)

| Component | Role in this project | Typical upstream terms | Notes |
|-----------|----------------------|------------------------|-------|
| FFmpeg    | Invoked via `ffmpeg` on `PATH` for media I/O (`ffmpeg_io.py`) | Often LGPL-2.1+ or GPL-2.0+, depending on the build/configuration you install | **Not redistributed** by this repository. Install FFmpeg yourself and comply with the license of the binary/build you use. Project home: https://ffmpeg.org/ |

This project's MIT license covers only the source and materials in this
repository. Using FFmpeg does not change that; FFmpeg remains under its own
terms.

## Project assets note

`config/audacity_default_curve.csv` is project-authored EQ curve data inspired
by an Audacity-*style workflow*, not by Audacity software itself. See NOTICE.
