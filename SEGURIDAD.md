# Seguridad de la Agenda RT

Guía práctica para el despacho. Está en orden de importancia real, no de
sofisticación: lo primero es lo que más probablemente te va a pasar.

## 1. Lo más importante: la tablet

Todos tus expedientes están dentro del aparato. El incidente probable no es que
alguien intercepte una consulta: es que la tablet se quede en un juzgado, en un
taxi o en una sala de espera.

- [ ] **Bloqueo de pantalla con PIN, patrón o huella.** No es un trámite: Android
      cifra el almacenamiento usando eso. **Sin bloqueo de pantalla, el cifrado no
      protege nada** y cualquiera que la encienda lee tus expedientes.
- [ ] **Bloqueo automático en 1 o 2 minutos**, no en 30.
- [ ] **PIN de al menos 6 dígitos**, y que no sea una fecha que venga en tus
      propios expedientes.
- [ ] **Apaga «instalar apps desconocidas»** después de instalar la agenda. Es un
      interruptor por aplicación y se vuelve a pedir cuando lo necesites.
- [ ] **No instales nada más de fuera de la tienda** en esa tablet.
- [ ] **Respaldos cifrados** («⟳ Compartir datos → Respaldo completo») guardados
      fuera del aparato. Si se pierde, no pierdes el trabajo; y si alguien se topa
      con el respaldo, no puede abrirlo.

## 2. La clave de sincronización

Es la que protege todos los archivos que van y vienen: respaldos, pendientes y
propuestas.

- [ ] **Al menos 12 caracteres**, mejor una frase que recuerdes.
- [ ] **No la uses para nada más**, y menos para el correo o el banco.
- [ ] **No viaja con el archivo.** Si mandas un respaldo por OneDrive, la clave va
      por otro camino, o mejor, no va: ya la sabes.
- [ ] ⚠ **Si la pierdes, los respaldos no se pueden abrir.** No hay puerta de
      atrás, ni para mí. Anótala donde guardas lo importante.

## 3. La llave de Claude, si usas el asistente

- [ ] **Vive solo en la computadora**, en una variable de entorno.
- [ ] **Nunca en la tablet, ni en el repositorio, ni en un correo.** Un APK es un
      archivo comprimido: una llave metida ahí se extrae en un minuto.
- [ ] **Ponle tope de gasto** en la consola de Anthropic.
- [ ] **Revísala si cambias de computadora** o si despides a alguien que tuvo
      acceso al equipo: se revoca y se genera otra.

## 4. Lo que ya está resuelto en la app, y que no hay que deshacer

Esto viene así de fábrica. Lo anoto para que nadie lo "arregle" después:

| Protección | Qué evita |
|---|---|
| **Sin permiso de internet** en el manifiesto | La app es incapaz de enviar expedientes a ningún servidor, ni por error ni por código inyectado |
| `allowBackup="false"` y reglas de extracción vacías | La agenda no sube a la nube de Google ni se copia al cambiar de teléfono |
| Interfaz servida por `https://appassets.androidplatform.net` y no por `file://` | Conserva el cifrado AES-256-GCM de los respaldos, que `file://` deshabilita, y mantiene estable la base de datos |
| WebView sin acceso a archivos ni a `content://` | Que la página pueda leer el resto del teléfono |
| Navegación limitada al origen de la app | Que un enlace saque la agenda a una página externa dentro de la app |
| Puente con Android restringido por origen, solo acción «compartir» | Que algo distinto de tu agenda use el puente |
| Depuración remota solo en compilaciones de prueba | Que se lea la base de datos por cable |
| Sin permiso de cámara: la foto la toma la app de cámara del sistema | Que la agenda pueda ver por la cámara |

## 5. Decisiones que son tuyas, no técnicas

- **¿Datos de tus asuntos salen hacia un servicio externo?** Usar el asistente
  implica que el texto que escribes y las fotos que tomas se envían a Anthropic
  para interpretarlos. Eso toca secreto profesional y lo decides tú. La
  alternativa honesta: los avisos de riesgo de «Mi día» no mandan nada a ninguna
  parte y ya cubren buena parte del valor.
- **Qué sale:** solo lo que escribes en la charola y las fotos que agregas. La
  base de expedientes **no** se envía. Queda registrado en `agente/bitacora.jsonl`.
- **Si alguien te pregunta qué datos salieron**, esa bitácora es la respuesta.

## 6. Qué hacer si pierdes la tablet

1. Cambia la clave de sincronización (afecta a los archivos nuevos, no a los ya
   generados).
2. Si el aparato tenía bloqueo de pantalla y PIN decente, los expedientes están
   cifrados en reposo: el riesgo es bajo, no nulo.
3. Instala la agenda en el aparato nuevo y restaura tu último respaldo cifrado.
4. Revisa qué respaldos andaban en OneDrive y si siguen siendo necesarios.
5. ⚠ No existe borrado remoto desde la agenda. Si lo necesitas, se hace con el
   administrador de dispositivos de tu cuenta de Google.
