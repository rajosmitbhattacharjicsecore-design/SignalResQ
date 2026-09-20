import Foundation
import Network
import React

@objc(MeshNative)
final class MeshNative: RCTEventEmitter {
  private let service = "_signalrescue._tcp"
  private var browser: NWBrowser?
  private var listener: NWListener?
  private var conns: [String:NWConnection] = [:]
  private var id = UserDefaults.standard.string(forKey: "sr.node.id") ?? UUID().uuidString
  override init(){ super.init(); UserDefaults.standard.set(id,forKey:"sr.node.id") }
  override func supportedEvents()->[String]! { ["meshPeerChanged","meshPacket"] }
  @objc(start:resolver:rejecter:) func start(_ opts:NSDictionary,resolver resolve:RCTPromiseResolveBlock,rejecter reject:RCTPromiseRejectBlock){startListener();startBrowser();resolve(true)}
  @objc(hasInternet:rejecter:) func hasInternet(_ resolve:RCTPromiseResolveBlock,rejecter reject:RCTPromiseRejectBlock){let p=NWPathMonitor();let q=DispatchQueue(label:"sr.path");p.pathUpdateHandler={path in resolve(path.status == .satisfied);p.cancel()};p.start(queue:q)}
  @objc(advertise:resolver:rejecter:) func advertise(_ meta:NSDictionary,resolver resolve:RCTPromiseResolveBlock,rejecter reject:RCTPromiseRejectBlock){resolve(true)}
  @objc(discover:resolver:rejecter:) func discover(_ resolve:RCTPromiseResolveBlock,rejecter reject:RCTPromiseRejectBlock){resolve(true)}
  @objc(connect:resolver:rejecter:) func connect(_ peer:String,resolver resolve:RCTPromiseResolveBlock,rejecter reject:RCTPromiseRejectBlock){resolve(true)}
  @objc(send:json:resolver:rejecter:) func send(_ peer:String,json:String,resolver resolve:RCTPromiseResolveBlock,rejecter reject:RCTPromiseRejectBlock){guard let c=conns[peer],let d=json.data(using:.utf8) else {reject("NO_PEER","Peer unavailable",nil);return};c.send(content:d,completion:.contentProcessed{e in e == nil ? resolve(true):reject("SEND","send failed",e)} )}
  @objc(stop:resolver:rejecter:) func stop(_ resolve:RCTPromiseResolveBlock,rejecter reject:RCTPromiseRejectBlock){browser?.cancel();listener?.cancel();conns.values.forEach{$0.cancel()};conns.removeAll();resolve(true)}
  private func startListener(){listener=try? NWListener(using:.tcp);listener?.service=NWListener.Service(name:id,type:service);listener?.newConnectionHandler={ [weak self] c in self?.accept(c)};listener?.start(queue:.global())}
  private func startBrowser(){let p=NWParameters.tcp;browser=NWBrowser(for:.bonjour(type:service,domain:nil),using:p);browser?.browseResultsChangedHandler={ [weak self] results,_ in for r in results {if case let .service(name:name,_,_,_)=r.endpoint {self?.connectService(name,r.endpoint)}}};browser?.start(queue:.global())}
  private func connectService(_ name:String,_ endpoint:NWEndpoint){if conns[name] != nil{return};let c=NWConnection(to:endpoint,using:.tcp);conns[name]=c;observe(c,name);c.start(queue:.global())}
  private func accept(_ c:NWConnection){observe(c,UUID().uuidString);c.start(queue:.global())}
  private func observe(_ c:NWConnection,_ peer:String){c.stateUpdateHandler={ [weak self] st in if case .ready=st {self?.emitPeers()} else if case .failed(_)=st {self?.conns.removeValue(forKey:peer);self?.emitPeers()}};c.receive(minimumIncompleteLength:1,maximumLength:64*1024){[weak self] data,_,_,_ in if let data=data,let json=String(data:data,encoding:.utf8){self?.sendEvent(withName:"meshPacket",body:["from":peer,"json":json])};self?.observe(c,peer)}}
  private func emitPeers(){sendEvent(withName:"meshPeerChanged",body:["peers":conns.keys.map{["id":$0,"gateway":false,"transport":"network"]}])}
}
