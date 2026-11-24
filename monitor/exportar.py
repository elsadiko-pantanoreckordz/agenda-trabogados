"""Arma el archivo cifrado de acuerdos que recibe la tablet.

Solo salen los acuerdos que la tablet todavía no tiene (los marcados como
«nuevo»), y se recortan los campos para no mandar más de lo necesario.
El cifrado es el mismo de siempre: AES-256-GCM con la clave de sincronización.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# El cifrado se comparte con el asistente: una sola implementación, ya probada
# contra la de la agenda en ambos sentidos.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agente"))
import almacen
from cripto import cifrar

# Topes: la tablet rechaza archivos desmedidos, así que aquí se respetan.
MAX_ACUERDOS = 2000
MAX_TEXTO = 20_000
MAX_SINTESIS = 1_000

_CAMPOS = ("fuente", "clave", "expediente", "expediente_crudo", "juzgado", "distrito",
           "materia", "jurisdiccion", "partes", "fecha_acuerdo", "fecha_publicacion",
           "sintesis", "texto", "url_documento", "huella")


def para_tablet(fila: sqlite3.Row) -> dict:
    a = {c: fila[c] for c in _CAMPOS}
    a["sintesis"] = (a["sintesis"] or "")[:MAX_SINTESIS]
    a["texto"] = (a["texto"] or "")[:MAX_TEXTO]
    # Solo se manda un enlace si es https: la tablet descarta cualquier otro.
    if not str(a["url_documento"] or "").startswith("https://"):
        a["url_documento"] = ""
    return a


def exportar(con: sqlite3.Connection, clave: str, destino: Path,
             solo_nuevos: bool = True, limite: int = MAX_ACUERDOS) -> tuple[int, Path]:
    filas = almacen.buscar(con, solo_nuevos=solo_nuevos, limite=min(limite, MAX_ACUERDOS))
    if not filas:
        return 0, destino
    paquete = {
        "formato": "agenda-rt-acuerdos", "version": 1,
        "generado": datetime.now().astimezone().isoformat(timespec="seconds"),
        "acuerdos": [para_tablet(f) for f in filas],
    }
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(cifrar(paquete, clave, "acuerdos"), ensure_ascii=False),
                       encoding="utf-8")
    almacen.marcar_vistos(con, [f["id"] for f in filas])
    return len(filas), destino
