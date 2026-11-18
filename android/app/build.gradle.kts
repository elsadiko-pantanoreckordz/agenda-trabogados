plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "mx.trabogados.agenda"
    compileSdk = 35

    defaultConfig {
        // Identificador propio: la app de Android es independiente de la agenda de la PC.
        applicationId = "mx.trabogados.agenda"
        minSdk = 24
        targetSdk = 35
        versionCode = 1
        versionName = "1.0"
        // Sin pruebas instrumentadas por ahora: nada que exponga la app.
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            // Nunca depurable en release: evita que se lea la base de datos por adb.
            isDebuggable = false
        }
        debug {
            applicationIdSuffix = ".debug"
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }

    packaging { resources.excludes += "/META-INF/{AL2.0,LGPL2.1}" }
}

dependencies {
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.activity:activity-ktx:1.9.3")
    // WebViewAssetLoader: sirve los archivos locales bajo un origen https real.
    implementation("androidx.webkit:webkit:1.12.1")
}
