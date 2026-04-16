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

## Configuracion

El preset editable vive en `config/settings.toml`.

Si `config/user_curve.csv` no existe, el programa usa `config/audacity_default_curve.csv`.
