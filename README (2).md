# SIGNALRESCUE — Role-Based SOS Node Server v2.1

This update makes every node role explicit and adds transfer popups plus a victim geo-location tag.

## Role duties

- **VICTIM / PRIMARY:** originates SOS; captures device location; can receive transfers.
- **RELAY:** accepts an SOS addressed to it; preserves the original victim ID/location; forwards to another RELAY or GATEWAY.
- **GATEWAY:** accepts mesh SOS traffic; bridges it to the dashboard; forwards it to an available HELPER. The dashboard is treated as a trusted GATEWAY control node.
- **HELPER:** accepts the SOS; sees the victim location; acknowledges receipt.

## SOS information carried through the route

Each SOS keeps:

- `originId` / `originRole` — original victim identity
- `sourceId` / `sourceRole` — current forwarding node
- `hopsTaken` — route history
- `ttl` — hop limit
- `priority: CRITICAL`
- `victimLocation: {lat, lon, accuracy, capturedAt}` when location permission is available

Relays and gateways do **not** replace the victim location with their own location.

## Popups

Nodes show a transfer popup for:

- **SEND:** SOS sent, next destination, route, victim location
- **RECEIVE:** SOS accepted by the node, sender, route, victim location
- **FORWARD:** SOS forwarded, next destination, route, victim location
- **HELPER ACK:** SOS accepted/acknowledged with the victim location

The victim browser asks for geolocation permission only when the VICTIM presses **Send CRITICAL SOS + Location**. If location is unavailable, the victim is asked whether to continue without a location tag.

## Run

```text
cd SIGNALRESCUE_FINAL/gateway
python server.py
```

Open:

```text
http://YOUR-LAN-IP:8765/node
```

Register nodes with different roles. For example:

```text
Phone A → VICTIM
Phone B → RELAY
Phone C → GATEWAY
Phone D → HELPER
```

The browser node is a LAN prototype. Actual Bluetooth/Wi-Fi phone-to-phone radio forwarding still requires the native Android mesh app.
