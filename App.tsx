import React,{useEffect,useRef,useState} from 'react';
import {SafeAreaView,View,Text,Button,FlatList,StyleSheet,TextInput,Switch,ScrollView,PermissionsAndroid,Platform} from 'react-native';
import {NativeModules,NativeEventEmitter} from 'react-native';
import {MeshRouter,makePacket,stableNodeId,Neighbor,MeshPacket} from './protocol';

const {MeshNative}=NativeModules;
const router=new MeshRouter();
const DEFAULT_GATEWAY='http://192.168.1.20:8765';

type Role='PRIMARY'|'RELAY'|'GATEWAY';
export default function App(){
 const [id,setId]=useState(''); const [peers,setPeers]=useState<Neighbor[]>([]); const [log,setLog]=useState<string[]>([]);
 const [text,setText]=useState('Medical emergency'); const [gatewayUrl,setGatewayUrl]=useState(DEFAULT_GATEWAY); const [gateway,setGateway]=useState(false); const [role,setRole]=useState<Role>('RELAY');
 const peerMap=useRef(new Map<string,string>()); const gatewayRef=useRef(gateway); const roleRef=useRef(role); const idRef=useRef('');
 gatewayRef.current=gateway; roleRef.current=role;
 const addLog=(x:string)=>setLog(v=>[x,...v].slice(0,100));
 const sendTransport=async(transportId:string,p:MeshPacket)=>MeshNative.send(transportId,JSON.stringify(p));
 const updateVisiblePeers=(raw:any[])=>{const list=(raw||[]).map((x:any)=>{const stable=peerMap.current.get(x.id)||x.id;return {...x,id:stable,transportId:x.id}});router.updateNeighbors(list);setPeers(list);return list};
 async function registerGateway(telemetry:any={}){
   const base=gatewayUrl.trim().replace(/\/$/,'');if(!/^https?:\/\//.test(base))return;
   try{await fetch(base+'/api/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:idRef.current,name:`Phone ${idRef.current.slice(-6)}`,role:roleRef.current,gateway:gatewayRef.current,battery:telemetry.battery??100,rssi:telemetry.rssi??-60,latency:telemetry.latency??0,packetLoss:telemetry.packetLoss??0,transport:'nearby/network'})})}catch(e){addLog('Gateway offline: '+String(e))}
 }
 useEffect(()=>{
  let alive=true; (async()=>{const nid=await stableNodeId();if(!alive)return;idRef.current=nid;setId(nid);await router.load();
   try{if(Platform.OS==='android'){const p:any={};if(Platform.Version>=31){p[PermissionsAndroid.PERMISSIONS.BLUETOOTH_SCAN]=PermissionsAndroid.RESULTS.GRANTED;p[PermissionsAndroid.PERMISSIONS.BLUETOOTH_CONNECT]=PermissionsAndroid.RESULTS.GRANTED;p[PermissionsAndroid.PERMISSIONS.BLUETOOTH_ADVERTISE]=PermissionsAndroid.RESULTS.GRANTED;if(Platform.Version>=33)p[PermissionsAndroid.PERMISSIONS.NEARBY_WIFI_DEVICES]=PermissionsAndroid.RESULTS.GRANTED;}else{p[PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION]=PermissionsAndroid.RESULTS.GRANTED;}const res=await PermissionsAndroid.requestMultiple(Object.keys(p));const denied=Object.values(res).some((x:any)=>x!==PermissionsAndroid.RESULTS.GRANTED);if(denied){addLog('Nearby permissions not granted; mesh cannot start');return;}}await MeshNative.start({serviceId:'com.signalrescue.mesh',strategy:'P2P_CLUSTER',nodeId:nid});await MeshNative.advertise({nodeId:nid,gateway:String(gatewayRef.current),role:roleRef.current});await MeshNative.discover();addLog('Mesh discovery started');}catch(e){addLog('Transport unavailable: '+String(e))}
   await registerGateway();
  })();
  const ev=new NativeEventEmitter(MeshNative);
  const a=ev.addListener('meshPeerChanged',(x)=>{const list=updateVisiblePeers(x.peers||[]);router.flush((p,m)=>sendTransport(p,m),new Set(list.filter(n=>n.gateway).map(n=>n.id))).catch(()=>{})});
  const r=ev.addListener('meshPacket',(x)=>{try{const p:MeshPacket=JSON.parse(x.json);if(p.payloadType==='HELLO'&&p.payload?.nodeId){peerMap.current.set(x.from,p.payload.nodeId);addLog(`Discovered ${p.payload.nodeId}`);const raw=(x.peers||[]);if(raw.length)updateVisiblePeers(raw);return;}router.receive(p,x.from,(peer,m)=>sendTransport(peer,m),new Set(peers.filter(n=>n.gateway).map(n=>n.id))).then(s=>addLog(`${p.payloadType} ${p.id.slice(-8)}: ${s}`)).catch(e=>addLog('Route error: '+String(e)));}catch(e){addLog('Invalid packet: '+String(e))}});
  const heartbeat=setInterval(()=>registerGateway(),5000);
  return()=>{alive=false;clearInterval(heartbeat);a.remove();r.remove();MeshNative.stop?.()};
 },[]);
 useEffect(()=>{roleRef.current=role;MeshNative.advertise?.({nodeId:idRef.current,gateway:String(gateway),role}).catch?.(()=>{});registerGateway()},[gateway,role,gatewayUrl]);
 async function hello(transportId:string){const p=makePacket(idRef.current,'HELLO',{nodeId:idRef.current,role:roleRef.current,gateway:gatewayRef.current},'HIGH',3);await sendTransport(transportId,p)}
 async function sos(){const p=makePacket(id,'SOS',{text},'CRITICAL',8);addLog('Created CRITICAL '+p.id);if(peers.length){for(const n of peers)await sendTransport(n.transportId||n.id,p)}else{await router.receive(p,'',(peer,m)=>sendTransport(peer,m),new Set())}}
 return <SafeAreaView style={s.root}><ScrollView contentContainerStyle={{paddingBottom:30}}><Text style={s.title}>SIGNALRESCUE MESH</Text><Text style={s.sub}>Physical node: {id||'initializing…'}</Text>
 <View style={s.box}><Text style={s.label}>Node role</Text><View style={s.row}>{(['PRIMARY','RELAY','GATEWAY'] as Role[]).map(r=><View key={r} style={{flex:1,marginRight:5}}><Button title={r+(role===r?' ✓':'')} onPress={()=>setRole(r)}/></View>)}</View><View style={s.row}><Text style={s.label}>Advertise as gateway</Text><Switch value={gateway} onValueChange={setGateway}/></View><TextInput style={s.input} value={gatewayUrl} onChangeText={setGatewayUrl} autoCapitalize="none" placeholder="http://laptop-ip:8765" placeholderTextColor="#6e8495"/><Button title="Register / Sync Gateway" onPress={()=>registerGateway()}/></View>
 <TextInput style={s.input} value={text} onChangeText={setText} placeholder="Emergency message" placeholderTextColor="#6e8495"/><Button title="🚨 SEND CRITICAL SOS" onPress={sos}/>
 <Text style={s.h}>Direct mesh neighbors ({peers.length})</Text><FlatList scrollEnabled={false} data={peers} keyExtractor={x=>x.id} renderItem={({item})=><View style={s.peer}><Text style={s.rowText}>{item.id}</Text><Text style={s.meta}>{item.transport} {item.gateway?'· GATEWAY':''}</Text><Button title="Handshake" onPress={()=>hello(item.transportId||item.id)}/></View>}/>
 <Text style={s.h}>Protocol log</Text>{log.map((item,i)=><Text key={i} style={s.log}>{item}</Text>)}</ScrollView></SafeAreaView>
}
const s=StyleSheet.create({root:{flex:1,backgroundColor:'#071018'},title:{color:'#fff',fontSize:24,fontWeight:'800',paddingHorizontal:18,paddingTop:15},sub:{color:'#8fa7b7',paddingHorizontal:18,marginBottom:12},box:{backgroundColor:'#0d1822',padding:12,margin:10,borderRadius:10},label:{color:'#8fa7b7',marginBottom:7},row:{flexDirection:'row',alignItems:'center',marginBottom:10},input:{backgroundColor:'#0d1822',color:'#fff',padding:12,borderRadius:8,margin:10},h:{color:'#43d9ff',fontWeight:'700',marginTop:18,marginHorizontal:10,marginBottom:7},peer:{backgroundColor:'#0d1822',marginHorizontal:10,marginBottom:7,padding:9,borderRadius:8},rowText:{color:'#dce9ef',fontWeight:'700'},meta:{color:'#91a8b8',fontSize:11,marginVertical:4},log:{color:'#9bb0bd',fontSize:11,padding:5,marginHorizontal:10,borderBottomWidth:1,borderBottomColor:'#203746'}});
