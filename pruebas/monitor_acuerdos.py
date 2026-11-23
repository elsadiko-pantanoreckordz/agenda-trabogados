#!/usr/bin/env python3
"""Pruebas del Monitor de Acuerdos (etapa a).

No tocan la red ni la base del despacho: cada prueba trabaja sobre una base
temporal propia. Incluye pruebas de seguridad con entradas hostiles.
"""
from __future__ import annotations

import json
import sys
import tempfile
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "monitor"))

import almacen  # noqa: E402
import cli  # noqa: E402
import expedientes  # noqa: E402

FALLAS = 0


def probar(nombre: str, obtenido, esperado) -> None:
    global FALLAS
    ok = obtenido == esperado
    print(f"{'OK   ' if ok else 'FALLA'} {nombre}: {obtenido!r}"
          + ("" if ok else f" (se esperaba {esperado!r})"))
    if not ok:
        FALLAS += 1


def base_con_ejemplos(carpeta: Path):
    con = almacen.abrir(carpeta / "prueba.db")
    datos = json.loads((RAIZ / "monitor" / "ejemplos" / "acuerdos_demo.json").read_text(encoding="utf-8"))
    for a in datos:
        almacen.guardar(con, a)
    return con


def pruebas_normalizacion() -> None:
    """Usa la misma tabla de casos que la prueba de la agenda, para que la
    computadora y la tablet normalicen exactamente igual."""
    print("\n── Normalización de expedientes (tabla compartida) ──")
    tabla = json.loads((RAIZ / "pruebas" / "casos_expedientes.json").read_text(encoding="utf-8"))
    hoy = date.fromisoformat(tabla["_hoy"])
    malos = 0
    for entrada, canon, completo in tabla["casos"]:
        e = expedientes.normalizar(entrada, hoy=hoy)
        obtenido = (e.canonico if e else "", e.completo if e else "")
        if obtenido != (canon, completo):
            print(f"FALLA {entrada!r}: {obtenido!r} (se esperaba {(canon, completo)!r})")
            malos += 1
    probar(f"los {len(tabla['casos'])} casos de la tabla compartida", malos, 0)
    ext = tabla["_extraccion"]
    probar("extrae todos sin repetir",
           [str(x) for x in expedientes.extraer(ext["texto"], hoy=hoy)], ext["esperado"])


def pruebas_almacen(carpeta: Path) -> None:
    print("\n── Almacén y búsqueda ──")
    con = base_con_ejemplos(carpeta)

    probar("guardó los tres ejemplos", almacen.estado(con)["acuerdos"], 3)
    probar("empató el expediente normalizado",
           len(almacen.buscar(con, expediente="00452/2026")), 2)
    probar("busca por texto", len(almacen.buscar(con, texto="vista")), 1)
    probar("busca por parte", len(almacen.buscar(con, parte="CONSTRUCTORA")), 2)
    probar("busca sin acentos (señala/senala)", len(almacen.buscar(con, texto="señala")), 1)
    probar("filtra por materia", len(almacen.buscar(con, materia="Amparo")), 1)
    probar("filtra por fechas", len(almacen.buscar(con, desde="2026-11-19")), 2)
    probar("combina filtros",
           len(almacen.buscar(con, materia="Civil", desde="2026-11-19", texto="vista")), 1)
    probar("respeta el límite", len(almacen.buscar(con, limite=1)), 1)
    probar("el límite tiene tope", len(almacen.buscar(con, limite=10**9)), 3)

    # Vigilancia
    almacen.vigilar(con, "452/2026", nota="principal")
    probar("vigilados", [v["expediente"] for v in almacen.vigilados(con)], ["452/2026"])
    probar("filtra por vigilados", len(almacen.buscar(con, solo_vigilados=True)), 2)
    almacen.vigilar(con, "452/2026", activo=False)
    probar("se puede pausar la vigilancia", len(almacen.vigilados(con)), 0)
    try:
        almacen.vigilar(con, "no es un expediente")
        probar("rechaza vigilar basura", "aceptado", "rechazado")
    except ValueError:
        probar("rechaza vigilar basura", "rechazado", "rechazado")


def pruebas_huella(carpeta: Path) -> None:
    print("\n── Detección de acuerdos nuevos por huella ──")
    con = almacen.abrir(carpeta / "huella.db")
    base = {"fuente": "sonora", "clave": "x-1", "expediente_crudo": "9/2026",
            "sintesis": "se da vista", "fecha_acuerdo": "2026-11-20"}
    probar("la primera vez es nuevo", almacen.guardar(con, base), True)
    probar("el mismo acuerdo no se repite", almacen.guardar(con, dict(base)), False)
    probar("no duplicó el renglón", almacen.estado(con)["acuerdos"], 1)

    cambiado = dict(base, sintesis="se da vista por tres dias")
    probar("si cambia el contenido, vuelve a ser nuevo", almacen.guardar(con, cambiado), True)
    probar("sigue siendo un solo acuerdo", almacen.estado(con)["acuerdos"], 1)

    ids = [f["id"] for f in almacen.buscar(con)]
    probar("marcar como visto", almacen.marcar_vistos(con, ids), 1)
    probar("ya no aparece como nuevo", len(almacen.buscar(con, solo_nuevos=True)), 0)

    try:
        almacen.guardar(con, {"sintesis": "sin fuente ni clave"})
        probar("exige fuente y clave", "aceptado", "rechazado")
    except ValueError:
        probar("exige fuente y clave", "rechazado", "rechazado")


def pruebas_seguridad(carpeta: Path) -> None:
    print("\n── Seguridad: entradas hostiles ──")
    con = base_con_ejemplos(carpeta)

    # SQL: el texto del usuario nunca se concatena en la consulta.
    hostiles = ["'; DROP TABLE acuerdos; --", "' OR '1'='1", '" OR 1=1 --', "%", "_", "\\"]
    for h in hostiles:
        try:
            almacen.buscar(con, texto=h, parte=h, juzgado=h, expediente=h)
        except Exception as e:
            probar(f"sobrevive a {h!r}", f"excepción {type(e).__name__}", "sin excepción")
    probar("las tablas siguen ahí después de las inyecciones",
           almacen.estado(con)["acuerdos"], 3)

    # FTS5 tiene sintaxis propia: operadores y comillas deben quedar como texto.
    probar("un operador OR queda como texto, no como operador",
           almacen.consulta_fts('vista" OR 1=1 --'), '"vista" AND "OR"')
    probar("comilla suelta no rompe la consulta",
           len(almacen.buscar(con, texto='vista"')), 1)
    probar("el comodín no trae todo",
           len(almacen.buscar(con, texto="*")), 0)
    probar("NEAR no se interpreta como operador",
           len(almacen.buscar(con, texto="NEAR(vista audiencia)")), 0)
    probar("limita el número de palabras",
           almacen.consulta_fts(" ".join(f"palabra{i}" for i in range(30))).count(" AND "), 11)

    # La base del monitor es independiente: no conoce las tablas de la agenda.
    tablas = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for ajena in ("eventos", "expedientes", "tribunales", "usuarios", "sesiones_tablet"):
        probar(f"no toca la tabla «{ajena}» de la agenda", ajena in tablas, False)


def pruebas_analisis() -> None:
    """De acuerdo a propuesta de evento. Sin modelo: solo reglas verificables."""
    print("\n── Acuerdo → propuesta de evento ──")
    import analisis

    inhabiles = {date(2026, 11, 24)}
    base = {"fuente": "sonora", "clave": "k", "expediente": "452/2026",
            "fecha_acuerdo": "2026-11-20", "juzgado": "Juzgado X", "sintesis": "", "texto": ""}

    # Plazo en letras, días hábiles. 20-nov-2026 es viernes; con el 24 inhábil,
    # tres hábiles caen el jueves 26.
    p = analisis.propuesta_de_acuerdo(
        dict(base, sintesis="Se da vista por el termino de tres dias habiles"), inhabiles)
    probar("plazo en letras y hábiles", (p["evento"]["tipo"], p["evento"]["fecha"]),
           ("Vencimiento", "2026-11-26"))
    probar("trae el conteo día por día", len(p["conteo"]) >= 5, True)
    probar("avisa de la fecha desde la que contó",
           any("surtió efectos" in c for c in p["conteo"]), True)

    # Plazo en dígitos y naturales.
    p = analisis.propuesta_de_acuerdo(
        dict(base, sintesis="Se concede plazo de 5 dias naturales para alegatos"), inhabiles)
    probar("plazo en dígitos y naturales", p["evento"]["fecha"], "2026-11-25")

    # Sin decir si son hábiles o naturales: NO se adivina.
    p = analisis.propuesta_de_acuerdo(
        dict(base, sintesis="Se concede el termino de tres dias para contestar"), inhabiles)
    probar("plazo ambiguo no inventa vencimiento", p["evento"]["tipo"], "Tarea")
    probar("y explica por qué", "no dice" in p["explicacion"], True)

    # Audiencia con fecha y hora en letras.
    p = analisis.propuesta_de_acuerdo(
        dict(base, sintesis="Se senalan las nueve treinta horas del dia diez de diciembre de dos mil veintiseis "
                            "para la audiencia de pruebas"), inhabiles)
    probar("audiencia en letras", (p["evento"]["tipo"], p["evento"]["fecha"], p["evento"]["hora"]),
           ("Audiencia", "2026-12-10", "09:30"))
    probar("la audiencia no se presenta como plazo contado",
           any("no es un plazo contado" in c.lower() for c in p["conteo"]), True)

    # Audiencia con fecha y hora en dígitos.
    p = analisis.propuesta_de_acuerdo(
        dict(base, sintesis="Se fija audiencia para el 15/12/2026 a las 11:00 horas"), inhabiles)
    probar("audiencia en dígitos", (p["evento"]["fecha"], p["evento"]["hora"]), ("2026-12-15", "11:00"))

    # Fundamento: solo si aparece literalmente.
    p = analisis.propuesta_de_acuerdo(
        dict(base, sintesis="Se da vista por termino de tres dias habiles, con fundamento en el articulo 273 del codigo"), inhabiles)
    probar("cita el artículo que sí aparece", p["fundamento"].startswith("articulo 273"), True)
    p = analisis.propuesta_de_acuerdo(
        dict(base, sintesis="Se da vista por termino de tres dias habiles"), inhabiles)
    probar("no inventa fundamento cuando no hay", p["fundamento"], "")

    # Lo que NO debe proponer.
    for sintesis, motivo in [
        ("Se tiene por presentado el escrito y se agrega a los autos", "trámite sin plazo"),
        ("", "acuerdo vacío"),
    ]:
        probar(f"no propone nada ante {motivo}",
               analisis.propuesta_de_acuerdo(dict(base, sintesis=sintesis), inhabiles), None)
    probar("sin fecha de acuerdo no propone",
           analisis.propuesta_de_acuerdo(dict(base, fecha_acuerdo="", sintesis="termino de tres dias habiles")), None)
    probar("plazo absurdo no propone vencimiento",
           analisis.propuesta_de_acuerdo(dict(base, sintesis="termino de 900 dias habiles"), inhabiles), None)

    # Un acuerdo que pide algo pero no dice cuándo: solo si tú lo pides.
    accionable = dict(base, sintesis="Se requiere a la parte para que exhiba el documento")
    probar("por omisión se calla", analisis.propuesta_de_acuerdo(accionable, inhabiles), None)
    p = analisis.propuesta_de_acuerdo(accionable, inhabiles, sin_plazo=True)
    probar("con --sin-plazo propone revisar", p["evento"]["tipo"], "Tarea")


def pruebas_cli(carpeta: Path) -> None:
    print("\n── Línea de comandos ──")
    base = str(carpeta / "cli.db")
    probar("demo carga los ejemplos", cli.main(["--base", base, "demo"]), 0)
    probar("estado responde", cli.main(["--base", base, "estado"]), 0)
    probar("buscar responde", cli.main(["--base", base, "buscar", "--texto", "amparo"]), 0)
    probar("vigilar responde", cli.main(["--base", base, "vigilar", "452/2026"]), 0)
    probar("vigilar basura devuelve error", cli.main(["--base", base, "vigilar", "nada"]), 1)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="monitor-pruebas-") as tmp:
        carpeta = Path(tmp)
        pruebas_normalizacion()
        pruebas_almacen(carpeta)
        pruebas_huella(carpeta)
        pruebas_seguridad(carpeta)
        pruebas_analisis()
        pruebas_cli(carpeta)
    print()
    print("Todo en orden." if not FALLAS else f"{FALLAS} prueba(s) fallaron.")
    return 1 if FALLAS else 0


if __name__ == "__main__":
    raise SystemExit(main())
