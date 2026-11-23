"""Cifrado compartido con la agenda (AES-256-GCM + PBKDF2-SHA256).

Es el mismo formato que usa la tablet, así que los archivos van y vienen
cifrados y autenticados: uno alterado o que no venga de tu agenda se rechaza.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ITERACIONES = 600_000
MIN_ITER, MAX_ITER = 100_000, 5_000_000


def _llave(clave: str, sal: bytes, iteraciones: int) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", clave.encode("utf-8"), sal, iteraciones, dklen=32)


def _aad(contenido: str) -> bytes:
    return f"agenda-rt|{contenido}|v1".encode("utf-8")


def cifrar(obj: Any, clave: str, contenido: str) -> dict:
    sal, iv = os.urandom(16), os.urandom(12)
    ct = AESGCM(_llave(clave, sal, ITERACIONES)).encrypt(
        iv, json.dumps(obj, ensure_ascii=False).encode("utf-8"), _aad(contenido)
    )
    return {
        "formato": "agenda-rt-cifrado", "version": 1, "contenido": contenido,
        "kdf": {"alg": "PBKDF2-SHA256", "iter": ITERACIONES, "sal": base64.b64encode(sal).decode()},
        "cifrado": "AES-256-GCM",
        "iv": base64.b64encode(iv).decode(),
        "datos": base64.b64encode(ct).decode(),
    }


def descifrar(sobre: dict, clave: str, contenido: str) -> Any:
    if sobre.get("formato") != "agenda-rt-cifrado" or sobre.get("version") != 1:
        raise ValueError("El archivo no tiene el formato de la agenda")
    if sobre.get("contenido") != contenido:
        raise ValueError(f"Se esperaba contenido «{contenido}» y el archivo trae «{sobre.get('contenido')}»")
    kdf = sobre.get("kdf") or {}
    it = kdf.get("iter")
    if kdf.get("alg") != "PBKDF2-SHA256" or not isinstance(it, int) or not (MIN_ITER <= it <= MAX_ITER):
        raise ValueError("Archivo cifrado dañado")
    llave = _llave(clave, base64.b64decode(kdf["sal"]), it)
    try:
        plano = AESGCM(llave).decrypt(
            base64.b64decode(sobre["iv"]), base64.b64decode(sobre["datos"]), _aad(contenido)
        )
    except Exception as e:  # noqa: BLE001
        raise ValueError("La clave no es correcta o el archivo fue alterado") from e
    return json.loads(plano.decode("utf-8"))
