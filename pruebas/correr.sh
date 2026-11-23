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

echo
if [ "$fallas" -eq 0 ]; then echo "Todo en orden."; else echo "$fallas prueba(s) fallaron."; fi
exit "$fallas"
