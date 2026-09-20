# Android integration

The native adapter uses Google Play services Nearby Connections.

Add this dependency to the **app module** of your React Native Android project:

```gradle
dependencies {
    implementation("com.google.android.gms:play-services-nearby:19.5.0")
}
```

Register `MeshNativePackage()` in `MainApplication` and merge `AndroidManifest.additions.xml` into the app manifest.

Request the Nearby/Bluetooth permissions at runtime on supported Android versions. Keep the app in the foreground during the first physical test. Android/Google Play Services behavior and required permissions can vary by target SDK/device.
