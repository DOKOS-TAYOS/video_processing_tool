from __future__ import annotations

from pathlib import Path

import typer

from video_processing.config import load_app_config
from video_processing.dialogs import pick_input_file, pick_output_directory
from video_processing.ffmpeg_io import FFmpegCommandError, FFmpegNotAvailableError
from video_processing.mode_1 import Mode1Result, process_mode_1_job
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


def _print_mode_1_result(result: Mode1Result | None) -> None:
    if result is None:
        return

    for warning in result.warnings:
        typer.echo(f"Aviso: {warning}")
    typer.echo(f"Audio procesado guardado en: {result.output_path}")
    typer.echo(f"Plan de edicion guardado en: {result.edit_plan_path}")
    if result.recommended_anchor is not None:
        typer.echo(f"Ancla recomendada: {result.recommended_anchor}")


def _resolve_output_format(output_format: str | None, default_output_format: str) -> str:
    resolved_output_format = (output_format or default_output_format).lower()
    if resolved_output_format not in {"wav", "mp3"}:
        typer.echo("El formato de salida debe ser wav o mp3.")
        raise typer.Exit(code=1)
    return resolved_output_format


def _handle_processing_error(error: Exception) -> None:
    typer.echo(str(error))
    raise typer.Exit(code=1) from error


@app.command("process-audio")
def process_audio_command(
    input_path: Path | None = INPUT_OPTION,
    output_dir: Path | None = OUTPUT_DIR_OPTION,
    output_format: str | None = FORMAT_OPTION,
    config_path: Path | None = CONFIG_OPTION,
) -> None:
    """Procesa un audio o medio compatible y exporta solo el audio final."""
    config = load_app_config(config_path)
    resolved_input_path = _resolve_input_path(input_path)
    resolved_output_dir = _resolve_output_directory(output_dir)
    resolved_output_format = _resolve_output_format(output_format, config.default_output_format)

    if not resolved_input_path.exists():
        typer.echo(f"No existe el archivo de entrada: {resolved_input_path}")
        raise typer.Exit(code=1)

    try:
        result = process_audio_job(
            input_path=resolved_input_path,
            output_dir=resolved_output_dir,
            output_format=resolved_output_format,
            config=config,
        )
    except (FFmpegCommandError, FFmpegNotAvailableError) as error:
        _handle_processing_error(error)
    _print_result(result)


@app.command("mode-1")
def mode_1_command(
    input_path: Path | None = INPUT_OPTION,
    output_dir: Path | None = OUTPUT_DIR_OPTION,
    output_format: str | None = FORMAT_OPTION,
    config_path: Path | None = CONFIG_OPTION,
) -> None:
    """Genera audio procesado y un plan JSON con sincronizacion base para video."""
    config = load_app_config(config_path)
    resolved_input_path = _resolve_input_path(input_path)
    resolved_output_dir = _resolve_output_directory(output_dir)
    resolved_output_format = _resolve_output_format(output_format, config.default_output_format)

    if not resolved_input_path.exists():
        typer.echo(f"No existe el archivo de entrada: {resolved_input_path}")
        raise typer.Exit(code=1)

    try:
        result = process_mode_1_job(
            input_path=resolved_input_path,
            output_dir=resolved_output_dir,
            output_format=resolved_output_format,
            config=config,
        )
    except (FFmpegCommandError, FFmpegNotAvailableError) as error:
        _handle_processing_error(error)
    _print_mode_1_result(result)


def run_cli() -> int:
    app()
    return 0
