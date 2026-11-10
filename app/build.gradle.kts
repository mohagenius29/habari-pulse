plugins { id("com.android.application"); id("org.jetbrains.kotlin.android") }
android {
    namespace = "com.mohart.habaripulse"
    compileSdk = 34
    defaultConfig {
        applicationId = "com.mohart.habaripulse"
        minSdk = 24; targetSdk = 34; versionCode = 1; versionName = "1.0"
        buildConfigField("String", "FEED_URL", "\"${project.findProperty("feedUrl") ?: "\"\"}\"")
    }
    buildFeatures { buildConfig = true }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
    kotlinOptions { jvmTarget = "17" }
}
dependencies { implementation("androidx.webkit:webkit:1.11.0") }
