#!/usr/bin/env python3
"""Monitor de Acuerdos · búsqueda por línea de comandos (etapa a).

Todavía no consulta ninguna fuente: eso llega cuando confirmemos los selectores
reales de cada boletín. Por ahora sirve para buscar en lo ya almacenado, llevar
la lista de vigilancia y ver el estado de la base.

Ejemplos:
    python3 -m monitor.cli estado
    python3 -m monitor.cli buscar --texto "vista" --desde 2026-11-01
    python3 -m monitor.cli buscar --expediente 452/2026
    python3 -m monitor.cli vigilar 452/2026 --nota "Audiencia próxima"
    python3 -m monitor.cli vigilados
    python3 -m monitor.cli demo          # mete acuerdos de ejemplo para probar
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

if __package__ in (None, ""):                      # permite ejecutarlo como archivo suelto
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import almacen

BASE_PREDETERMINADA = Path(__file__).resolve().parent / "datos" / "acuerdos.db"
EJEMPLOS = Path(__file__).resolve().parent / "ejemplos"


def ruta_base(args) -> Path:
    """La base a usar: --base, luego MONITOR_DB, luego la de siempre."""
    return Path(args.base or os.environ.get("MONITOR_DB") or BASE_PREDETERMINADA)


def _linea(fila) -> str:
    marca = "NUEVO " if fila["nuevo"] else "      "
    exp = fila["expediente"] or fila["expediente_crudo"] or "sin número"
    return (f"{marca}{fila['fecha_acuerdo'] or '??':10}  {exp:14}  "
            f"{(fila['juzgado'] or '')[:40]:40}  {(fila['sintesis'] or '')[:60]}")


def cmd_buscar(args) -> int:
    con = almacen.abrir(ruta_base(args))
    filas = almacen.buscar(
        con, texto=args.texto, expediente=args.expediente, juzgado=args.juzgado,
        materia=args.materia, jurisdiccion=args.jurisdiccion, parte=args.parte,
        desde=args.desde, hasta=args.hasta, solo_nuevos=args.nuevos,
        solo_vigilados=args.vigilados, limite=args.limite,
    )
    if args.json:
        print(json.dumps([dict(f) for f in filas], ensure_ascii=False, indent=2))
        return 0
    if not filas:
        print("Sin resultados.")
        return 0
    print(f"{len(filas)} resultado(s):\n")
    for f in filas:
        print(_linea(f))
    return 0


def cmd_vigilar(args) -> int:
    con = almacen.abrir(ruta_base(args))
    try:
        canon = almacen.vigilar(con, args.expediente, nota=args.nota, activo=not args.quitar)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    print(f"{'Ya no se vigila' if args.quitar else 'Se vigilará'}: {canon}")
    return 0


def cmd_vigilados(args) -> int:
    con = almacen.abrir(ruta_base(args))
    filas = almacen.vigilados(con, activos=not args.todos)
    if not filas:
        print("No hay expedientes en vigilancia.")
        return 0
    for f in filas:
        estado = "activo" if f["activo"] else "pausado"
        print(f"{f['expediente']:14}  {estado:8}  {f['nota']}")
    return 0


def cmd_estado(args) -> int:
    con = almacen.abrir(ruta_base(args))
    e = almacen.estado(con)
    print(f"Base:            {ruta_base(args)}")
    print(f"Acuerdos:        {e['acuerdos']} ({e['nuevos']} sin revisar)")
    print(f"Con expediente:  {e['con_expediente']}")
    print(f"En vigilancia:   {e['vigilados']}")
    if e["fuentes"]:
        print("Fuentes:")
        for f in e["fuentes"]:
            print(f"  {f['nombre']:12} {f['acuerdos']:5} acuerdos  última revisión: {f['ultima_revision'] or 'nunca'}")
    else:
        print("Fuentes:         ninguna todavía (los conectores llegan en la etapa d)")
    return 0


def cmd_demo(args) -> int:
    """Carga acuerdos de ejemplo para poder probar la búsqueda sin conectores."""
    ruta = EJEMPLOS / "acuerdos_demo.json"
    if not ruta.is_file():
        print(f"No encuentro los ejemplos en {ruta}", file=sys.stderr)
        return 1
    con = almacen.abrir(ruta_base(args))
    nuevos = sum(1 for a in json.loads(ruta.read_text(encoding="utf-8")) if almacen.guardar(con, a))
    print(f"{nuevos} acuerdo(s) de ejemplo cargados en {ruta_base(args)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="monitor.cli", description="Monitor de Acuerdos de la Agenda RT")
    ap.add_argument("--base", help="archivo de base de datos (por defecto monitor/datos/acuerdos.db)")
    ap.add_argument("-v", "--verboso", action="store_true", help="muestra el registro de actividad")
    sub = ap.add_subparsers(dest="orden", required=True)

    b = sub.add_parser("buscar", help="busca entre los acuerdos almacenados")
    b.add_argument("--texto", help="palabras a buscar en síntesis, texto, partes y juzgado")
    b.add_argument("--expediente", help="número de expediente, en cualquier formato")
    b.add_argument("--juzgado")
    b.add_argument("--materia")
    b.add_argument("--jurisdiccion")
    b.add_argument("--parte", help="nombre de una de las partes")
    b.add_argument("--desde", help="fecha mínima, AAAA-MM-DD")
    b.add_argument("--hasta", help="fecha máxima, AAAA-MM-DD")
    b.add_argument("--nuevos", action="store_true", help="solo los que no has revisado")
    b.add_argument("--vigilados", action="store_true", help="solo expedientes en vigilancia")
    b.add_argument("--limite", type=int, default=almacen.LIMITE_PREDETERMINADO)
    b.add_argument("--json", action="store_true", help="salida en JSON")
    b.set_defaults(func=cmd_buscar)

    g = sub.add_parser("vigilar", help="marca un expediente para revisión diaria")
    g.add_argument("expediente")
    g.add_argument("--nota", default="")
    g.add_argument("--quitar", action="store_true", help="deja de vigilarlo")
    g.set_defaults(func=cmd_vigilar)

    v = sub.add_parser("vigilados", help="lista los expedientes vigilados")
    v.add_argument("--todos", action="store_true", help="incluye los pausados")
    v.set_defaults(func=cmd_vigilados)

    e = sub.add_parser("estado", help="resumen de la base del monitor")
    e.set_defaults(func=cmd_estado)

    d = sub.add_parser("demo", help="carga acuerdos de ejemplo")
    d.set_defaults(func=cmd_demo)

    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verboso else logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
