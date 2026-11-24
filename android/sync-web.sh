#!/bin/sh
# Copia la agenda de la raíz del repositorio a los assets de la app de Android
# y le aplica los cambios propios de la versión Android.
# Uso (desde la carpeta android/):  sh sync-web.sh
set -eu
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$(cd "$(dirname "$0")" && pwd)/app/src/main/assets/web"
mkdir -p "$DEST"
cp "$RAIZ/icono.png" "$RAIZ/tribunales.json" "$DEST/"
python3 "$(dirname "$0")/parche-android.py" "$RAIZ/index.html" "$DEST/index.html"
echo "Assets actualizados en $DEST"
