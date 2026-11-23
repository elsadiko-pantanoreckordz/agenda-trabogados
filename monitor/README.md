# Monitor de Acuerdos

Busca y da seguimiento a acuerdos y boletines judiciales publicados por las
fuentes oficiales. **La computadora sale a la red; la tablet solo busca lo que
ya recibió**, en un archivo cifrado, igual que el asistente.

```
  FUENTES OFICIALES          COMPUTADORA                    TABLET
  Boletines del STJ   ──>  monitor/ (descarga,    ──cifrado──>  Pestaña «Acuerdos»
  Listas del PJF           parsea, indiza)                      (busca y aprueba)
```

## Por qué una base de datos aparte

El monitor guarda en `monitor/datos/acuerdos.db`, **no** en `agenda_rt.db`. Así
no puede alterar las tablas del despacho: ni `eventos`, ni `expedientes`, ni
`tribunales`. El empate con tus expedientes se hace por número normalizado al
exportar, no con llaves foráneas. Es la forma más segura de cumplir el requisito
de «migraciones que no alteren las existentes»: literalmente no las abre.

Las pruebas comprueban esto: verifican que la base del monitor no contenga
ninguna de las tablas de la agenda.

## Qué hay hecho (etapa a)

| Archivo | Qué hace |
|---|---|
| `expedientes.py` | Normaliza «123/2024», «00123/2024», «123/2024-II», «Exp. 123/24» a una forma canónica para empatar con la agenda |
| `almacen.py` | SQLite con búsqueda de texto completo (FTS5), huella por acuerdo, lista de vigilancia |
| `cli.py` | Búsqueda y vigilancia por línea de comandos |
| `ejemplos/` | Acuerdos de ejemplo para probar sin conectores |

| `exportar.py` | Arma el archivo cifrado de acuerdos que recibe la tablet |

| `analisis.py` | Lee el acuerdo y propone el evento: plazos, audiencias y clasificación |

**Falta** (etapas siguientes): los conectores reales, el OCR y la revisión diaria
automática.

## Qué hay hecho (etapa f): del acuerdo al evento

```sh
python3 monitor/cli.py proponer --ver
python3 monitor/cli.py proponer -s propuestas.json
```
- **Para qué sirve:** convierte los acuerdos en propuestas de evento, que apruebas en la tablet.
- **Opciones:** `--ver` → solo las muestra, no genera archivo ni pide clave; `-s ARCHIVO` → dónde escribirlas; `--vigilados` → solo expedientes en vigilancia; `--sin-plazo` → también propone revisar acuerdos que piden algo pero no señalan plazo; `--limite` → cuántos acuerdos revisar.
- **Efectos:** con `--ver` solo lee. Sin `--ver`, pide la clave de sincronización y escribe el archivo cifrado. No modifica la agenda ni la base del monitor. Reversible: borra el archivo.

**Sin modelo de lenguaje, a propósito.** Reconocer «tres días hábiles» o «las nueve
treinta horas del diez de diciembre» es reconocer patrones, y los patrones se
prueban uno por uno. Un modelo aquí añadiría costo, red y la posibilidad de
inventar, sin ganar nada. Las propuestas salen en el mismo formato que ya valida
la agenda, así que entran por el camino de siempre: tú apruebas o descartas.

### Tres reglas que el análisis no rompe

1. **Si el acuerdo no dice si los días son hábiles o naturales, no se adivina.**
   Se propone una tarea para revisar el plazo, nunca una fecha de vencimiento
   inventada. Hay una prueba que lo verifica.
2. **El fundamento solo se cita si aparece literalmente** en el acuerdo. Si no
   aparece, el campo va vacío.
3. **La fecha límite la calcula `plazos.py`** y viaja con el conteo día por día,
   incluido el aviso de que se contó desde la fecha del acuerdo: si la
   notificación surtió efectos otro día, lo corriges al aprobar.

## Qué hay hecho (etapa b)

La agenda tiene una pestaña **Acuerdos**: busca por palabras, expediente, juzgado,
materia, parte y fechas; marca expedientes como vigilados; avisa en «Mi día» de
los acuerdos sin revisar; y desde un acuerdo abre el formulario de evento ya
lleno, para que tú lo confirmes.

⚠ **La normalización de expedientes está escrita dos veces**, una en Python para
la computadora y otra en JavaScript para la tablet, porque son dos programas
distintos. Si las dos no coinciden, los acuerdos no empatarían con tus
expedientes. Por eso las dos leen la misma tabla de casos
(`pruebas/casos_expedientes.json`) y hay una prueba por lado: si alguien cambia
una y no la otra, las pruebas fallan.

```sh
python3 monitor/cli.py exportar
```
- **Para qué sirve:** genera el archivo cifrado con los acuerdos que la tablet todavía no tiene.
- **Opciones:** `-s ARCHIVO` → dónde escribirlo; `--todos` → manda también los ya enviados.
- **Efectos:** pide la clave de sincronización (o la toma de `AGENDA_CLAVE_SYNC`), escribe el archivo cifrado y marca esos acuerdos como enviados en la base del monitor. No toca la agenda. Reversible: vuelve a exportar con `--todos`.

## Comandos

Todos usan `monitor/datos/acuerdos.db`, o lo que indiques con `--base` o con la
variable `MONITOR_DB`. Ninguno toca la red todavía.

```sh
python3 monitor/cli.py estado
```
- **Para qué sirve:** resumen de la base: cuántos acuerdos hay, cuántos sin revisar, cuántos expedientes vigilados y qué fuentes han aportado.
- **Efectos:** solo lee. Crea la base vacía si todavía no existe. Reversible: borra el archivo.

```sh
python3 monitor/cli.py demo
```
- **Para qué sirve:** carga tres acuerdos de ejemplo para probar la búsqueda sin conectores.
- **Efectos:** escribe en la base del monitor. No toca la agenda. Reversible: borra el archivo de la base.

```sh
python3 monitor/cli.py buscar --texto "vista" --desde 2026-11-01 --nuevos
```
- **Para qué sirve:** busca entre los acuerdos almacenados.
- **Opciones:** `--texto` → palabras en síntesis, texto, partes y juzgado; `--expediente` → número en cualquier formato; `--juzgado`, `--materia`, `--jurisdiccion`, `--parte` → filtros por coincidencia; `--desde` / `--hasta` → rango de fechas (AAAA-MM-DD); `--nuevos` → solo los no revisados; `--vigilados` → solo expedientes en vigilancia; `--limite` → cuántos resultados (tope 500); `--json` → salida para otros programas.
- **Efectos:** solo lee.

```sh
python3 monitor/cli.py vigilar 452/2026 --nota "Juicio principal"
```
- **Para qué sirve:** marca un expediente para revisarlo a diario cuando existan los conectores.
- **Opciones:** `--nota` → recordatorio para ti; `--quitar` → deja de vigilarlo (no borra nada, solo lo pausa).
- **Efectos:** escribe un renglón en la tabla `vigilados` de la base del monitor. Reversible con `--quitar`.

```sh
python3 monitor/cli.py vigilados --todos
```
- **Para qué sirve:** lista los expedientes vigilados. `--todos` incluye los pausados.
- **Efectos:** solo lee.

## Seguridad aplicada en esta etapa

- **SQL parametrizado** en todas las consultas. Lo único que se concatena son
  signos de interrogación y nombres de columna fijos, nunca datos del usuario.
- **La sintaxis de FTS5 no se hereda del usuario.** FTS5 tiene operadores
  propios (`OR`, `NEAR`, `*`, comillas). Lo que escribes se convierte en frases
  entrecomilladas unidas con `AND`: es texto, nunca sintaxis. Hay pruebas con
  entradas hostiles.
- **Una búsqueda sin palabras utilizables devuelve nada**, no la base entera.
  (Este era un error real que las pruebas encontraron: buscar `*` devolvía todo.)
- **Los logs no llevan nombres.** Se registran la fuente y el número de
  expediente; las partes y la síntesis nunca.
- **Sin secretos en el código** y dependencias con versión fija en
  `requirements.txt`.

## Control de calidad

```sh
ruff check monitor/ pruebas/monitor_acuerdos.py
bandit -r monitor/
pip-audit -r monitor/requirements.txt
python3 pruebas/monitor_acuerdos.py
```
- **ruff** revisa estilo y errores; la configuración (`ruff.toml`) incluye las reglas `S`, que cubren parte de lo que revisa bandit.
- **bandit** busca patrones inseguros en el código.
- **pip-audit** busca vulnerabilidades conocidas en las dependencias.
- **Efectos:** las tres solo leen. `pip-audit` sí consulta internet para comparar versiones.
- ⚠ En el contenedor donde escribí esto, `bandit` y `pip-audit` **no se pudieron instalar** (no alcanza pypi). Hay que correrlas en tu computadora: `pip install bandit pip-audit`.

## Límites legales que respeta el diseño

- Solo información pública.
- Se respeta `robots.txt` y se limita el ritmo de peticiones (etapa d).
- **No se evaden CAPTCHAs ni bloqueos.** Si aparece uno, el conector se detiene
  y avisa para que tú lo resuelvas a mano.
- Los nombres de las partes son datos personales: se quedan entre tu
  computadora y tu tablet, cifrados. No se suben a ningún servicio externo.
