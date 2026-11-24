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

## Avisos de riesgo

«Mi día» avisa de audiencias que se enciman, compromisos con menos de 30 minutos
entre ellos, diligencias en distritos judiciales distintos el mismo día,
vencimientos a tres días sin promoción capturada y expedientes sin movimiento en
60 días. Se calcula en el dispositivo: no manda nada a ninguna parte.

## Asistente (opcional)

El asistente vive en la computadora y la agenda funciona igual sin él. En la
tablet dejas pendientes (una nota o la foto de un acuerdo), los pasas en un
archivo cifrado, la computadora los interpreta con Claude y devuelve propuestas
que tú apruebas o descartas. El modelo lee el lenguaje; **los días del plazo los
cuenta la computadora** y el conteo viene a la vista. Ver
[`agente/README.md`](agente/README.md).

## Seguridad

[`SEGURIDAD.md`](SEGURIDAD.md): lo que hay que configurar en la tablet, qué
protege ya la app y qué decisiones son del abogado y no del programa.

## Pruebas

```sh
sh pruebas/correr.sh
```

Cinco pruebas que no gastan en la API (la respuesta del modelo se simula):
los avisos de riesgo, el conteo de plazos, el cifrado entre tablet y
computadora en ambos sentidos, el circuito completo del asistente y la
validación de las propuestas al llegar a la agenda.
