plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

// ── Firma ──────────────────────────────────────────────
// Android se niega a actualizar una app si la nueva versión viene firmada con
// otra llave, y la salida habitual (desinstalar la vieja) BORRA la base de datos.
// Por eso todas las compilaciones, de prueba y de publicación, usan la misma
// llave. Si no hay llave configurada se cae en la de depuración de siempre, para
// que quien compile en su computadora no tenga que configurar nada.
val llaveRuta: String? = System.getenv("ANDROID_KEYSTORE")
val hayLlavePropia = !llaveRuta.isNullOrBlank() && file(llaveRuta).exists()

android {
    namespace = "mx.trabogados.agenda"
    compileSdk = 35

    defaultConfig {
        // Identificador propio: la app de Android es independiente de la agenda de la PC.
        applicationId = "mx.trabogados.agenda"
        minSdk = 24
        targetSdk = 35
        // La numera la compilación (en GitHub, el número de ejecución), para
        // poder saber qué versión tiene instalada la tablet.
        versionCode = (System.getenv("ANDROID_VERSION_CODE") ?: "1").toIntOrNull() ?: 1
        versionName = "1.0.${(System.getenv("ANDROID_VERSION_CODE") ?: "1")}"
        // Sin pruebas instrumentadas por ahora: nada que exponga la app.
    }

    signingConfigs {
        if (hayLlavePropia) {
            create("comun") {
                storeFile = file(llaveRuta!!)
                storePassword = System.getenv("ANDROID_KEYSTORE_PASS")
                keyAlias = System.getenv("ANDROID_KEY_ALIAS") ?: "agenda"
                keyPassword = System.getenv("ANDROID_KEY_PASS") ?: System.getenv("ANDROID_KEYSTORE_PASS")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            // Nunca depurable en release: evita que se lea la base de datos por adb.
            isDebuggable = false
            if (hayLlavePropia) signingConfig = signingConfigs.getByName("comun")
        }
        debug {
            // Sin sufijo a propósito: debug y release son la MISMA aplicación, con
            // la misma base de datos. Con sufijo serían dos apps distintas para
            // Android y pasar de una a otra parecería que se borraron los datos.
            isMinifyEnabled = false
            if (hayLlavePropia) signingConfig = signingConfigs.getByName("comun")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }

    // AGP 8 no genera BuildConfig por defecto; se usa para activar la depuración
    // remota del WebView solo en compilaciones debug.
    buildFeatures { buildConfig = true }

    packaging { resources.excludes += "/META-INF/{AL2.0,LGPL2.1}" }
}

dependencies {
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.activity:activity-ktx:1.9.3")
    // WebViewAssetLoader: sirve los archivos locales bajo un origen https real.
    implementation("androidx.webkit:webkit:1.12.1")
}
