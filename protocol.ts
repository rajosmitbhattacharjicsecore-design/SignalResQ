import AsyncStorage from '@react-native-async-storage/async-storage';

export type Priority = 'CRITICAL'|'HIGH'|'NORMAL';
export type PayloadType = 'SOS'|'STATUS'|'ACK'|'HELLO'|'GATEWAY';
export interface MeshPacket { id:string; sourceId:string; ttl:number; hopsTaken:string[]; priority:Priority; payloadType:PayloadType; payload:any; createdAt:number; signature?:string; publicKey?:string; ackFor?:string; }
export interface Neighbor { id:string; transportId?:string; name?:string; gateway:boolean; lastSeen:number; transport:string; battery?:number; rssi?:number; latency?:number; packetLoss?:number; }
const SEEN_KEY='sr_seen_v2', QUEUE_KEY='sr_queue_v2', NODE_KEY='sr_node_id_v2';
const MAX_SEEN=1000;

export async function stableNodeId(){let id=await AsyncStorage.getItem(NODE_KEY);if(!id){id='NODE-'+cryptoRandom();await AsyncStorage.setItem(NODE_KEY,id)}return id}
function cryptoRandom(){return Array.from({length:24},()=>Math.floor(Math.random()*16).toString(16)).join('')}
export function makePacket(sourceId:string,payloadType:PayloadType,payload:any,priority:Priority='NORMAL',ttl=8):MeshPacket{return {id:sourceId+'-'+Date.now().toString(36)+'-'+cryptoRandom().slice(0,8),sourceId,ttl,hopsTaken:[],priority,payloadType,payload,createdAt:Date.now()}}

export class MeshRouter {
 private seen=new Map<string,number>(); private queue:MeshPacket[]=[]; private neighbors=new Map<string,Neighbor>();
 async load(){const q=await AsyncStorage.getItem(QUEUE_KEY);this.queue=q?JSON.parse(q):[];const s=await AsyncStorage.getItem(SEEN_KEY);if(s)for(const [k,v] of JSON.parse(s))this.seen.set(k,v);}
 async persist(){await AsyncStorage.setItem(QUEUE_KEY,JSON.stringify(this.queue));await AsyncStorage.setItem(SEEN_KEY,JSON.stringify([...this.seen.entries()].slice(-MAX_SEEN)))}
 updateNeighbors(ns:Neighbor[]){this.neighbors=new Map(ns.map(n=>[n.id,n]));}
 isDuplicate(p:MeshPacket){return this.seen.has(p.id)}
 async receive(p:MeshPacket,fromPeer:string,send:(peer:string,p:MeshPacket)=>Promise<void>,gatewayIds:Set<string>){
   if(!p?.id||this.seen.has(p.id))return 'duplicate';
   this.seen.set(p.id,Date.now());
   p.hopsTaken=[...(p.hopsTaken||[])];const self=await stableNodeId();if(!p.hopsTaken.includes(self))p.hopsTaken.push(self);
   if(p.payloadType==='ACK')return 'ack';
   if(p.ttl<=0)return 'ttl_expired';p.ttl--;
   const peers=[...this.neighbors.values()].filter(n=>(n.transportId||n.id)!==fromPeer && n.id!==fromPeer);
   if(!peers.length){this.queue.push(p);await this.persist();return 'stored';}
   const ordered=peers.sort((a,b)=>Number(gatewayIds.has(b.id))-Number(gatewayIds.has(a.id)));
   if(p.priority==='CRITICAL')ordered.sort((a,b)=>Number(b.gateway)-Number(a.gateway));
   for(const n of ordered)await send(n.transportId||n.id,p);
   await this.persist();return 'forwarded';
 }
 async flush(send:(peer:string,p:MeshPacket)=>Promise<void>,gatewayIds:Set<string>){const peers=[...this.neighbors.values()];if(!peers.length)return;const out=this.queue.splice(0);for(const p of out){p.ttl=Math.max(p.ttl,2);for(const n of peers.sort((a,b)=>Number(gatewayIds.has(b.id))-Number(gatewayIds.has(a.id))))await send(n.transportId||n.id,p)}await this.persist()}
 pending(){return this.queue.length}
}
