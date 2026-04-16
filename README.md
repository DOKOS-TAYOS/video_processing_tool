# video-processing

CLI en Python para procesar audio de forma parecida a tu flujo de Audacity y dejar el proyecto listo para fases futuras de sincronizacion y recorte.

## Requisitos

- Python 3.12
- FFmpeg accesible desde la terminal
- Entorno virtual `.venv`

## Uso rapido

```powershell
.venv\Scripts\activate
video-processing process-audio
```

Tambien puedes pasar rutas directamente:

```powershell
video-processing process-audio --input C:\ruta\audio.wav --output-dir C:\ruta\salida --format wav
```

Para `Modo 1`, parte de un video o de cualquier medio con audio y genera el audio procesado junto con un plan base de sincronizacion:

```powershell
video-processing mode-1 --input C:\ruta\clip.mp4 --output-dir C:\ruta\salida --format wav
```

La salida incluye:

- audio procesado (`__processed.wav` o `__processed.mp3`)
- plan de edicion JSON (`__edit_plan.json`) con:
  - `speech_start`
  - `first_loud_sound`
  - `recommended_anchor`
  - avisos de deteccion si falta alguna marca fiable

Para `Modo 2`, combina video y audio externo. El audio externo se procesa y exporta, y el audio de camara se usa para calcular el offset con el video:

```powershell
video-processing mode-2 --video C:\ruta\clip.mp4 --audio C:\ruta\voz.wav --output-dir C:\ruta\salida --format wav
```

La salida mantiene el mismo `edit_plan.json`, ampliado con:

- `inputs`: rutas del video y del audio externo
- `video_sync`: offset estimado entre audio externo y audio de camara
- `edits`: recortes de silencios y marcas de pausas largas aplicadas al audio final

## Configuracion

El preset editable vive en `config/settings.toml`.

Si `config/user_curve.csv` no existe, el programa usa `config/audacity_default_curve.csv`.

La seccion `[sync_detection]` controla la deteccion base para `mode-1`:

- `speech_window_ms`: tamano de ventana RMS para buscar el inicio de habla.
- `speech_min_duration_ms`: tiempo minimo sostenido por encima del umbral para aceptar voz.
- `speech_threshold_dbfs`: umbral de energia para detectar voz.
- `loud_sound_window_ms`: ventana de suavizado para buscar el primer sonido fuerte.
- `loud_sound_threshold_dbfs`: umbral de amplitud para detectar el primer pico relevante.

La seccion `[silence_editing]` controla el recorte temporal del audio final:

- `silence_threshold_dbfs`: nivel maximo para considerar un tramo como silencio.
- `min_trim_silence_seconds`: silencio minimo para recortarlo.
- `long_pause_seconds`: a partir de aqui se inserta marca sonora en vez de dejar el silencio completo.
- `edge_padding_seconds`: margen que se conserva al entrar y al salir del silencio.

La seccion `[pause_marker]` define el beep neutro para pausas largas:

- `beep_frequency_hz`
- `beep_duration_ms`
- `beep_level_dbfs`
- `fade_ms`

## JSON de salida

El `edit_plan.json` conserva los campos ya existentes y ahora puede incluir:

- `inputs`
- `video_sync`
- `edits`

`edits` contiene operaciones como:

- `trim_silence`
- `pause_marker`

Cada operacion registra tiempos de origen y tiempos de salida para poder reutilizar el plan en la fase de video.

## Build Windows

Para generar un `.exe` único en Windows:

```powershell
.\scripts\build_windows_exe.ps1
```

El ejecutable se deja en:

```powershell
dist\video-processing.exe
```

Comprobaciones rapidas recomendadas despues del build:

```powershell
.\dist\video-processing.exe --help
.\dist\video-processing.exe mode-1 --help
.\dist\video-processing.exe mode-2 --help
```
