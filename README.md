# Agenda RT

Agenda Jurídica de TR Abogados. Funciona sin internet; los datos se guardan solo en el
dispositivo. Aquí solo está el código: ningún expediente ni dato del despacho se sube
a este sitio.

Hay dos versiones **independientes entre sí**, cada una con su propia base de datos:

| Versión | Dónde vive | Base de datos |
|---|---|---|
| **Web / tablet (PWA)** | `index.html`, se publica en `docs/` | IndexedDB `agenda_rt` del navegador |
| **Android (APK)** | carpeta [`android/`](android/README.md) | IndexedDB `agenda_rt_android`, privada de la app |

Instalar la versión web: abre
https://elsadiko-pantanoreckordz.github.io/agenda-trabogados/ en Chrome → menú ⋮ →
«Instalar app».

Compilar la versión de Android: ver [`android/README.md`](android/README.md). Pasar
datos de una a otra es **opcional** y se hace con un archivo cifrado (AES-256-GCM);
ninguna de las dos depende de la otra para funcionar.
