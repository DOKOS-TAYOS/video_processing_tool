from __future__ import annotations

from pathlib import Path

import typer

from video_processing.config import load_app_config
from video_processing.dialogs import pick_input_file, pick_output_directory
from video_processing.processing import ProcessResult, process_audio_job

app = typer.Typer(help="Procesado de audio para flujos de edicion de video.")
INPUT_OPTION = typer.Option(None, "--input")
OUTPUT_DIR_OPTION = typer.Option(None, "--output-dir")
FORMAT_OPTION = typer.Option(None, "--format")
CONFIG_OPTION = typer.Option(None, "--config")


@app.callback()
def main() -> None:
    """Punto de entrada base para mantener el modo de subcomandos."""


def _resolve_input_path(input_path: Path | None) -> Path:
    if input_path is not None:
        return input_path

    typer.echo("Abriendo selector de archivo...")
    chosen_path = pick_input_file()
    if chosen_path is None:
        typer.echo("No se selecciono ningun archivo de entrada.")
        raise typer.Exit(code=1)
    return chosen_path


def _resolve_output_directory(output_dir: Path | None) -> Path:
    if output_dir is not None:
        return output_dir

    typer.echo("Abriendo selector de carpeta de salida...")
    chosen_path = pick_output_directory()
    if chosen_path is None:
        typer.echo("No se selecciono ninguna carpeta de salida.")
        raise typer.Exit(code=1)
    return chosen_path


def _print_result(result: ProcessResult | None) -> None:
    if result is None:
        return

    for warning in result.warnings:
        typer.echo(f"Aviso: {warning}")
    typer.echo(f"Audio procesado guardado en: {result.output_path}")


@app.command("process-audio")
def process_audio_command(
    input_path: Path | None = INPUT_OPTION,
    output_dir: Path | None = OUTPUT_DIR_OPTION,
    output_format: str | None = FORMAT_OPTION,
    config_path: Path | None = CONFIG_OPTION,
) -> None:
    config = load_app_config(config_path)
    resolved_input_path = _resolve_input_path(input_path)
    resolved_output_dir = _resolve_output_directory(output_dir)
    resolved_output_format = (output_format or config.default_output_format).lower()

    if resolved_output_format not in {"wav", "mp3"}:
        typer.echo("El formato de salida debe ser wav o mp3.")
        raise typer.Exit(code=1)

    if not resolved_input_path.exists():
        typer.echo(f"No existe el archivo de entrada: {resolved_input_path}")
        raise typer.Exit(code=1)

    result = process_audio_job(
        input_path=resolved_input_path,
        output_dir=resolved_output_dir,
        output_format=resolved_output_format,
        config=config,
    )
    _print_result(result)


def run_cli() -> int:
    app()
    return 0
