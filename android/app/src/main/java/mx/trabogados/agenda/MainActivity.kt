package mx.trabogados.agenda

import android.app.AlertDialog
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.ViewGroup
import android.webkit.JsPromptResult
import android.webkit.JsResult
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.EditText
import androidx.activity.ComponentActivity
import androidx.activity.OnBackPressedCallback
import androidx.activity.result.contract.ActivityResultContracts
import androidx.webkit.JavaScriptReplyProxy
import androidx.webkit.WebMessageCompat
import androidx.webkit.WebViewAssetLoader
import androidx.webkit.WebViewCompat
import androidx.webkit.WebViewFeature

/**
 * Agenda RT · Android.
 *
 * La interfaz de la agenda vive en app/src/main/assets/web y se sirve por
 * WebViewAssetLoader bajo https://appassets.androidplatform.net/.
 * Dos razones para no usar file:// :
 *   1. file:// no es "contexto seguro", y sin él el navegador no presta
 *      crypto.subtle: se perdería el cifrado AES-256-GCM de los respaldos.
 *   2. El origen https es estable, así la base de datos (IndexedDB) de la app
 *      no se pierde y queda en el almacenamiento privado de la aplicación,
 *      separada de la agenda de la computadora.
 */
class MainActivity : ComponentActivity() {

    private lateinit var web: WebView
    private var selectorArchivo: ValueCallback<Array<Uri>>? = null

    private val abrirArchivo = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { res ->
        val cb = selectorArchivo
        selectorArchivo = null
        val uri = if (res.resultCode == RESULT_OK) res.data?.data else null
        cb?.onReceiveValue(if (uri != null) arrayOf(uri) else emptyArray())
    }

    override fun onCreate(estado: Bundle?) {
        super.onCreate(estado)

        val cargador = WebViewAssetLoader.Builder()
            .addPathHandler("/", WebViewAssetLoader.AssetsPathHandler(this))
            .build()

        web = WebView(this)
        web.layoutParams = ViewGroup.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT
        )
        setContentView(web)

        web.settings.apply {
            javaScriptEnabled = true          // la agenda es una aplicación JS
            domStorageEnabled = true          // localStorage/IndexedDB de la app
            // Todo lo demás, cerrado:
            allowFileAccess = false           // nada de leer /sdcard ni el disco
            allowContentAccess = false        // nada de content:// desde la página
            @Suppress("DEPRECATION")
            allowFileAccessFromFileURLs = false
            @Suppress("DEPRECATION")
            allowUniversalAccessFromFileURLs = false
            javaScriptCanOpenWindowsAutomatically = false
            setSupportMultipleWindows(false)
            mediaPlaybackRequiresUserGesture = true
            setGeolocationEnabled(false)
            mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
            cacheMode = WebSettings.LOAD_DEFAULT
            setSupportZoom(false)
            builtInZoomControls = false
        }
        // Depuración remota jamás en la app instalada (solo en compilaciones debug).
        WebView.setWebContentsDebuggingEnabled(BuildConfig.DEBUG)

        web.webViewClient = object : WebViewClient() {
            override fun shouldInterceptRequest(v: WebView, p: WebResourceRequest): WebResourceResponse? =
                cargador.shouldInterceptRequest(p.url)

            /** Solo se navega dentro de la app; cualquier enlace externo se abre en el navegador. */
            override fun shouldOverrideUrlLoading(v: WebView, p: WebResourceRequest): Boolean {
                val u = p.url
                if (u.host == HOST_APP) return false
                if (u.scheme == "https" || u.scheme == "http") {
                    try { startActivity(Intent(Intent.ACTION_VIEW, u)) } catch (e: Exception) { }
                }
                return true
            }
        }

        web.webChromeClient = object : WebChromeClient() {
            // El WebView no muestra alert/confirm/prompt por su cuenta: la agenda
            // los usa para confirmar acciones, así que se dibujan aquí.
            override fun onJsAlert(v: WebView?, url: String?, msj: String?, r: JsResult): Boolean {
                AlertDialog.Builder(this@MainActivity).setMessage(msj)
                    .setPositiveButton("Aceptar") { _, _ -> r.confirm() }
                    .setOnCancelListener { r.cancel() }.show()
                return true
            }

            override fun onJsConfirm(v: WebView?, url: String?, msj: String?, r: JsResult): Boolean {
                AlertDialog.Builder(this@MainActivity).setMessage(msj)
                    .setPositiveButton("Sí") { _, _ -> r.confirm() }
                    .setNegativeButton("No") { _, _ -> r.cancel() }
                    .setOnCancelListener { r.cancel() }.show()
                return true
            }

            override fun onJsPrompt(v: WebView?, url: String?, msj: String?, pre: String?, r: JsPromptResult): Boolean {
                val campo = EditText(this@MainActivity).apply { setText(pre ?: "") }
                AlertDialog.Builder(this@MainActivity).setMessage(msj).setView(campo)
                    .setPositiveButton("Aceptar") { _, _ -> r.confirm(campo.text.toString()) }
                    .setNegativeButton("Cancelar") { _, _ -> r.cancel() }
                    .setOnCancelListener { r.cancel() }.show()
                return true
            }

            /** Para «Recibir datos»: abre el selector de archivos del sistema. */
            override fun onShowFileChooser(
                v: WebView?, cb: ValueCallback<Array<Uri>>?, params: FileChooserParams?
            ): Boolean {
                selectorArchivo?.onReceiveValue(null)
                selectorArchivo = cb
                val i = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
                    addCategory(Intent.CATEGORY_OPENABLE)
                    type = "*/*"
                    putExtra(Intent.EXTRA_MIME_TYPES, arrayOf("application/json", "text/plain"))
                }
                return try { abrirArchivo.launch(i); true } catch (e: Exception) {
                    selectorArchivo = null; cb?.onReceiveValue(null); false
                }
            }
        }

        val puente = PuenteAgenda(this)
        if (WebViewFeature.isFeatureSupported(WebViewFeature.WEB_MESSAGE_LISTENER)) {
            // Canal moderno: solo la página de la propia app puede hablar por él.
            WebViewCompat.addWebMessageListener(
                web, "puenteAgenda", setOf(ORIGEN_APP)
            ) { _: WebView, msj: WebMessageCompat, _: Uri, _: Boolean, _: JavaScriptReplyProxy ->
                msj.data?.let { puente.mensaje(it) }
            }
        } else {
            // Respaldo en sistemas viejos. Aceptable aquí porque la navegación está
            // limitada al origen de la app y la app no tiene permiso de internet.
            web.addJavascriptInterface(puente, "PuenteAgendaLegado")
        }

        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (web.canGoBack()) web.goBack() else finish()
            }
        })

        if (estado == null) web.loadUrl("$ORIGEN_APP/index.html") else web.restoreState(estado)
    }

    override fun onSaveInstanceState(estado: Bundle) {
        super.onSaveInstanceState(estado)
        web.saveState(estado)
    }

    companion object {
        const val HOST_APP = "appassets.androidplatform.net"
        const val ORIGEN_APP = "https://$HOST_APP"
    }
}
