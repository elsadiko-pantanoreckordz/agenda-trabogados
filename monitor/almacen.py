"""Almacén local de acuerdos: SQLite con búsqueda de texto completo (FTS5).

Decisión de seguridad: esta es una base **propia y aparte** (`datos/acuerdos.db`).
No abre ni migra `agenda_rt.db`, así que no puede alterar las tablas existentes
de la agenda. El empate con los expedientes del despacho se hace por número
normalizado al momento de exportar, no con llaves foráneas.

Todo el SQL va parametrizado. El texto que escribe el usuario nunca se concatena
en una consulta: ni en el SQL ni en la sintaxis propia de FTS5.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import sqlite3
import unicodedata
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from expedientes import canonico

registro = logging.getLogger("monitor.almacen")

VERSION_ESQUEMA = 1
LIMITE_PREDETERMINADO = 50
LIMITE_MAXIMO = 500

# Campos que definen la identidad de un acuerdo. Si cambia cualquiera de ellos,
# la huella cambia y el acuerdo se considera nuevo (o modificado).
_CAMPOS_HUELLA = ("fuente", "clave", "expediente", "juzgado", "fecha_acuerdo", "sintesis", "texto")

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS acuerdos (
    id               INTEGER PRIMARY KEY,
    fuente           TEXT NOT NULL,
    clave            TEXT NOT NULL,
    expediente       TEXT NOT NULL DEFAULT '',
    expediente_crudo TEXT NOT NULL DEFAULT '',
    juzgado          TEXT NOT NULL DEFAULT '',
    distrito         TEXT NOT NULL DEFAULT '',
    materia          TEXT NOT NULL DEFAULT '',
    jurisdiccion     TEXT NOT NULL DEFAULT '',
    partes           TEXT NOT NULL DEFAULT '',
    fecha_acuerdo    TEXT NOT NULL DEFAULT '',
    fecha_publicacion TEXT NOT NULL DEFAULT '',
    sintesis         TEXT NOT NULL DEFAULT '',
    texto            TEXT NOT NULL DEFAULT '',
    url_lista        TEXT NOT NULL DEFAULT '',
    url_documento    TEXT NOT NULL DEFAULT '',
    archivo          TEXT NOT NULL DEFAULT '',
    huella           TEXT NOT NULL UNIQUE,
    nuevo            INTEGER NOT NULL DEFAULT 1,
    creado           TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_acuerdos_exp   ON acuerdos(expediente);
CREATE INDEX IF NOT EXISTS idx_acuerdos_fecha ON acuerdos(fecha_acuerdo);
CREATE INDEX IF NOT EXISTS idx_acuerdos_nuevo ON acuerdos(nuevo);
CREATE UNIQUE INDEX IF NOT EXISTS idx_acuerdos_fuente_clave ON acuerdos(fuente, clave);

-- Índice de texto completo. «external content»: el texto vive una sola vez,
-- en la tabla acuerdos, y aquí solo se guarda el índice.
CREATE VIRTUAL TABLE IF NOT EXISTS acuerdos_fts USING fts5(
    expediente, juzgado, partes, sintesis, texto,
    content='acuerdos', content_rowid='id',
    tokenize="unicode61 remove_diacritics 2"
);
CREATE TRIGGER IF NOT EXISTS acuerdos_ai AFTER INSERT ON acuerdos BEGIN
    INSERT INTO acuerdos_fts(rowid, expediente, juzgado, partes, sintesis, texto)
    VALUES (new.id, new.expediente, new.juzgado, new.partes, new.sintesis, new.texto);
END;
CREATE TRIGGER IF NOT EXISTS acuerdos_ad AFTER DELETE ON acuerdos BEGIN
    INSERT INTO acuerdos_fts(acuerdos_fts, rowid, expediente, juzgado, partes, sintesis, texto)
    VALUES ('delete', old.id, old.expediente, old.juzgado, old.partes, old.sintesis, old.texto);
END;
CREATE TRIGGER IF NOT EXISTS acuerdos_au AFTER UPDATE ON acuerdos BEGIN
    INSERT INTO acuerdos_fts(acuerdos_fts, rowid, expediente, juzgado, partes, sintesis, texto)
    VALUES ('delete', old.id, old.expediente, old.juzgado, old.partes, old.sintesis, old.texto);
    INSERT INTO acuerdos_fts(rowid, expediente, juzgado, partes, sintesis, texto)
    VALUES (new.id, new.expediente, new.juzgado, new.partes, new.sintesis, new.texto);
END;

CREATE TABLE IF NOT EXISTS vigilados (
    expediente TEXT PRIMARY KEY,
    nota       TEXT NOT NULL DEFAULT '',
    activo     INTEGER NOT NULL DEFAULT 1,
    agregado   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fuentes (
    nombre          TEXT PRIMARY KEY,
    ultima_revision TEXT NOT NULL DEFAULT '',
    ultimo_error    TEXT NOT NULL DEFAULT '',
    acuerdos        INTEGER NOT NULL DEFAULT 0
);
"""


def ahora() -> str:
    return datetime.now(UTC).astimezone().isoformat(timespec="seconds")


def abrir(ruta: str | Path) -> sqlite3.Connection:
    """Abre (y crea si hace falta) la base del monitor, ya migrada."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(ruta)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode = WAL")
    con.execute("PRAGMA foreign_keys = ON")
    migrar(con)
    return con


def migrar(con: sqlite3.Connection) -> int:
    """Crea el esquema si falta. Solo añade; nunca altera ni borra nada."""
    version = con.execute("PRAGMA user_version").fetchone()[0]
    if version >= VERSION_ESQUEMA:
        return version
    with con:
        con.executescript(_ESQUEMA)
        con.execute(f"PRAGMA user_version = {VERSION_ESQUEMA}")
    registro.info("esquema del monitor creado o actualizado a la versión %d", VERSION_ESQUEMA)
    return VERSION_ESQUEMA


def huella(acuerdo: dict[str, Any]) -> str:
    """Huella estable del contenido: si cambia, es otro acuerdo."""
    crudo = json.dumps({c: str(acuerdo.get(c, "") or "").strip() for c in _CAMPOS_HUELLA},
                       sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(crudo.encode("utf-8")).hexdigest()


def guardar(con: sqlite3.Connection, acuerdo: dict[str, Any]) -> bool:
    """Guarda un acuerdo. Devuelve True si era nuevo, False si ya estaba.

    No registra partes ni síntesis en el log: son datos personales.
    """
    if not acuerdo.get("fuente") or not acuerdo.get("clave"):
        raise ValueError("Un acuerdo necesita al menos «fuente» y «clave»")

    fila = {
        "fuente": str(acuerdo["fuente"]),
        "clave": str(acuerdo["clave"]),
        "expediente": canonico(acuerdo.get("expediente") or acuerdo.get("expediente_crudo")),
        "expediente_crudo": str(acuerdo.get("expediente_crudo") or acuerdo.get("expediente") or ""),
        "juzgado": str(acuerdo.get("juzgado") or ""),
        "distrito": str(acuerdo.get("distrito") or ""),
        "materia": str(acuerdo.get("materia") or ""),
        "jurisdiccion": str(acuerdo.get("jurisdiccion") or ""),
        "partes": str(acuerdo.get("partes") or ""),
        "fecha_acuerdo": str(acuerdo.get("fecha_acuerdo") or ""),
        "fecha_publicacion": str(acuerdo.get("fecha_publicacion") or ""),
        "sintesis": str(acuerdo.get("sintesis") or ""),
        "texto": str(acuerdo.get("texto") or ""),
        "url_lista": str(acuerdo.get("url_lista") or ""),
        "url_documento": str(acuerdo.get("url_documento") or ""),
        "archivo": str(acuerdo.get("archivo") or ""),
        "creado": ahora(),
    }
    fila["huella"] = huella(fila)

    with con:
        cur = con.execute(
            """INSERT INTO acuerdos
                 (fuente, clave, expediente, expediente_crudo, juzgado, distrito, materia,
                  jurisdiccion, partes, fecha_acuerdo, fecha_publicacion, sintesis, texto,
                  url_lista, url_documento, archivo, huella, nuevo, creado)
               VALUES
                 (:fuente, :clave, :expediente, :expediente_crudo, :juzgado, :distrito, :materia,
                  :jurisdiccion, :partes, :fecha_acuerdo, :fecha_publicacion, :sintesis, :texto,
                  :url_lista, :url_documento, :archivo, :huella, 1, :creado)
               ON CONFLICT(fuente, clave) DO UPDATE SET
                  expediente = excluded.expediente,
                  expediente_crudo = excluded.expediente_crudo,
                  juzgado = excluded.juzgado,
                  distrito = excluded.distrito,
                  materia = excluded.materia,
                  jurisdiccion = excluded.jurisdiccion,
                  partes = excluded.partes,
                  fecha_acuerdo = excluded.fecha_acuerdo,
                  fecha_publicacion = excluded.fecha_publicacion,
                  sintesis = excluded.sintesis,
                  texto = excluded.texto,
                  url_documento = excluded.url_documento,
                  huella = excluded.huella,
                  nuevo = 1
               WHERE acuerdos.huella <> excluded.huella""",
            fila,
        )
        cambio = cur.rowcount > 0
        if cambio:
            con.execute("""INSERT INTO fuentes(nombre, acuerdos, ultima_revision)
                           VALUES(?, 1, ?)
                           ON CONFLICT(nombre) DO UPDATE SET
                             acuerdos = fuentes.acuerdos + 1,
                             ultima_revision = excluded.ultima_revision""",
                        (fila["fuente"], fila["creado"]))
    if cambio:
        registro.info("acuerdo guardado · fuente=%s expediente=%s", fila["fuente"], fila["expediente"] or "sin número")
    return cambio


_TOKEN = re.compile(r"[0-9A-Za-zÁÉÍÓÚÜÑáéíóúüñ/-]{2,}")


def consulta_fts(texto: str) -> str:
    """Convierte lo que escribe el usuario en una consulta FTS5 segura.

    FTS5 tiene sintaxis propia (comillas, NEAR, *, OR, paréntesis). Si se le
    pasa el texto tal cual, un carácter suelto puede romper la consulta o
    cambiar su sentido. Aquí cada palabra se vuelve una frase entrecomillada y
    se unen con AND: lo que escriba el usuario es siempre texto, nunca sintaxis.
    """
    limpio = unicodedata.normalize("NFC", str(texto or ""))
    palabras = [p.replace('"', "") for p in _TOKEN.findall(limpio)]
    # Un trozo sin letras ni dígitos («--», «//») no aporta y no tiene por qué
    # llegar al índice: se descarta.
    palabras = [p for p in palabras if any(c.isalnum() for c in p)]
    return " AND ".join(f'"{p}"' for p in palabras[:12])


def buscar(
    con: sqlite3.Connection,
    texto: str | None = None,
    expediente: str | None = None,
    juzgado: str | None = None,
    materia: str | None = None,
    jurisdiccion: str | None = None,
    parte: str | None = None,
    desde: str | None = None,
    hasta: str | None = None,
    solo_nuevos: bool = False,
    solo_vigilados: bool = False,
    limite: int = LIMITE_PREDETERMINADO,
) -> list[sqlite3.Row]:
    """Búsqueda con filtros combinables. Todo parametrizado."""
    where: list[str] = []
    datos: list[Any] = []

    if texto and str(texto).strip():
        consulta = consulta_fts(texto)
        if consulta:
            where.append("a.id IN (SELECT rowid FROM acuerdos_fts WHERE acuerdos_fts MATCH ?)")
            datos.append(consulta)
        else:
            # Se buscó algo que no deja ninguna palabra utilizable (por ejemplo
            # «*» o «--»). Eso es «sin resultados», nunca «todos los acuerdos».
            where.append("0 = 1")
    if expediente:
        canon = canonico(expediente)
        if canon:
            where.append("a.expediente = ?")
            datos.append(canon)
        else:
            where.append("a.expediente_crudo LIKE ?")
            datos.append(f"%{expediente}%")
    for campo, valor in (("juzgado", juzgado), ("materia", materia),
                         ("jurisdiccion", jurisdiccion), ("partes", parte)):
        if valor:
            where.append(f"a.{campo} LIKE ?")      # nombre de columna fijo, valor parametrizado
            datos.append(f"%{valor}%")
    if desde:
        where.append("a.fecha_acuerdo >= ?")
        datos.append(desde)
    if hasta:
        where.append("a.fecha_acuerdo <= ?")
        datos.append(hasta)
    if solo_nuevos:
        where.append("a.nuevo = 1")
    if solo_vigilados:
        where.append("a.expediente IN (SELECT expediente FROM vigilados WHERE activo = 1)")

    sql = "SELECT a.* FROM acuerdos a"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY a.fecha_acuerdo DESC, a.id DESC LIMIT ?"
    datos.append(max(1, min(int(limite), LIMITE_MAXIMO)))
    return con.execute(sql, datos).fetchall()


def marcar_vistos(con: sqlite3.Connection, ids: Iterable[int]) -> int:
    """Quita la marca de «nuevo». Se usa al exportar a la tablet."""
    lista = [int(i) for i in ids]
    if not lista:
        return 0
    with con:
        # Lo único que se concatena son los signos de interrogación, uno por
        # elemento; los valores van como parámetros y además ya pasaron por
        # int(), así que no puede colarse texto en la consulta.
        marcas = ",".join("?" * len(lista))
        cur = con.execute(
            f"UPDATE acuerdos SET nuevo = 0 WHERE id IN ({marcas})",  # noqa: S608
            lista,
        )
    return cur.rowcount


def vigilar(con: sqlite3.Connection, expediente: str, nota: str = "", activo: bool = True) -> str:
    """Agrega (o reactiva) un expediente en la lista de vigilancia."""
    canon = canonico(expediente)
    if not canon:
        raise ValueError(f"«{expediente}» no parece un número de expediente")
    with con:
        con.execute("""INSERT INTO vigilados(expediente, nota, activo, agregado)
                       VALUES(?, ?, ?, ?)
                       ON CONFLICT(expediente) DO UPDATE SET
                         nota = excluded.nota, activo = excluded.activo""",
                    (canon, str(nota or ""), 1 if activo else 0, ahora()))
    return canon


def vigilados(con: sqlite3.Connection, activos: bool = True) -> list[sqlite3.Row]:
    sql = "SELECT * FROM vigilados"
    if activos:
        sql += " WHERE activo = 1"
    return con.execute(sql + " ORDER BY expediente").fetchall()


def estado(con: sqlite3.Connection) -> dict[str, Any]:
    uno = lambda sql: con.execute(sql).fetchone()[0]  # noqa: E731
    return {
        "acuerdos": uno("SELECT COUNT(*) FROM acuerdos"),
        "nuevos": uno("SELECT COUNT(*) FROM acuerdos WHERE nuevo = 1"),
        "vigilados": uno("SELECT COUNT(*) FROM vigilados WHERE activo = 1"),
        "con_expediente": uno("SELECT COUNT(*) FROM acuerdos WHERE expediente <> ''"),
        "fuentes": [dict(f) for f in con.execute("SELECT * FROM fuentes ORDER BY nombre")],
    }
