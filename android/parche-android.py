#!/usr/bin/env python3
"""Genera la copia Android de la agenda a partir de index.html.

Cada cambio se aplica con reemplazo exacto y verificado: si el original cambia
y un fragmento ya no aparece, el script falla en lugar de dejar la app a medias.
"""
import sys

ORIGEN, DESTINO = sys.argv[1], sys.argv[2]
html = open(ORIGEN, encoding="utf-8").read()

CAMBIOS = [
    # 1. Base de datos propia: nombre distinto al de la agenda de la PC/tablet.
    ('indexedDB.open("agenda_rt", 1)',
     'indexedDB.open("agenda_rt_android", 1)'),

    # 2. La app de Android nunca habla con la computadora: trabaja sola.
    ('const HAY_PC = !/github\\.io$/.test(location.hostname);',
     'const HAY_PC = false;   // App de Android: base de datos propia, sin servidor.'),

    # 3. Mensaje claro cuando algo pedía la computadora.
    ('throw new Error("Esta función necesita la computadora. Usa «Sincronizar» → archivo.");',
     'throw new Error("Esta función era de la computadora. En Android usa «⟳ Compartir datos».");'),

    # 4. Sin service worker: los archivos ya vienen dentro de la app.
    ('  if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});\n',
     '  // Sin service worker: en Android los archivos ya están dentro de la app.\n'),

    # 5. Descarga -> guardar y compartir por Android. El objeto ya viene cifrado.
    ('''function bajar(nombre, obj) {
  const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([JSON.stringify(obj)], {type: "application/json"}));
  a.download = nombre; document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
}''',
     '''function bajar(nombre, obj) {
  // En Android no hay carpeta de descargas del navegador: el archivo se entrega
  // a Android, que abre el menú de compartir (OneDrive, correo, etc.).
  const texto = JSON.stringify(obj);
  if (window.puenteAgenda && window.puenteAgenda.postMessage) {
    window.puenteAgenda.postMessage(JSON.stringify({accion: "compartir", nombre, contenido: texto}));
    return aviso("Archivo listo: elige dónde guardarlo o enviarlo.");
  }
  if (window.PuenteAgendaLegado && window.PuenteAgendaLegado.guardarArchivo) {
    return window.PuenteAgendaLegado.guardarArchivo(nombre, texto)
      ? aviso("Archivo listo: elige dónde guardarlo o enviarlo.")
      : aviso("No se pudo generar el archivo", 1);
  }
  const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([texto], {type: "application/json"}));
  a.download = nombre; document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
}'''),

    # 6. Textos: compartir datos es opcional, no una obligación.
    ('<h2 style="margin:0">Sincronizar con la computadora</h2>',
     '<h2 style="margin:0">Compartir datos (opcional)</h2>'),
    ('<p class="t2">Sin red directa con la computadora, la sincronización se hace con un archivo cifrado (por OneDrive). Se pide la clave de sincronización.</p>',
     '<p class="t2">Esta agenda guarda todo en este dispositivo y funciona sola. Si quieres, puedes enviar o recibir datos con un archivo cifrado; no es necesario para usarla.</p>'),
    ('⬆ Enviar mis cambios a la computadora (${D.cola.length})',
     '⬆ Enviar mis cambios (${D.cola.length})'),
    ('<div class="t2" style="margin:4px 0 14px">Descarga «cambios_tablet_….json». Guárdalo en OneDrive › Agenda RT; la agenda de la computadora lo importa.</div>',
     '<div class="t2" style="margin:4px 0 14px">Genera «cambios_tablet_….json» cifrado y elige a dónde enviarlo (OneDrive, correo…). La agenda de la computadora lo puede importar.</div>'),
    ('⬇ Recibir datos de la computadora',
     '⬇ Recibir datos de un archivo'),
    ('<div class="t2" style="margin:4px 0 14px">Elige el archivo «datos_agenda.json» (OneDrive › Agenda RT). Tus cambios pendientes se conservan.</div>',
     '<div class="t2" style="margin:4px 0 14px">Elige un archivo «datos_agenda.json» o un respaldo. Tus cambios pendientes se conservan.</div>'),
    ('⤓ Respaldo completo de la tablet (cifrado)',
     '⤓ Respaldo completo de esta agenda (cifrado)'),
    ('`⟳ Sincronizar${n ? ` <span class="badge">${n}</span>` : ""}`',
     '`⟳ Compartir datos${n ? ` <span class="badge">${n}</span>` : ""}`'),
    ('<div class="t2" style="margin-top:12px">La agenda funciona en esta tablet sin internet. Para pasar tus datos a la computadora usa «Sincronizar».</div>',
     '<div class="t2" style="margin-top:12px">La agenda funciona en este dispositivo sin internet y con su propia base de datos. Compartir datos con la computadora es opcional.</div>'),
    ('<title>Agenda RT</title>', '<title>Agenda RT · Android</title>'),
]

for viejo, nuevo in CAMBIOS:
    n = html.count(viejo)
    if n != 1:
        sys.exit("ERROR: el fragmento aparece %d veces (se esperaba 1):\n%s" % (n, viejo[:120]))
    html = html.replace(viejo, nuevo)

open(DESTINO, "w", encoding="utf-8").write(html)
print("index.html adaptado: %d cambios" % len(CAMBIOS))
