package mx.trabogados.agenda

import android.content.Context
import android.content.Intent
import android.webkit.JavascriptInterface
import androidx.core.content.FileProvider
import org.json.JSONObject
import java.io.File

/**
 * Puente entre la página de la agenda y Android, con un solo propósito:
 * guardar un archivo que la agenda ya generó (y que ella misma cifró) y
 * ofrecerlo para compartir. No lee ni devuelve datos de la agenda.
 */
class PuenteAgenda(private val ctx: Context) {

    /** Llamado desde JavaScript. Devuelve true si el archivo quedó listo para compartir. */
    @JavascriptInterface
    fun guardarArchivo(nombre: String?, contenido: String?): Boolean = exportar(nombre, contenido)

    /** Ruta usada por el canal moderno (WebMessageListener), con el mensaje en JSON. */
    fun mensaje(json: String): Boolean = try {
        val o = JSONObject(json)
        if (o.optString("accion") == "compartir")
            exportar(o.optString("nombre"), o.optString("contenido")) else false
    } catch (e: Exception) { false }

    private fun exportar(nombre: String?, contenido: String?): Boolean {
        val limpio = nombreSeguro(nombre) ?: return false
        val texto = contenido ?: return false
        // Tope de tamaño: evita que un error llene el almacenamiento del teléfono.
        if (texto.isEmpty() || texto.length > MAX_CARACTERES) return false

        val dir = File(ctx.cacheDir, AppAgenda.DIR_COMPARTIDOS)
        if (!dir.isDirectory && !dir.mkdirs()) return false
        val archivo = File(dir, limpio)
        // Comprobación final: el archivo tiene que quedar dentro de la carpeta de intercambio.
        if (archivo.canonicalFile.parentFile != dir.canonicalFile) return false

        return try {
            archivo.writeText(texto)
            val uri = FileProvider.getUriForFile(ctx, "${ctx.packageName}.archivos", archivo)
            val enviar = Intent(Intent.ACTION_SEND).apply {
                type = "application/json"
                putExtra(Intent.EXTRA_STREAM, uri)
                putExtra(Intent.EXTRA_SUBJECT, limpio)
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            }
            val selector = Intent.createChooser(enviar, ctx.getString(R.string.compartir)).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_GRANT_READ_URI_PERMISSION)
            }
            ctx.startActivity(selector)
            true
        } catch (e: Exception) { false }
    }

    /**
     * Lista blanca del nombre: solo letras, dígitos, punto, guion y guion bajo,
     * y terminando en .json. Así un nombre como "../../databases/x" no puede
     * escribir fuera de la carpeta de intercambio.
     */
    private fun nombreSeguro(n: String?): String? {
        val base = n?.substringAfterLast('/')?.substringAfterLast('\\')?.trim() ?: return null
        if (base.length !in 1..64 || !base.endsWith(".json")) return null
        if (base.startsWith(".") || base.contains("..")) return null
        if (!base.all { it.isLetterOrDigit() || it == '.' || it == '_' || it == '-' }) return null
        return base
    }

    companion object { const val MAX_CARACTERES = 25 * 1024 * 1024 }
}
