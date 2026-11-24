# Asistente de la Agenda RT · Modo A

El asistente vive **en la computadora**. La tablet nunca habla con internet: le
dejas pendientes en una charola, los pasas en un archivo cifrado, la computadora
los trabaja y te devuelve propuestas que tú apruebas o descartas.

```
  TABLET                        COMPUTADORA                    TABLET
  Charola de      ──cifrado──>  agente_pc.py    ──cifrado──>   Propuestas
  pendientes                    (lee y cuenta)                 (tú apruebas)
```

## Reparto de trabajo, a propósito

| Quién | Qué hace | Por qué |
|---|---|---|
| **Claude** | Lee el lenguaje: qué pide la nota o el acuerdo fotografiado | Es lo que un modelo hace bien |
| **Python** (`plazos.py`) | Cuenta los días del plazo | Contar es aritmética, y la aritmética no se le delega a un modelo |
| **La tablet** | Valida campo por campo y espera tu aprobación | Nada entra a la agenda sin que lo veas |

El modelo tiene prohibido contar días y citar artículos que no aparezcan en el
documento. Si un dato falta, debe dejarlo vacío y decir qué falta.

## Instalación, una sola vez

```sh
pip install -r requirements.txt
```
- **Plataforma:** Windows (PowerShell o cmd), macOS o Linux, con Python 3.10 o más.
- **Para qué sirve:** instala las dos bibliotecas que usa el asistente.
- **Opciones:** `-r requirements.txt` → lee la lista de bibliotecas del archivo en vez de nombrarlas a mano. Son `anthropic` (hablar con Claude) y `cryptography` (abrir y cerrar los archivos cifrados).
- **Efectos:** instala en tu Python; no toca la agenda ni el registro. Reversible con `pip uninstall anthropic cryptography`. No requiere administrador si usas un entorno virtual.

Luego la llave de acceso a Claude, que **vive solo en esta computadora**:

```sh
setx ANTHROPIC_API_KEY "sk-ant-..."      # Windows, permanente
export ANTHROPIC_API_KEY="sk-ant-..."    # macOS o Linux, en esta sesión
```
- **Para qué sirve:** guarda la llave donde el asistente la encuentre.
- **Opciones:** `setx` la deja guardada para las siguientes sesiones de Windows; `export` solo para la ventana actual (para dejarla fija en macOS o Linux va en `~/.bashrc` o `~/.zshrc`).
- ⚠ **Efectos:** la llave queda legible por tu usuario de Windows. Quien la tenga puede gastar a tu cuenta. **Nunca** la pongas en la tablet, en el repositorio ni en un correo. Para revocarla, bórrala en la consola de Anthropic.

## Cada vez que trabajes

**1. En la tablet:** deja pendientes en el Asistente (botón +) y luego
«⟳ Compartir datos → ⚙ Enviar pendientes al asistente». Guarda el archivo
`pendientes_….json` donde la computadora lo vea (OneDrive, por ejemplo).

**2. En la computadora:**

```sh
python3 agente_pc.py pendientes_202611231040.json
```
- **Plataforma:** cualquiera (en Windows a veces es `python` en lugar de `python3`).
- **Para qué sirve:** abre la charola, le pide a Claude que interprete cada pendiente, cuenta los plazos y escribe el archivo de propuestas.
- **Opciones:**
  - `-s ARCHIVO` → dónde escribir las propuestas (por defecto, junto al de pendientes).
  - `-m MODELO` → qué modelo usar (por defecto `claude-opus-5-5`).
  - `-e NIVEL` → esfuerzo del modelo: `low`, `medium`, `high` (el que usa), `xhigh` o `max`. Más esfuerzo cuesta más y razona más.
  - `-n NÚMERO` → tope de pendientes por corrida (20 por defecto), para que un error no se convierta en una cuenta grande.
- **Efectos:** pide la clave de sincronización en pantalla (no se ve lo que escribes) o la toma de `AGENDA_CLAVE_SYNC`. Escribe dos archivos: las propuestas cifradas y un renglón por pendiente en `bitacora.jsonl`. Envía a Anthropic el texto que escribiste y la foto, si la hay; **no** manda tu base de expedientes. No modifica la agenda de nadie.

**3. De vuelta en la tablet:** «⟳ Compartir datos → ⬇ Recibir datos», eliges el
archivo `propuestas_….json`, y las propuestas aparecen en la sección Asistente
con su conteo día por día. Ahí apruebas o descartas.

## Días inhábiles

`dias_inhabiles.json` es tuyo y hay que mantenerlo: los acuerdos de suspensión de
labores y los periodos vacacionales de los tribunales que te importan.

⚠ El conteo descuenta sábados, domingos y lo que esté en ese archivo. **Si falta
un día inhábil, el plazo saldrá más corto de lo real.** Por eso cada propuesta
trae el conteo día por día a la vista: para que lo revises antes de aprobar.

## Bitácora

`bitacora.jsonl` guarda, por cada pendiente enviado: cuándo, de qué expediente,
si llevaba foto, cuántos caracteres, una huella del texto, el modelo y los
tokens. **Guarda la huella, no el contenido**, para poder demostrar qué salió sin
duplicar los datos del despacho en otro archivo.

## Lo que el asistente nunca hace

- Escribir en tu agenda por su cuenta. Solo propone.
- Contar días. Eso lo hace `plazos.py` y lo muestra completo.
- Citar un artículo que no esté en el documento.
- Borrar algo. No tiene con qué.
- Obedecer instrucciones que vengan dentro de un acuerdo escaneado o de una nota:
  ese contenido se le entrega marcado como datos, y si trae órdenes debe
  reportarlas, no cumplirlas.

## Probar sin gastar

```sh
sh ../pruebas/correr.sh
```
- **Para qué sirve:** corre las cinco pruebas del proyecto simulando la respuesta del modelo: no consume API ni necesita llave.
- **Efectos:** solo lee el proyecto y escribe en una carpeta temporal que se borra al terminar.
