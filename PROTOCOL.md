# SIGNALRESCUE Mesh Protocol v1

## Transport abstraction
`MeshTransport` exposes `advertise`, `discover`, `connect`, `send`, `onReceive`, `onPeerLost`, `stop`.
Android uses Google Nearby Connections `P2P_CLUSTER`; iOS uses Network framework Bonjour/TCP peer sessions in this starter. Apple documents MultipeerConnectivity as deprecated and recommends Network framework, so this implementation avoids starting new production code on the deprecated framework.

## Packet
```json
{"id":"NODE-abc-xyz","sourceId":"NODE-abc","ttl":8,"hopsTaken":[],"priority":"CRITICAL","payloadType":"SOS","payload":{"text":"..."},"createdAt":1760000000000,"signature":"...","publicKey":"..."}
```

## Flooding/dedup
On first receipt, store `id` in an LRU/expiring seen cache. Append the local node ID, decrement TTL, then forward to all connected peers except the ingress peer. Drop duplicates and TTL=0 packets. A production implementation should cap packet size and seen-cache age.

## Store-and-forward
If there are no usable peers, persist the packet locally with an expiry. When a peer appears, flush queued packets subject to TTL/expiry and priority.

## Gateway
A node announces `gateway=true` when it has Internet/cellular reachability. CRITICAL traffic prefers gateway-advertised peers, but flooding remains the safety fallback. The Python LAN gateway is represented as a supernode via HTTP bridge; it is not the only route.

## ACK
Destination/gateway creates `{payloadType:"ACK", ackFor:<original id>}`. ACK follows the recorded reverse path. Sender marks the original as acknowledged only after verifying the ACK ID and signature.

## Integrity
Production packets must carry an Ed25519 signature over canonical packet bytes. Public keys are bound to the persisted node ID during enrollment/pairing. Reject invalid signatures and stale/replayed packets.

## Battery
At >30% battery: normal discovery/advertising. At 15–30%: lengthen discovery windows but preserve SOS receive/relay. Below 15%: reduce background duty cycle further, but never disable an active SOS relay path solely because of battery.

## Dead-zone risk in real topology
Risk should combine neighbor count, gateway reachability, packet delivery, latency, and recent peer churn. Suggested prototype classification: Green = >=2 usable neighbors and a gateway path; Yellow = one usable neighbor OR gateway path unstable; Red = zero usable neighbors OR no gateway path for a sustained interval. These are project thresholds, not radio standards.
