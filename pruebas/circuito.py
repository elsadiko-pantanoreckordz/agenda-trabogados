"""Circuito completo sin gastar en la API: se simula la respuesta del modelo."""
import json, sys, types
from datetime import date
from pathlib import Path

AG = Path("/home/user/agenda-trabogados/agente")
sys.path.insert(0, str(AG))
import agente_pc
from cripto import cifrar, descifrar

CLAVE = "clave-de-sincronizacion-del-despacho"
P = Path(sys.argv[1])

# La tablet (código real de index.html, cifrado en node) dejó esta charola:
charola = {"formato": "agenda-rt-peticiones", "version": 1, "peticiones": [
    {"uid": "pet1", "clase": "texto", "texto": "vista por tres dias del acuerdo del 452/2026, notificado el 24 de noviembre de 2026",
     "expediente_num": "452/2026", "imagen": None, "creado": "2026-11-23T10:00:00Z"},
    {"uid": "pet2", "clase": "texto", "texto": "audiencia de pruebas el 10 de diciembre a las 9:30 en el juzgado tercero civil de Hermosillo",
     "expediente_num": "100/2026", "imagen": None, "creado": "2026-11-23T10:05:00Z"},
]}
(P / "pendientes.json").write_text(json.dumps(cifrar(charola, CLAVE, "pendientes")))

# Respuestas que daría el modelo, con el esquema exacto que le exigimos.
RESPUESTAS = {
    "pet1": {"clase": "plazo", "titulo": "Desahogar vista", "tipo": "Vencimiento", "expediente_num": "452/2026",
             "fecha": "", "hora": "", "lugar": "", "notas": "Vista del acuerdo.", "tiene_plazo": True,
             "plazo_dias": 3, "plazo_cuenta": "habiles", "plazo_desde": "2026-11-24",
             "fundamento": "", "explicacion": "El acuerdo concede tres días hábiles.", "confianza": "alta", "faltante": ""},
    "pet2": {"clase": "evento", "titulo": "Audiencia de pruebas", "tipo": "Audiencia", "expediente_num": "100/2026",
             "fecha": "2026-12-10", "hora": "09:30", "lugar": "Juzgado Tercero de Primera Instancia de lo Civil del Distrito Judicial de Hermosillo",
             "notas": "", "tiene_plazo": False, "plazo_dias": 0, "plazo_cuenta": "ninguno", "plazo_desde": "",
             "fundamento": "", "explicacion": "Fecha y hora directas de la nota.", "confianza": "alta", "faltante": ""},
}

def preguntar_falso(cliente, peticion, modelo, esfuerzo):
    datos = RESPUESTAS[peticion["uid"]]
    r = types.SimpleNamespace(stop_reason="end_turn",
        content=[types.SimpleNamespace(type="text", text=json.dumps(datos))],
        usage=types.SimpleNamespace(input_tokens=1200, output_tokens=240))
    return r, peticion["texto"]

agente_pc.preguntar = preguntar_falso
agente_pc.BITACORA = P / "bitacora.jsonl"
sys.modules["anthropic"] = types.SimpleNamespace(Anthropic=lambda: object())
sys.argv = ["agente_pc.py", str(P / "pendientes.json"), "-s", str(P / "propuestas.json")]
import os; os.environ["AGENDA_CLAVE_SYNC"] = CLAVE

codigo = agente_pc.main()
print("salida del programa:", codigo)

res = descifrar(json.loads((P / "propuestas.json").read_text()), CLAVE, "propuestas")
fallas = 0
def probar(n, obtenido, esperado):
    global fallas
    ok = obtenido == esperado
    print(f"{'OK  ' if ok else 'FALLA'} {n}: {obtenido}" + ("" if ok else f" (se esperaba {esperado})"))
    if not ok: fallas += 1

probar("dos propuestas", len(res["propuestas"]), 2)
probar("ambos pendientes marcados atendidos", sorted(res["peticiones_atendidas"]), ["pet1", "pet2"])
plazo = next(x for x in res["propuestas"] if x["evento"]["tipo"] == "Vencimiento")
# 24 nov 2026 es martes: 3 hábiles vencen el viernes 27.
probar("plazo contado por la computadora", plazo["evento"]["fecha"], "2026-11-27")
probar("trae el conteo día por día", len(plazo["conteo"]) >= 5, True)
probar("dice que hay que verificar", any("Verifícalo" in x for x in plazo["conteo"]), True)
aud = next(x for x in res["propuestas"] if x["evento"]["tipo"] == "Audiencia")
probar("audiencia con fecha y hora", (aud["evento"]["fecha"], aud["evento"]["hora"]), ("2026-12-10", "09:30"))
bit = [json.loads(l) for l in (P / "bitacora.jsonl").read_text().splitlines()]
probar("bitácora con dos renglones", len(bit), 2)
probar("bitácora sin copiar el texto", all("texto" not in b or not isinstance(b.get("texto"), str) for b in bit), True)
probar("bitácora guarda huella, no contenido", "huella_texto" in bit[0] and len(bit[0]["huella_texto"]) == 16, True)
sys.exit(1 if fallas else 0)
