#!/bin/sh
# Corre todas las pruebas del proyecto. No gasta en la API: la respuesta del
# modelo se simula. Requiere node y python3 (con cryptography).
#
# Uso:  sh pruebas/correr.sh
set -eu
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
fallas=0

paso() {
  echo
  echo "── $1 ──"
  shift
  if "$@"; then echo "   PASÓ"; else echo "   FALLÓ"; fallas=$((fallas + 1)); fi
}

paso "Avisos de riesgo (reglas en el dispositivo)" node "$RAIZ/pruebas/riesgos.test.js"
paso "Conteo de plazos (aritmética en la computadora)" python3 "$RAIZ/agente/plazos.py"
paso "Cifrado: la tablet cifra, la computadora abre" sh -c "cd '$RAIZ' && node pruebas/cruzado.js"
paso "Circuito del asistente (modelo simulado)" python3 "$RAIZ/pruebas/circuito.py" "$TMP"
paso "La agenda acepta y valida las propuestas" node "$RAIZ/pruebas/acepta.js" "$TMP"
paso "Monitor de Acuerdos (normalización, almacén, seguridad)" python3 "$RAIZ/pruebas/monitor_acuerdos.py"
paso "Pestaña Acuerdos: paridad con la computadora y búsqueda" node "$RAIZ/pruebas/acuerdos.test.js"
paso "Circuito de acuerdos (computadora cifra, la agenda abre)" sh -c '
  set -eu
  export AGENDA_CLAVE_SYNC="clave-de-sincronizacion-del-despacho"
  export MONITOR_DB="$2/monitor.db"
  python3 "$1/monitor/cli.py" demo >/dev/null
  python3 "$1/monitor/cli.py" exportar -s "$2/acuerdos.json" >/dev/null
  node "$1/pruebas/acuerdos_circuito.js" "$2/acuerdos.json"
' sh "$RAIZ" "$TMP"
paso "Acuerdo → propuesta de evento aceptada por la agenda" sh -c '
  set -eu
  export AGENDA_CLAVE_SYNC="clave-de-sincronizacion-del-despacho"
  export MONITOR_DB="$2/monitor2.db"
  python3 "$1/monitor/cli.py" demo >/dev/null
  python3 "$1/monitor/cli.py" proponer -s "$2/propuestas.json" >/dev/null
  node "$1/pruebas/acuerdos_propuestas.js" "$2/propuestas.json"
' sh "$RAIZ" "$TMP"
if command -v ruff >/dev/null 2>&1; then
  paso "Revisión de código con ruff" ruff check "$RAIZ/monitor" "$RAIZ/pruebas/monitor_acuerdos.py"
else
  echo; echo "── Revisión de código con ruff ──"; echo "   OMITIDA: ruff no está instalado (pip install ruff)"
fi

echo
if [ "$fallas" -eq 0 ]; then echo "Todo en orden."; else echo "$fallas prueba(s) fallaron."; fi
exit "$fallas"
