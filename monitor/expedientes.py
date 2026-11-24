"""Normalización de números de expediente.

Los boletines escriben el mismo expediente de muchas formas: «123/2024»,
«00123/2024», «123/2024-II», «Exp. 123/24». Para empatar con la tabla
`expedientes` de la agenda, que los guarda como «número/año», aquí se
reducen todos a una forma canónica.

No toca la red ni archivos: es texto puro, y por eso se puede probar entero.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date

# Límites de cordura: fuera de esto no es un expediente, es otra cosa.
ANIO_MIN = 1900
NUMERO_MAX = 999_999

# Sufijos que distinguen cuadernos o secciones del mismo expediente.
_ROMANOS = r"(?:I{1,3}|IV|V|VI{1,3}|IX|X{1,2})"
_SUFIJO = rf"(?:{_ROMANOS}|BIS|TER|[A-Z])"

_PATRON = re.compile(
    r"(?<![\d/-])"                       # que no venga pegado a otro número
    r"(?P<numero>\d{1,6})"
    r"\s*[/-]\s*"
    r"(?P<anio>\d{2}|\d{4})"
    r"(?!\s*[/-]?\s*\d)"                 # ni seguido de otro: «12/2024/2025» no es expediente
    # El cuaderno pegado con guion admite hasta una letra suelta («123/2024-A»);
    # separado por espacio solo se acepta romano, BIS o TER, para no confundir
    # con la palabra siguiente («452/2026 y su acumulado» no es el cuaderno «Y»).
    rf"(?:\s*[-/]\s*(?P<sufijo>{_SUFIJO})|\s+(?P<sufijo_suelto>{_ROMANOS}|BIS|TER))?"
    r"(?![A-Z0-9])",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Expediente:
    """Un expediente ya normalizado."""

    numero: int
    anio: int
    sufijo: str = ""

    @property
    def canonico(self) -> str:
        """Forma para empatar con la agenda: «123/2024», sin sufijo."""
        return f"{self.numero}/{self.anio}"

    @property
    def completo(self) -> str:
        """Forma completa, con el cuaderno o sección si venía: «123/2024-II»."""
        return f"{self.canonico}-{self.sufijo}" if self.sufijo else self.canonico

    def misma_causa(self, otro: Expediente) -> bool:
        """Mismo expediente aunque sea otro cuaderno."""
        return (self.numero, self.anio) == (otro.numero, otro.anio)

    def __str__(self) -> str:
        return self.completo


def _sin_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto)
                   if unicodedata.category(c) != "Mn")


def _anio_completo(crudo: str, hoy: date | None = None) -> int | None:
    """«24» es 2024; «99» es 1999. Un año futuro de dos dígitos no existe."""
    anio = int(crudo)
    if len(crudo) == 4:
        return anio if ANIO_MIN <= anio <= (hoy or date.today()).year + 1 else None
    tope = (hoy or date.today()).year
    candidato = 2000 + anio
    if candidato > tope + 1:
        candidato = 1900 + anio
    return candidato if ANIO_MIN <= candidato <= tope + 1 else None


def normalizar(texto: str | None, hoy: date | None = None) -> Expediente | None:
    """Devuelve el primer expediente que encuentre en el texto, o None."""
    encontrados = extraer(texto, hoy=hoy, limite=1)
    return encontrados[0] if encontrados else None


def extraer(texto: str | None, hoy: date | None = None, limite: int = 50) -> list[Expediente]:
    """Todos los expedientes distintos que aparezcan en un texto, en orden."""
    if not texto:
        return []
    limpio = _sin_acentos(str(texto)).upper()
    salida: list[Expediente] = []
    vistos: set[tuple[int, int, str]] = set()
    for m in _PATRON.finditer(limpio):
        numero = int(m.group("numero"))
        anio = _anio_completo(m.group("anio"), hoy=hoy)
        if anio is None or not (1 <= numero <= NUMERO_MAX):
            continue
        sufijo = (m.group("sufijo") or m.group("sufijo_suelto") or "").upper().strip()
        llave = (numero, anio, sufijo)
        if llave in vistos:
            continue
        vistos.add(llave)
        salida.append(Expediente(numero=numero, anio=anio, sufijo=sufijo))
        if len(salida) >= limite:
            break
    return salida


def canonico(texto: str | None, hoy: date | None = None) -> str:
    """Atajo: la forma «123/2024» o cadena vacía si no hay expediente."""
    e = normalizar(texto, hoy=hoy)
    return e.canonico if e else ""


def _autoprueba() -> int:
    fallas = 0
    hoy = date(2026, 11, 23)

    def probar(nombre: str, obtenido, esperado) -> None:
        nonlocal fallas
        ok = obtenido == esperado
        print(f"{'OK   ' if ok else 'FALLA'} {nombre}: {obtenido!r}"
              + ("" if ok else f" (se esperaba {esperado!r})"))
        if not ok:
            fallas += 1

    # Las tres formas que pediste tienen que dar el mismo canónico.
    for crudo in ("123/2024", "00123/2024", "123/2024-II", "Exp. 123/2024",
                  "EXPEDIENTE 123 / 2024", "123-2024", "123/24"):
        probar(f"canónico de {crudo!r}", canonico(crudo, hoy), "123/2024")

    probar("conserva el cuaderno", normalizar("123/2024-II", hoy).completo, "123/2024-II")
    probar("cuaderno con espacio", normalizar("123/2024 II", hoy).completo, "123/2024-II")
    probar("cuaderno BIS", normalizar("45/2023 BIS", hoy).completo, "45/2023-BIS")
    probar("sufijo de una letra", normalizar("45/2023-A", hoy).completo, "45/2023-A")

    # Mismo expediente, distinto cuaderno.
    a, b = normalizar("123/2024", hoy), normalizar("123/2024-II", hoy)
    probar("misma causa, otro cuaderno", a.misma_causa(b), True)
    probar("no son iguales", a == b, False)
    probar("distinta causa", a.misma_causa(normalizar("124/2024", hoy)), False)

    # Años de dos dígitos.
    probar("«99» es 1999", normalizar("7/99", hoy).anio, 1999)
    probar("«26» es 2026", normalizar("7/26", hoy).anio, 2026)
    probar("«27» aún es válido", normalizar("7/27", hoy).anio, 2027)
    probar("«30» no es 2030 futuro", normalizar("7/30", hoy).anio, 1930)

    # Lo que NO es un expediente.
    for basura in ("", None, "sin número", "12/2024/2025", "0/2024", "1234567/2024",
                   "123/1800", "123/2050", "teléfono 6621234567"):
        probar(f"descarta {basura!r}", canonico(basura, hoy), "")

    # Varios en un mismo párrafo, como en un boletín.
    texto = ("En los autos del expediente 452/2026 y su acumulado 00453/2026-II, "
             "así como en el 452/2026 (repetido), se acuerda…")
    probar("extrae todos sin repetir",
           [e.completo for e in extraer(texto, hoy)],
           ["452/2026", "453/2026-II"])

    # Acentos y mayúsculas no estorban.
    probar("con acentos", canonico("Expediénte Núm. 88/2025", hoy), "88/2025")
    return fallas


if __name__ == "__main__":
    raise SystemExit(_autoprueba())
