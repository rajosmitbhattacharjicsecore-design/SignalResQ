# Implementation / Verification Notes

## Milestones
1. **2-device:** Android Nearby cluster discovery + accepted connection + signed bytes; iOS Network peer discovery + reliable message.
2. **3+ devices:** each node rebroadcasts packet with dedup/TTL. Verify A→B→C when A cannot directly reach C.
3. **Store-forward:** disconnect B, send packet, verify queue persistence, reconnect B, verify automatic flush.
4. **Gateway bridge:** phone uses HTTP `/api/send` and `/api/inbox` when LAN gateway is available; dashboard receives the same packet schema.
5. **Battery/signing:** add OS battery API, duty-cycle policy, Ed25519 signing/verification.

## Physical test plan
- Open field: 5 m, 10 m, 20 m, 30 m, 50 m; record discovery time, connection time, packet delivery and RTT.
- Indoor: one concrete wall, two walls, corridor/doorway, floor separation; repeat at 5–20 m.
- Three-hop chain: A↔B↔C with A and C outside direct radio range; verify C receives only through B.
- Mobility: walk one relay away from the chain at 1 m/s and record peer-loss/recovery time.
- Battery: repeat at 80%, 30%, 15% battery to validate duty-cycle policy.

## What is simulated vs physically verified
- `tools/protocol_sim.js`: simulated topology/flooding only.
- Android Kotlin transport: implementation target; must be run on physical Android devices to verify radios and permissions.
- iOS Swift transport: implementation target using Network framework; must be run on physical iPhones. Background behavior and radio availability are OS-controlled.
- Gateway bridge: reuses the existing Python LAN gateway concept; requires same-LAN reachability.
- Browser dashboard remains a visualization/control layer; it cannot itself create a radio mesh.
