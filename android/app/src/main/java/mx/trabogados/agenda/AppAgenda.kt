package mx.trabogados.agenda

import android.app.Application
import java.io.File

/**
 * Arranque de la aplicación. Solo hace limpieza: borra los archivos de
 * intercambio que quedaron de sesiones anteriores, para que no se queden
 * respaldos con datos del despacho dentro de la caché del teléfono.
 */
class AppAgenda : Application() {
    override fun onCreate() {
        super.onCreate()
        File(cacheDir, DIR_COMPARTIDOS).deleteRecursively()
        File(cacheDir, DIR_CAMARA).deleteRecursively()
    }

    companion object {
        const val DIR_COMPARTIDOS = "compartidos"
        const val DIR_CAMARA = "camara"
    }
}
