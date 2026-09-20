# SIGNALRESCUE physical mesh test

## 4-phone test

- Phone A: PRIMARY / victim
- Phone B: RELAY
- Phone C: RELAY
- Phone D: GATEWAY
- Laptop: Python gateway + GitHub Pages dashboard

1. Start `gateway/start_windows.bat` on the laptop.
2. Find the laptop LAN address printed by the script, for example `192.168.1.20`.
3. On every phone, set the gateway URL to `http://192.168.1.20:8765`.
4. Install/build the React Native app on all phones.
5. Give every phone a different role.
6. Enable Mesh Mode / keep the app foregrounded.
7. Verify the phone IDs appear in the dashboard.
8. Move one relay away from the others and watch its last-seen status.
9. Send a CRITICAL SOS from Phone A.
10. Verify hop-by-hop forwarding and gateway receipt.

## What is actually verified

The browser dashboard and Python gateway are runnable software. The radio mesh must be physically tested on real devices because this environment cannot access phone Bluetooth/Wi-Fi radios, Android/iOS signing, or device-specific OS behavior.
