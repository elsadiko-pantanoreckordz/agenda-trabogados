"""Conteo de plazos. Lo hace Python, no el modelo.

El modelo lee el documento y dice «tres días hábiles desde el 24 de noviembre».
Contar los días es aritmética, y la aritmética no se delega a un modelo de
lenguaje: aquí se cuenta de forma verificable y se entrega el conteo día por día
para que el abogado lo revise.
"""
from __future__ import annotations

from datetime import date, timedelta

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
MAX_DIAS = 365          # tope de seguridad: ningún plazo razonable lo pasa


def largo(d: date) -> str:
    return f"{DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]} de {d.year}"


def contar(desde: date, dias: int, cuenta: str, inhabiles: set[date]) -> tuple[date, list[str]]:
    """Devuelve la fecha límite y el conteo día por día.

    El conteo empieza el día siguiente a `desde`. Cuándo surte efectos una
    notificación depende del código aplicable, así que eso NO se adivina:
    `desde` es la fecha que el abogado verifica, y el conteo lo dice en voz alta.
    """
    if dias < 1 or dias > MAX_DIAS:
        raise ValueError(f"Número de días fuera de lo razonable: {dias}")
    if cuenta not in ("habiles", "naturales"):
        raise ValueError(f"Tipo de conteo desconocido: {cuenta}")

    detalle = [f"Se cuenta a partir del día siguiente al {largo(desde)}.",
               f"Plazo: {dias} día(s) {'hábil(es)' if cuenta == 'habiles' else 'natural(es)'}."]
    contados, d, vueltas = 0, desde, 0
    while contados < dias:
        d += timedelta(days=1)
        vueltas += 1
        if vueltas > MAX_DIAS * 3:
            raise ValueError("No se pudo cerrar el conteo: revisa los días inhábiles")
        if cuenta == "habiles":
            if d.weekday() >= 5:
                detalle.append(f"  {largo(d)}: no corre (fin de semana)")
                continue
            if d in inhabiles:
                detalle.append(f"  {largo(d)}: no corre (día inhábil registrado)")
                continue
        contados += 1
        detalle.append(f"  Día {contados}: {largo(d)}")

    detalle.append(f"Vence el {largo(d)}.")
    if cuenta == "naturales" and (d.weekday() >= 5 or d in inhabiles):
        detalle.append("AVISO: el último día cae en día inhábil. Verifica si el plazo se corre al siguiente hábil.")
    detalle.append("Conteo hecho por la computadora sobre los días inhábiles que tú registraste. Verifícalo.")
    return d, detalle


def _autoprueba() -> int:
    fallas = 0

    def probar(nombre, obtenido, esperado):
        nonlocal fallas
        ok = obtenido == esperado
        print(f"{'OK  ' if ok else 'FALLA'} {nombre}: {obtenido}{'' if ok else f' (se esperaba {esperado})'}")
        if not ok:
            fallas += 1

    # Martes 24 de noviembre de 2026 + 3 hábiles = viernes 27.
    f, _ = contar(date(2026, 11, 24), 3, "habiles", set())
    probar("3 hábiles desde martes", f, date(2026, 11, 27))

    # Jueves + 3 hábiles salta sábado y domingo = martes siguiente.
    f, _ = contar(date(2026, 11, 26), 3, "habiles", set())
    probar("3 hábiles cruzando fin de semana", f, date(2026, 12, 1))

    # Con un inhábil en medio (viernes 27) se corre un día más.
    f, _ = contar(date(2026, 11, 24), 3, "habiles", {date(2026, 11, 27)})
    probar("3 hábiles con un inhábil", f, date(2026, 11, 30))

    # Naturales no salta nada.
    f, _ = contar(date(2026, 11, 26), 3, "naturales", set())
    probar("3 naturales", f, date(2026, 11, 29))

    # El aviso del último día inhábil aparece.
    _, det = contar(date(2026, 11, 26), 3, "naturales", set())
    probar("avisa que el último día es domingo", any("AVISO" in x for x in det), True)

    # Entradas absurdas se rechazan.
    for dias in (0, -5, 10_000):
        try:
            contar(date(2026, 1, 1), dias, "habiles", set())
            probar(f"rechaza {dias} días", "aceptado", "rechazado")
        except ValueError:
            probar(f"rechaza {dias} días", "rechazado", "rechazado")
    return fallas


if __name__ == "__main__":
    raise SystemExit(_autoprueba())
