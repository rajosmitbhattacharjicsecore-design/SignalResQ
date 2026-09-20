# iOS integration

Merge these keys into the iOS app `Info.plist` for the local peer-discovery test:

```xml
<key>NSLocalNetworkUsageDescription</key>
<string>SIGNALRESCUE uses the local network to discover nearby emergency mesh peers.</string>
<key>NSBonjourServices</key>
<array>
    <string>_signalrescue._tcp</string>
</array>
```

Add `MeshNative.swift` and `MeshNative.m` to the Xcode target and link the **Network** framework.

Keep the app in the foreground for the first physical test. iOS background execution and peer discovery are OS-controlled.
