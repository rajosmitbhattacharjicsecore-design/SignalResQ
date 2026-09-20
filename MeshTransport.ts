export type ReceiveHandler=(peerId:string,bytes:Uint8Array)=>void;
export type PeerLostHandler=(peerId:string)=>void;
export interface MeshTransport { advertise(meta:Record<string,string>):Promise<void>; discover():Promise<void>; connect(peerId:string):Promise<void>; send(peerId:string,bytes:Uint8Array):Promise<void>; onReceive(cb:ReceiveHandler):void; onPeerLost(cb:PeerLostHandler):void; stop():Promise<void>; }
