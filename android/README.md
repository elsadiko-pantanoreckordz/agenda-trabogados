# Agenda RT · Android

Proyecto de Android **independiente** de la agenda de la computadora. La app lleva
su propia copia de la agenda dentro del APK y **su propia base de datos**: nada se
comparte con la PC a menos que tú exportes un archivo cifrado a mano.

## Cómo está armada

| Pieza | Para qué sirve |
|---|---|
| `app/src/main/assets/web/` | Copia de la agenda (interfaz y datos semilla) que viaja dentro del APK. |
| `MainActivity.kt` | Abre esa copia en un WebView servido por `WebViewAssetLoader`. |
| `PuenteAgenda.kt` | Único puente con Android: guardar y compartir el archivo cifrado. |
| `sync-web.sh` + `parche-android.py` | Regeneran los assets desde `../index.html` cuando cambia la agenda. |

### Base de datos propia

* La interfaz se sirve desde `https://appassets.androidplatform.net/`, **no** desde
  `file://`. Dos motivos:
  1. `file://` no es *contexto seguro*: sin él el navegador no presta `crypto.subtle`
     y se perdería el cifrado AES-256-GCM de los respaldos.
  2. Con un origen `https` estable, el almacenamiento (IndexedDB) no se pierde.
* La base se llama `agenda_rt_android` (la de la PC/tablet es `agenda_rt`), y vive en
  el almacenamiento privado de la app: `/data/data/mx.trabogados.agenda/app_webview/`.
  Ninguna otra app, ni la PWA del navegador, puede leerla.
* Al desinstalar la app se borra esa base. **Haz respaldos cifrados** (⟳ Compartir
  datos → «Respaldo completo»).

### Decisiones de seguridad

* **Sin permiso `INTERNET`** en el manifiesto: la app no puede enviar tus expedientes
  a ningún servidor, ni por error ni por código inyectado.
* `allowBackup="false"` y reglas de extracción que excluyen todo: la agenda no se
  sube a la nube de Google ni se copia al cambiar de teléfono.
* WebView cerrado: sin acceso a archivos (`allowFileAccess=false`), sin
  `content://`, sin ventanas nuevas, sin geolocalización, sin contenido mixto.
* La navegación está limitada al origen de la app; cualquier enlace externo (p. ej.
  el SJF) se abre en el navegador del sistema, fuera de la app.
* El puente JS usa `WebMessageListener` restringido al origen de la app; solo acepta
  la acción «compartir», valida el nombre con lista blanca y limita el tamaño.
* La depuración remota del WebView solo se activa en compilaciones `debug`.

## Compilar

### Opción A — GitHub Actions (sin instalar nada)

Al subir cambios de `android/**` se ejecuta `.github/workflows/android.yml` y el APK
queda como *artifact* («agenda-rt-android-debug»). También se puede lanzar a mano
desde la pestaña **Actions** → *Run workflow*.

### Opción B — en tu computadora

Requisitos: Android Studio (o el SDK de Android) y JDK 17.

```sh
cd android
./gradlew assembleDebug
```

* **Para qué sirve:** compila la app y produce un APK instalable.
* **Opciones:** `assembleDebug` → variante de depuración, se firma con la llave de
  prueba del SDK y se instala sin configurar nada.
* **Objetivo:** obtener `app/build/outputs/apk/debug/app-debug.apk`.
* **Efectos:** solo escribe en `android/app/build/`. No requiere root ni toca el
  sistema. Reversible: borra esa carpeta (`./gradlew clean`).
* **Plataforma:** Linux/macOS (shell). En Windows PowerShell: `.\gradlew.bat assembleDebug`.

Instalar en el teléfono o tablet con el cable:

```sh
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

* **Para qué sirve:** instala el APK en el dispositivo conectado.
* **Opciones:** `-r` → reinstala sobre una versión anterior **conservando los datos**;
  sin `-r`, una instalación previa hace fallar el comando.
* **Objetivo:** probar la app sin pasar por la tienda.
* **Efectos:** instala/actualiza la app. Requiere «Depuración USB» activada en el
  dispositivo; no requiere root. Reversible: `adb uninstall mx.trabogados.agenda`,
  que **borra también la base de datos** de la agenda. Respalda antes.
* **Plataforma:** cualquier sistema con `adb` (incluido en Android Studio).

## ⚠ La firma: por qué sin ella se pierden los datos

Android **se niega a actualizar** una app si la nueva versión viene firmada con
otra llave («No se pudo instalar la aplicación»). La salida habitual —desinstalar
la vieja— **borra la base de datos**.

Durante un tiempo este proyecto no fijaba ninguna llave, así que cada compilación
en GitHub usaba la llave de depuración que generaba esa máquina: **cada APK iba
firmado distinto y ninguno se podía instalar encima del anterior.** Ya está
corregido: `debug` y `release` son la misma aplicación (mismo identificador, misma
base de datos) y ambas usan la misma llave.

### Crear la llave, una sola vez

```sh
keytool -genkeypair -v -keystore agenda.jks -alias agenda \
        -keyalg RSA -keysize 4096 -validity 10000
```
* **Plataforma:** cualquier sistema con Java (viene con Android Studio).
* **Para qué sirve:** crea el archivo de llave con el que se firmarán todas las versiones.
* **Opciones:** `-keystore` → archivo a crear; `-alias` → nombre interno de la llave; `-keyalg RSA -keysize 4096` → tipo y fuerza de la llave; `-validity 10000` → días de vigencia (unos 27 años, para no quedarse sin poder actualizar).
* **Efectos:** pide una contraseña y algunos datos. Crea `agenda.jks` en la carpeta actual.
* ⚠ **Guárdalo como guardas una escritura.** Si pierdes ese archivo o su
  contraseña, **ya no podrás publicar actualizaciones** sobre las instalaciones
  existentes: la única salida sería desinstalar, perdiendo los datos.
* ⚠ **Nunca lo subas al repositorio.**

### Darle la llave a GitHub

```sh
base64 -w0 agenda.jks > agenda.jks.b64
```
* **Para qué sirve:** convierte la llave a texto para poder pegarla como secreto.
* **Opciones:** `-w0` → sin saltos de línea (en macOS es `base64 -i agenda.jks | tr -d '\n'`).
* **Efectos:** crea un archivo de texto con el contenido de la llave. **Bórralo en
  cuanto lo pegues**: vale lo mismo que la llave.

En GitHub: **Settings → Secrets and variables → Actions → New repository secret**,
y crea cuatro:

| Secreto | Qué contiene |
|---|---|
| `ANDROID_KEYSTORE_B64` | el contenido de `agenda.jks.b64` |
| `ANDROID_KEYSTORE_PASS` | la contraseña del keystore |
| `ANDROID_KEY_ALIAS` | `agenda` |
| `ANDROID_KEY_PASS` | la contraseña de la llave (suele ser la misma) |

El workflow escribe la llave en un archivo temporal, compila y **la borra siempre**,
aunque la compilación falle. Si los secretos no están puestos, compila igual pero
deja una advertencia: ese APK no se podrá instalar encima de otro.

### ⚠ El cambio de llave cuesta una desinstalación, una sola vez

El primer APK firmado con la llave nueva tiene, por fuerza, una firma distinta a
la de los APK anteriores. **Esa instalación exige desinstalar lo que haya, y eso
borra los datos.** Exporta un respaldo completo antes. A partir de ahí, todas las
actualizaciones se instalan encima sin perder nada.

### Qué versión tengo instalada

La app lo dice en «⟳ Compartir datos», al final del panel, junto con la fecha del
último respaldo y si el sistema prometió no borrar los datos. El número coincide
con el de la ejecución de GitHub que generó ese APK.

### Recordatorios: la agenda los guarda, pero no avisa

Los minutos de recordatorio de cada evento se almacenan, pero ni esta app ni la versión
web programan una notificación. Para avisos reales haría falta el permiso
`POST_NOTIFICATIONS`, alarmas del sistema (`AlarmManager`) y un receptor de arranque.

### Versión de publicación (release)

`./gradlew assembleRelease` usa la misma llave que las compilaciones de prueba,
leyendo `ANDROID_KEYSTORE`, `ANDROID_KEYSTORE_PASS`, `ANDROID_KEY_ALIAS` y
`ANDROID_KEY_PASS` del entorno. Sin esas variables cae en la llave de depuración
local, cómoda para probar pero **no apta para instalar encima de otra versión**.

## Cuando cambie la agenda de la PC

```sh
cd android && sh sync-web.sh
```

* **Para qué sirve:** vuelve a copiar `../index.html`, `../icono.png` y
  `../tribunales.json` a los assets y aplica los cambios de la versión Android.
* **Objetivo:** mantener una sola fuente de la interfaz.
* **Efectos:** solo sobrescribe `android/app/src/main/assets/web/`. Si la agenda de
  la PC cambió tanto que un fragmento ya no coincide, el script **falla y avisa** en
  lugar de generar una app a medias.
* **Plataforma:** Linux/macOS/WSL con `python3`.
