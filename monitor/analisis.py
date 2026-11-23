"""Lee un acuerdo y propone un evento. Sin modelo de lenguaje: solo reglas.

Esto es deliberado. Detectar «tres días hábiles» o «las nueve treinta horas del
diez de diciembre» es reconocer patrones, y los patrones se pueden probar uno
por uno. Un modelo de lenguaje aquí añadiría costo, red y la posibilidad de
inventar, sin ganar nada.

Tres reglas que no se rompen:
  1. Si el acuerdo NO dice si los días son hábiles o naturales, no se adivina:
     se propone una tarea para revisar el plazo, no una fecha de vencimiento.
  2. El fundamento solo se cita si aparece literalmente en el acuerdo.
  3. La fecha límite la calcula plazos.py y viaja con su conteo día por día.
"""
from __future__ import annotations

import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

# El conteo de plazos se comparte con el asistente: una sola implementación,
# con sus propias pruebas, en vez de dos que se puedan separar.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agente"))
from plazos import contar

# Números escritos con letras, hasta 31: lo que necesita un plazo o un día.
_LETRAS = {
    "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "once": 11,
    "doce": 12, "trece": 13, "catorce": 14, "quince": 15, "dieciseis": 16,
    "diecisiete": 17, "dieciocho": 18, "diecinueve": 19, "veinte": 20,
    "veintiuno": 21, "veintiun": 21, "veintidos": 22, "veintitres": 23,
    "veinticuatro": 24, "veinticinco": 25, "veintiseis": 26, "veintisiete": 27,
    "veintiocho": 28, "veintinueve": 29, "treinta": 30, "treinta y uno": 31,
}
_MESES = {m: i + 1 for i, m in enumerate(
    ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
     "agosto", "septiembre", "octubre", "noviembre", "diciembre"])}

MAX_DIAS_PLAZO = 180


def limpiar(texto: str | None) -> str:
    """Minúsculas, sin acentos y con espacios normalizados."""
    base = unicodedata.normalize("NFD", str(texto or ""))
    base = "".join(c for c in base if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", base).lower().strip()


def numero(palabra: str) -> int | None:
    """Convierte «3», «tres» o «treinta y uno» en un entero."""
    p = limpiar(palabra)
    if p.isdigit():
        return int(p)
    return _LETRAS.get(p)


def anio_en_letras(texto: str) -> int | None:
    """«dos mil veintiseis» → 2026. Solo años de este siglo y el pasado."""
    t = limpiar(texto)
    m = re.search(r"\b(19|20)\d{2}\b", t)
    if m:
        return int(m.group(0))
    m = re.search(r"\bdos mil(?:\s+([a-z]+(?:\s+y\s+[a-z]+)?))?\b", t)
    if m:
        resto = (m.group(1) or "").strip()
        return 2000 + (numero(resto) or 0) if (not resto or numero(resto) is not None) else None
    m = re.search(r"\bmil novecientos\b", t)
    return 1900 if m else None


_PLAZO = re.compile(
    r"(?:termino|plazo)\s+(?:comun\s+)?de\s+"
    r"(\d{1,3}|[a-z]+(?:\s+y\s+[a-z]+)?)\s+dias?"
    r"(\s+(?:habiles|naturales))?",
)


def detectar_plazo(texto: str) -> dict | None:
    """Encuentra «término de tres días hábiles» y devuelve días y tipo de conteo."""
    t = limpiar(texto)
    m = _PLAZO.search(t)
    if not m:
        return None
    dias = numero(m.group(1))
    if dias is None or not (1 <= dias <= MAX_DIAS_PLAZO):
        return None
    clase = (m.group(2) or "").strip()
    return {
        "dias": dias,
        # Si el acuerdo no lo dice, se queda en «sin especificar»: NO se adivina.
        "cuenta": "habiles" if clase == "habiles" else "naturales" if clase == "naturales" else "sin especificar",
        "frase": m.group(0),
    }


_HORA = re.compile(r"\b(\d{1,2})[:.](\d{2})\s*(?:horas|hrs|hras)?\b")
_HORA_LETRAS = re.compile(
    r"\b(?:las\s+)?([a-z]+(?:\s+y\s+[a-z]+)?)\s*(treinta|quince|cuarenta y cinco)?\s*horas\b")
_FECHA_LETRAS = re.compile(
    r"\bdia\s+(\d{1,2}|[a-z]+(?:\s+y\s+[a-z]+)?)\s+de\s+([a-z]+)\s+de\s+([^,.;]{3,30})")
_FECHA_DIGITOS = re.compile(r"\b(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})\b")
_SENALA = re.compile(r"se\s+(?:senala|senalan|fija|fijan)\b")


def detectar_audiencia(texto: str) -> dict | None:
    """Encuentra «se señala(n) … las nueve treinta horas del día diez de diciembre…»."""
    t = limpiar(texto)
    if not _SENALA.search(t):
        return None

    fecha = None
    m = _FECHA_LETRAS.search(t)
    if m:
        dia, mes_txt, anio_txt = numero(m.group(1)), _MESES.get(m.group(2)), anio_en_letras(m.group(3))
        if dia and mes_txt and anio_txt:
            try:
                fecha = date(anio_txt, mes_txt, dia)
            except ValueError:
                fecha = None
    if fecha is None:
        m = _FECHA_DIGITOS.search(t)
        if m:
            try:
                fecha = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            except ValueError:
                fecha = None
    if fecha is None:
        return None

    hora = ""
    m = _HORA.search(t)
    if m and 0 <= int(m.group(1)) <= 23:
        hora = f"{int(m.group(1)):02d}:{m.group(2)}"
    else:
        m = _HORA_LETRAS.search(t)
        if m:
            h = numero(m.group(1))
            minutos = {"treinta": 30, "quince": 15, "cuarenta y cinco": 45}.get(m.group(2) or "", 0)
            if h is not None and 0 <= h <= 23:
                hora = f"{h:02d}:{minutos:02d}"
    return {"fecha": fecha.isoformat(), "hora": hora}


# Palabras del acuerdo → tipo de evento de la agenda. El orden importa: gana
# la primera que coincida.
_CLASES = [
    (r"\bvista\b", "Vencimiento", "Desahogar vista"),
    (r"\brequiere|requerimiento\b", "Vencimiento", "Cumplir requerimiento"),
    (r"\bprevien|prevencion\b", "Vencimiento", "Desahogar prevención"),
    (r"\bconteste|contestacion de la demanda\b", "Vencimiento", "Contestar demanda"),
    (r"\balegatos\b", "Vencimiento", "Presentar alegatos"),
    (r"\bapel|recurso\b", "Vencimiento", "Plazo de recurso"),
    (r"\baudiencia\b", "Audiencia", "Audiencia"),
    (r"\bsentencia\b", "Vigilancia", "Sentencia dictada"),
    (r"\badmite\b", "Vigilancia", "Admisión"),
]

_FUNDAMENTO = re.compile(r"\barticulos?\s+[\d\w\s,.ºo-]{1,40}", re.IGNORECASE)


def fundamento(texto: str) -> str:
    """Devuelve el artículo SOLO si aparece literalmente en el acuerdo."""
    m = _FUNDAMENTO.search(str(texto or ""))
    return m.group(0).strip(" .,;")[:120] if m else ""


def clasificar(texto: str) -> tuple[str, str]:
    t = limpiar(texto)
    for patron, tipo, titulo in _CLASES:
        if re.search(patron, t):
            return tipo, titulo
    return "Tarea", "Revisar acuerdo"


def propuesta_de_acuerdo(acuerdo: dict, inhabiles: set[date] | None = None,
                         sin_plazo: bool = False) -> dict | None:
    """Convierte un acuerdo en una propuesta de evento, o None si no hay nada que proponer.

    La propuesta sale en el mismo formato que ya entiende y valida la agenda,
    así que no hay un camino nuevo: entra por donde ya entran las del asistente,
    y tú la apruebas o la descartas.
    """
    texto = f"{acuerdo.get('sintesis', '')} {acuerdo.get('texto', '')}".strip()
    if not texto:
        return None
    base_txt = acuerdo.get("fecha_acuerdo") or ""
    try:
        base = date.fromisoformat(base_txt[:10])
    except ValueError:
        return None

    inhabiles = inhabiles or set()
    tipo, titulo = clasificar(texto)
    conteo: list[str] = []
    explicacion = ""
    fecha = base.isoformat()
    hora = ""

    audiencia = detectar_audiencia(texto)
    plazo = detectar_plazo(texto)

    if audiencia:
        tipo, fecha, hora = "Audiencia", audiencia["fecha"], audiencia["hora"]
        titulo = "Audiencia" if titulo == "Audiencia" else f"{titulo} (audiencia)"
        explicacion = (f"El acuerdo señala audiencia para el {fecha}"
                       + (f" a las {hora}." if hora else ", sin hora clara en el texto."))
        conteo = [f"Fecha tomada del acuerdo: {fecha}" + (f", {hora} horas." if hora else "."),
                  "No es un plazo contado: es la fecha que el propio acuerdo fija. Verifícala."]
    elif plazo and plazo["cuenta"] in ("habiles", "naturales"):
        try:
            limite, conteo = contar(base, plazo["dias"], plazo["cuenta"], inhabiles)
            fecha = limite.isoformat()
            explicacion = (f"El acuerdo abre un plazo de {plazo['dias']} día(s) "
                           f"{'hábiles' if plazo['cuenta'] == 'habiles' else 'naturales'} "
                           f"(«{plazo['frase']}»), contado desde la fecha del acuerdo.")
            conteo.insert(0, "AVISO: se contó desde la fecha del acuerdo. Si la notificación "
                             "surtió efectos otro día, corrige la fecha al aprobar.")
        except ValueError as e:
            return _tarea_revisar(acuerdo, base, f"No se pudo contar el plazo: {e}")
    elif plazo:
        # Hay plazo pero el acuerdo no dice si son hábiles o naturales.
        # No se adivina: se propone revisarlo, no una fecha de vencimiento.
        return _tarea_revisar(
            acuerdo, base,
            f"El acuerdo abre un plazo de {plazo['dias']} día(s) («{plazo['frase']}») pero no dice "
            f"si son hábiles o naturales. Revísalo y captura el vencimiento tú.")
    elif sin_plazo and tipo != "Tarea":
        # El acuerdo parece accionable pero no trae plazo ni fecha. Solo se
        # propone si tú lo pediste: por omisión se calla, para no llenarte la
        # agenda de tareas sin contenido.
        return _tarea_revisar(acuerdo, base,
                              f"El acuerdo parece requerir actuación ({titulo.lower()}) pero no "
                              f"señala plazo ni fecha. Revísalo y decide qué capturar.")
    else:
        return None

    exp = acuerdo.get("expediente") or ""
    return {
        "uid": str(acuerdo.get("huella") or acuerdo.get("clave") or "")[:32] + "-ev",
        "peticion_uid": None,
        "resumen": f"{titulo}{f' · Exp. {exp}' if exp else ''}",
        "explicacion": explicacion + " Propuesta del monitor de acuerdos: revísala antes de aprobar.",
        "fundamento": fundamento(texto),
        "conteo": conteo,
        "evento": {
            "categoria": "Asunto del despacho",
            "tipo": tipo,
            "titulo": titulo[:80],
            "fecha": fecha,
            "hora": hora,
            "expediente_num": exp,
            "lugar": str(acuerdo.get("juzgado") or "")[:200],
            "notas": f"Del acuerdo del {base.isoformat()} ({acuerdo.get('fuente', '')}).\n"
                     f"{str(acuerdo.get('sintesis') or '')[:500]}",
            "recordatorios": [1440] if tipo in ("Vencimiento", "Vigilancia") else [60, 1440],
        },
    }


def _tarea_revisar(acuerdo: dict, base: date, motivo: str) -> dict:
    exp = acuerdo.get("expediente") or ""
    return {
        "uid": str(acuerdo.get("huella") or acuerdo.get("clave") or "")[:32] + "-rev",
        "peticion_uid": None,
        "resumen": f"Revisar plazo{f' · Exp. {exp}' if exp else ''}",
        "explicacion": motivo + " Propuesta del monitor de acuerdos: revísala antes de aprobar.",
        "fundamento": fundamento(f"{acuerdo.get('sintesis', '')} {acuerdo.get('texto', '')}"),
        "conteo": [motivo],
        "evento": {
            "categoria": "Asunto del despacho", "tipo": "Tarea",
            "titulo": "Revisar plazo del acuerdo", "fecha": base.isoformat(), "hora": "",
            "expediente_num": exp, "lugar": str(acuerdo.get("juzgado") or "")[:200],
            "notas": f"{motivo}\n{str(acuerdo.get('sintesis') or '')[:500]}",
            "recordatorios": [1440],
        },
    }
