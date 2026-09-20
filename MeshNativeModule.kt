package com.signalrescue.mesh

import android.content.Context
import com.facebook.react.bridge.*
import com.facebook.react.modules.core.DeviceEventManagerModule
import com.google.android.gms.nearby.Nearby
import com.google.android.gms.nearby.connection.*

class MeshNativeModule(private val ctx: ReactApplicationContext): ReactContextBaseJavaModule(ctx) {
    private val strategy = Strategy.P2P_CLUSTER
    private val serviceId = "com.signalrescue.mesh"
    private val peers = mutableSetOf<String>()
    override fun getName() = "MeshNative"

    private fun emit(name: String, map: WritableMap) {
        ctx.getJSModule(DeviceEventManagerModule.RCTDeviceEventEmitter::class.java).emit(name, map)
    }

    @ReactMethod fun start(opts: ReadableMap, p: Promise) { p.resolve(true) }

    @ReactMethod fun hasInternet(p: Promise) {
        val cm = ctx.getSystemService(Context.CONNECTIVITY_SERVICE) as android.net.ConnectivityManager
        p.resolve(cm.activeNetwork != null)
    }

    @ReactMethod fun advertise(meta: ReadableMap, p: Promise) {
        Nearby.getConnectionsClient(ctx)
            .startAdvertising(ctx.packageName, serviceId, life, AdvertisingOptions.Builder().setStrategy(strategy).build())
            .addOnSuccessListener { p.resolve(true) }
            .addOnFailureListener { p.reject("ADVERTISE", it) }
    }

    @ReactMethod fun discover(p: Promise) {
        Nearby.getConnectionsClient(ctx)
            .startDiscovery(serviceId, disc, DiscoveryOptions.Builder().setStrategy(strategy).build())
            .addOnSuccessListener { p.resolve(true) }
            .addOnFailureListener { p.reject("DISCOVER", it) }
    }

    @ReactMethod fun connect(id: String, p: Promise) {
        Nearby.getConnectionsClient(ctx).requestConnection(ctx.packageName, id, life)
            .addOnSuccessListener { p.resolve(true) }
            .addOnFailureListener { p.reject("CONNECT", it) }
    }

    @ReactMethod fun send(id: String, json: String, p: Promise) {
        Nearby.getConnectionsClient(ctx).sendPayload(id, Payload.fromBytes(json.toByteArray(Charsets.UTF_8)))
            .addOnSuccessListener { p.resolve(true) }
            .addOnFailureListener { p.reject("SEND", it) }
    }

    @ReactMethod fun stop(p: Promise) {
        Nearby.getConnectionsClient(ctx).stopAllEndpoints()
        Nearby.getConnectionsClient(ctx).stopAdvertising()
        Nearby.getConnectionsClient(ctx).stopDiscovery()
        peers.clear(); emitPeers(); p.resolve(true)
    }

    private val life = object: ConnectionLifecycleCallback() {
        override fun onConnectionInitiated(id: String, info: ConnectionInfo) {
            Nearby.getConnectionsClient(ctx).acceptConnection(id, payload)
        }
        override fun onConnectionResult(id: String, res: ConnectionResolution) {
            if (res.status.isSuccess) { peers.add(id); emitPeers() }
        }
        override fun onDisconnected(id: String) { peers.remove(id); emitPeers() }
    }

    private val disc = object: EndpointDiscoveryCallback() {
        override fun onEndpointFound(id: String, info: DiscoveredEndpointInfo) {
            Nearby.getConnectionsClient(ctx).requestConnection(ctx.packageName, id, life)
        }
        override fun onEndpointLost(id: String) { peers.remove(id); emitPeers() }
    }

    private val payload = object: PayloadCallback() {
        override fun onPayloadReceived(id: String, p: Payload) {
            if (p.type == Payload.Type.BYTES) {
                val bytes = p.asBytes() ?: return
                val m = Arguments.createMap(); m.putString("from", id); m.putString("json", String(bytes, Charsets.UTF_8)); emit("meshPacket", m)
            }
        }
        override fun onPayloadTransferUpdate(id: String, u: PayloadTransferUpdate) {}
    }

    private fun emitPeers() {
        val a = Arguments.createArray()
        peers.forEach { id ->
            val m = Arguments.createMap(); m.putString("id", id); m.putString("transportId", id); m.putBoolean("gateway", false); m.putString("transport", "nearby"); a.pushMap(m)
        }
        val out = Arguments.createMap(); out.putArray("peers", a); emit("meshPeerChanged", out)
    }
}
