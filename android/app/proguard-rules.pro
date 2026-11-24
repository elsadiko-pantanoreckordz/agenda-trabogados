# El puente JS->Android se invoca por reflexión desde la página: no se puede renombrar.
-keepclassmembers class mx.trabogados.agenda.PuenteAgenda {
    @android.webkit.JavascriptInterface <methods>;
}
