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
  dispositivo; no requiere root. Reversible: `adb uninstall mx.trabogados.agenda.debug`,
  que **borra también la base de datos** de la agenda. Respalda antes.
* **Plataforma:** cualquier sistema con `adb` (incluido en Android Studio).

### ⚠ Depuración y publicación son dos apps distintas

La variante `debug` se instala como `mx.trabogados.agenda.debug` y la `release` como
`mx.trabogados.agenda`. Para Android son **aplicaciones diferentes, con bases de datos
diferentes**: lo capturado en una no aparece en la otra. Para pasar los datos de una a
otra, exporta un «Respaldo completo» cifrado desde la primera e impórtalo en la segunda.

### Recordatorios: la agenda los guarda, pero no avisa

Los minutos de recordatorio de cada evento se almacenan, pero ni esta app ni la versión
web programan una notificación. Para avisos reales haría falta el permiso
`POST_NOTIFICATIONS`, alarmas del sistema (`AlarmManager`) y un receptor de arranque.

### Versión de publicación (release)

`assembleRelease` exige una llave de firma propia; sin ella el APK no se puede
instalar. Hay que crear un *keystore* y añadir `signingConfigs` a
`app/build.gradle.kts`. **El keystore y su contraseña nunca van al repositorio.**

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
