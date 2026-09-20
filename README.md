# SIGNALRESCUE Mobile Mesh Starter

This repository turns the centralized browser proof-of-concept into a mobile mesh transport/application starter.

## Choice
React Native was selected to share the packet/router/UI layer. Native transport adapters are used because radio discovery is platform-specific.

## Current status
The repository contains the protocol core, router/store-forward logic, Android Nearby Connections adapter skeleton, iOS Network-framework peer adapter skeleton, gateway bridge contract, and virtual-node test harness. It is **not physically verified in this environment** because this environment cannot access Android/iOS radios or sign/build mobile apps.

## Build direction
Create a standard React Native 0.81 project and copy `src/`, the native module files, and permissions into it. Register `MeshNativePackage` in `MainApplication`, add the Google Play Services Nearby dependency, and add the Swift files to the iOS target. Then test on physical phones.

## Important iOS update
The requested MultipeerConnectivity framework is now deprecated in current Apple documentation; Apple recommends the Network framework. Therefore this starter uses Network framework for new iOS code. See Apple TN3213.
