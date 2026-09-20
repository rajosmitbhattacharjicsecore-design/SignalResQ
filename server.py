from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json, time, uuid, threading, os

HOST = os.getenv('SIGNALRESCUE_HOST', '0.0.0.0')
PORT = int(os.getenv('SIGNALRESCUE_PORT', '8765'))
STALE_AFTER = int(os.getenv('SIGNALRESCUE_STALE_AFTER', '20'))
lock = threading.RLock()
nodes, messages, acks = {}, [], {}

ROLE_DUTIES = {
    'VICTIM': {'canSend': True, 'canReceive': True, 'canForward': False, 'canAck': False, 'duty': 'Originates the SOS and supplies the victim geo-location tag.'},
    'RELAY': {'canSend': False, 'canReceive': True, 'canForward': True, 'canAck': False, 'duty': 'Accepts an SOS, preserves the victim tag, and forwards it to the next hop.'},
    'GATEWAY': {'canSend': True, 'canReceive': True, 'canForward': True, 'canAck': False, 'duty': 'Accepts mesh SOS traffic, bridges it to the dashboard, and forwards it to a HELPER.'},
    'HELPER': {'canSend': False, 'canReceive': True, 'canForward': False, 'canAck': True, 'duty': 'Accepts the SOS, views the victim location, and acknowledges receipt.'},
}

def now(): return time.time()
def clean_node(n):
    x=dict(n); x['online']=(now()-float(x.get('lastSeen',0)))<=STALE_AFTER; return x
def json_bytes(obj): return json.dumps(obj,separators=(',',':')).encode()
def normalize_role(r):
    r=str(r or '').upper().strip()
    return 'VICTIM' if r=='PRIMARY' else r

def online_nodes_by_role(role, exclude=None):
    ex=set(exclude or [])
    with lock:
        return [n for n in nodes.values() if normalize_role(n.get('role'))==role and n.get('id') not in ex and clean_node(n)['online']]

def role_of(nid):
    with lock: return normalize_role(nodes.get(nid,{}).get('role'))

def choose_next_hop(packet, current_id):
    hops=list(packet.get('hopsTaken') or []); ex=set(hops)|{current_id}; current_role=role_of(current_id)
    if current_role=='VICTIM':
        candidates=online_nodes_by_role('RELAY',ex) or online_nodes_by_role('GATEWAY',ex)
    elif current_role=='RELAY':
        candidates=online_nodes_by_role('RELAY',ex) or online_nodes_by_role('GATEWAY',ex)
    elif current_role=='GATEWAY':
        candidates=online_nodes_by_role('HELPER',ex)
    else: candidates=[]
    return candidates[0]['id'] if candidates else None

def location_from(msg):
    p=msg.get('payload') or {}; loc=p.get('victimLocation') or msg.get('victimLocation')
    return loc if isinstance(loc,dict) else None

def role_action(role, action):
    return f'{role} • {action}'

NODE_HTML = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SIGNALRESCUE Node</title>
<style>body{font-family:Arial,sans-serif;background:#07111f;color:#eaf2ff;margin:0;padding:18px}.card{max-width:720px;margin:auto;background:#0b192b;border:1px solid #20334d;border-radius:16px;padding:18px}.logo{color:#36a3ff;font-size:23px;font-weight:800}label{display:block;margin-top:12px;color:#9eb2ca;font-size:13px}.row{display:grid;grid-template-columns:1fr auto;gap:8px}select,input,button{width:100%;padding:12px;margin-top:7px;border-radius:9px;border:1px solid #29425d;background:#06121f;color:#fff;box-sizing:border-box;font-size:14px}button{background:#1677d2;font-weight:700;cursor:pointer}button.secondary{background:#233a55}button.danger{background:#7d2634;border-color:#a83d4d}button.green{background:#145b43;border-color:#237d5d}button:disabled{opacity:.42;cursor:not-allowed}.status,.panel{margin-top:13px;padding:13px;border-radius:11px;background:#081524;border:1px solid #20334d;line-height:1.5}.ok{color:#55e89b}.warn{color:#ffd166}.bad{color:#ff6b78}.small{color:#8fa6bf;font-size:11px;line-height:1.5}.msg{border-bottom:1px solid #1b3047;padding:10px 0}.msg:last-child{border-bottom:0}.tag{display:inline-block;font-size:10px;padding:3px 7px;border-radius:999px;background:#16304a;color:#9dd5ff}.tag.sos{background:#4a1d27;color:#ff9aa4}.loc{display:inline-block;margin-top:5px;padding:5px 8px;border-radius:7px;background:#12392d;color:#72edb0}.duties{display:grid;grid-template-columns:repeat(2,1fr);gap:7px}.duty{padding:8px;border:1px solid #1d344c;border-radius:8px;background:#071422;font-size:11px}.modal{position:fixed;inset:0;background:#0009;display:flex;align-items:center;justify-content:center;padding:16px;z-index:99}.modal.hidden{display:none}.modalbox{max-width:500px;width:100%;background:#0b192b;border:1px solid #31506d;border-radius:16px;padding:18px;box-shadow:0 20px 70px #000b}.modalbox h2{margin:0 0 8px}.modalbox .big{font-size:16px;font-weight:800}.modalbox .locbox{margin:12px 0;padding:12px;background:#071422;border:1px solid #1e3a51;border-radius:10px}.modalbox button{margin-top:10px}@media(max-width:480px){body{padding:8px}.card{padding:14px}.row{grid-template-columns:1fr}.duties{grid-template-columns:1fr}}</style></head><body>
<div class="card"><div class="logo">SignalResQ</div><h1>SIGNALRESCUE Node</h1><p class="small">Each node follows its assigned emergency duty. SOS location is captured only when the VICTIM sends an SOS and is carried unchanged through relays and gateways.</p>
<label>Node ID</label><div class="row"><input id="id"><button id="newId" class="secondary">Generate ID</button></div><label>Node name</label><input id="name" placeholder="My Phone"><label>Role</label><select id="role"><option value="VICTIM">VICTIM / PRIMARY — originate SOS + location</option><option value="RELAY">RELAY — accept + forward SOS</option><option value="GATEWAY">GATEWAY — accept + bridge + forward</option><option value="HELPER">HELPER — accept + acknowledge</option></select><button id="register">Register / Start Node</button><div class="status" id="status">Not registered.</div>
<div class="panel"><b>Current duty</b><div id="duty" class="small"></div><div class="duties"><div class="duty">VICTIM<br>🚨 Send + location</div><div class="duty">RELAY<br>📥 Accept → ↗ Forward</div><div class="duty">GATEWAY<br>📥 Accept → 🌐 Bridge → ↗ Forward</div><div class="duty">HELPER<br>📥 Accept → ✓ Acknowledge</div></div></div>
<div class="panel"><b>Actions</b><button id="sendSOS" class="danger">🚨 Send CRITICAL SOS + Location</button><button id="forwardSOS" class="secondary">↗ Forward Accepted SOS</button><button id="ackSOS" class="green">✓ Accept / Acknowledge SOS</button><div id="hint" class="small" style="margin-top:7px"></div></div>
<div class="panel"><b>Incoming / transferred information</b><div id="inbox" class="small">Register the node to begin receiving.</div></div></div>
<div id="modal" class="modal hidden"><div class="modalbox"><h2 id="modalTitle">SOS</h2><div id="modalBody"></div><button id="modalClose" class="secondary">Close</button></div></div>
<script>(function(){'use strict';const $=id=>document.getElementById(id),ID='srId',NM='srName',RL='srRole';let reg=false,lastIds=new Set(),inbox=[];
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function rid(){try{if(crypto.randomUUID)return 'PHONE-'+crypto.randomUUID().replace(/-/g,'').slice(0,10).toUpperCase()}catch(e){}return 'PHONE-'+Math.random().toString(36).slice(2,10).toUpperCase()};function valid(x){return /^[A-Za-z0-9_-]{3,40}$/.test(x)}function role(){return $('role').value}function id(){return $('id').value.trim()}
function modal(title,html){$('modalTitle').textContent=title;$('modalBody').innerHTML=html;$('modal').classList.remove('hidden')}function locHtml(loc){if(!loc)return '<span class="small">No victim location tag available.</span>';let u='https://www.google.com/maps?q='+encodeURIComponent(loc.lat+','+loc.lon);return '<div class="locbox"><b>📍 Victim geo-location</b><br>Latitude: '+esc(loc.lat)+'<br>Longitude: '+esc(loc.lon)+'<br>Accuracy: '+esc(loc.accuracy??'—')+' m<br><a href="'+u+'" target="_blank" rel="noopener" style="color:#72edb0">Open map</a></div>'}
function setStatus(h){$('status').innerHTML=h}function update(){let r=role();let d={VICTIM:'Originates the emergency SOS and attaches the victim device geo-location. Can receive transfers.',RELAY:'Accepts an SOS from a previous hop, preserves the victim location tag, then forwards it to another RELAY/GATEWAY.',GATEWAY:'Accepts mesh SOS traffic, bridges it to the dashboard, then forwards it to an available HELPER.',HELPER:'Accepts the SOS, displays the victim geo-location, and acknowledges receipt.'};$('duty').textContent=d[r];$('sendSOS').disabled=!reg||!['VICTIM','GATEWAY'].includes(r);$('forwardSOS').disabled=!reg||!['RELAY','GATEWAY'].includes(r);$('ackSOS').disabled=!reg||r!=='HELPER';$('hint').textContent=d[r]}
function payload(){return {id:id(),name:($('name').value||id()).trim(),role:role(),transport:'browser-lan-node',battery:null,rssi:null,latency:null,packetLoss:null,gateway:role()==='GATEWAY',neighbors:[]}}
async function register(){if(!valid(id()))return setStatus('<span class="bad">Invalid Node ID.</span>');let d=payload();localStorage.setItem(ID,d.id);localStorage.setItem(NM,d.name);localStorage.setItem(RL,d.role);try{let r=await fetch('/api/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)}),j=await r.json();if(!r.ok||!j.ok)throw Error(j.error||r.status);reg=true;setStatus('<span class="ok">● REGISTERED</span> · '+esc(j.id)+' · <b>'+esc(j.node.role)+'</b>');update();await poll()}catch(e){setStatus('<span class="bad">Registration failed:</span> '+esc(e.message))}}
async function geo(){return new Promise(resolve=>{if(!navigator.geolocation)return resolve(null);navigator.geolocation.getCurrentPosition(p=>resolve({lat:+p.coords.latitude.toFixed(6),lon:+p.coords.longitude.toFixed(6),accuracy:Math.round(p.coords.accuracy),capturedAt:Date.now()}),()=>resolve(null),{enableHighAccuracy:true,timeout:8000,maximumAge:0})})}
async function sendSOS(){if(role()!=='VICTIM'&&role()!=='GATEWAY')return;let loc=role()==='VICTIM'?await geo():null;if(role()==='VICTIM'&&!loc){if(!confirm('Location permission was denied/unavailable. Send SOS without a geo-location tag?'))return}let pid='SOS-'+Date.now().toString(36).toUpperCase();let p={id:pid,sourceId:id(),sourceRole:role(),originId:id(),originRole:role(),ttl:8,hopsTaken:[id()],priority:'CRITICAL',payloadType:'SOS',payload:{text:'Emergency SOS from '+($('name').value||id()),createdBy:id(),victimLocation:loc},createdAt:Date.now()};await send(p,'SEND')}
async function forwardSOS(){if(role()!=='RELAY'&&role()!=='GATEWAY')return;let m=inbox.find(x=>(x.payloadType||x.type)==='SOS'&&x.status!=='acknowledged');if(!m)return modal('No SOS to forward','This node has no pending SOS assigned to it.');let p={...m,sourceId:id(),sourceRole:role(),originId:m.originId||m.sourceId,originRole:m.originRole||'VICTIM',forwardedBy:id(),action:'FORWARD',hopsTaken:[...(m.hopsTaken||[]),id()],ttl:Math.max(0,Number(m.ttl??8)-1)};delete p.receivedAt;await send(p,'FORWARD')}
async function ackSOS(){if(role()!=='HELPER')return;let m=inbox.find(x=>(x.payloadType||x.type)==='SOS');if(!m)return modal('Nothing pending','No SOS is waiting for acknowledgement.');let a={id:'ACK-'+Date.now().toString(36).toUpperCase(),type:'ACK',ackFor:m.id,sourceId:id(),sourceRole:'HELPER',targetId:m.originId||m.sourceId,priority:'HIGH',payloadType:'ACK',payload:{text:'SOS accepted by '+($('name').value||id()),victimLocation:(m.payload||{}).victimLocation||m.victimLocation}};try{let r=await fetch('/api/ack',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(a)}),j=await r.json();if(!r.ok||!j.ok)throw Error(j.error||r.status);modal('✓ SOS ACCEPTED', '<div class="big">HELPER has accepted the emergency message.</div>'+locHtml((m.payload||{}).victimLocation||m.victimLocation));await poll()}catch(e){modal('ACK FAILED',esc(e.message))}}
async function send(p,action){try{let r=await fetch('/api/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)}),j=await r.json();if(!r.ok||!j.ok)throw Error(j.error||r.status);let m=j.message||p;await poll();let loc=(m.payload||{}).victimLocation||m.victimLocation;let title=action==='SEND'?'🚨 SOS SENT':action==='FORWARD'?'↗ SOS FORWARDED':'MESSAGE TRANSFERRED';modal(title,'<div class="big">'+esc(role())+' • '+esc(action)+'</div><div class="small">Packet: '+esc(m.id)+'<br>Next destination: '+esc(m.recipientId||'gateway queue / awaiting next hop')+'<br>Route: '+esc((m.hopsTaken||[]).join(' → ')||'—')+'</div>'+locHtml(loc))}catch(e){modal('⚠ TRANSFER FAILED','<div class="bad">'+esc(e.message)+'</div>')}}
function render(){if(!inbox.length){$('inbox').innerHTML='No SOS messages for this node yet.';return}$('inbox').innerHTML=inbox.slice().reverse().slice(0,20).map(m=>{let loc=(m.payload||{}).victimLocation||m.victimLocation;return '<div class="msg"><span class="tag sos">'+esc(m.payloadType||m.type||'SOS')+'</span> <b>'+esc(m.id||'')+'</b><div class="small">Origin: '+esc(m.originId||m.sourceId||'unknown')+' · Current sender: '+esc(m.sourceId||'unknown')+' · Status: '+esc(m.status||'received')+'</div><div class="small">Route: '+esc((m.hopsTaken||[]).join(' → ')||'—')+'</div>'+(loc?'<div class="loc">📍 '+esc(loc.lat)+', '+esc(loc.lon)+' ±'+esc(loc.accuracy??'—')+'m</div>':'')+'</div>'}).join('')}
async function poll(){if(!reg)return;try{let r=await fetch('/api/inbox?nodeId='+encodeURIComponent(id())),j=await r.json();if(!r.ok||!j.ok)return;let next=j.messages||[];next.forEach(m=>{if(!lastIds.has(m.id)){lastIds.add(m.id);if(m.payloadType==='SOS'&&m.recipientId===id()&&role()!=='VICTIM'){let loc=(m.payload||{}).victimLocation||m.victimLocation;modal('📥 SOS RECEIVED','<div class="big">'+esc(role())+' has received an emergency SOS.</div><div class="small">From: '+esc(m.sourceId||m.originId||'unknown')+'<br>Route: '+esc((m.hopsTaken||[]).join(' → ')||'—')+'</div>'+locHtml(loc))}});inbox=next;render()}catch(e){}}
$('modalClose').onclick=()=>$('modal').classList.add('hidden');$('newId').onclick=()=>{$('id').value=rid()};$('register').onclick=register;$('role').onchange=update;$('sendSOS').onclick=sendSOS;$('forwardSOS').onclick=forwardSOS;$('ackSOS').onclick=ackSOS;try{$('id').value=localStorage.getItem(ID)||rid();$('name').value=localStorage.getItem(NM)||'My Phone';$('role').value=localStorage.getItem(RL)||'VICTIM'}catch(e){$('id').value=rid()}update();setInterval(poll,1200)})();</script></body></html>'''

class Handler(BaseHTTPRequestHandler):
    server_version='SIGNALRESCUE-Gateway/2.0'
    def headers_common(self,length=None):
        self.send_header('Access-Control-Allow-Origin','*');self.send_header('Access-Control-Allow-Methods','GET,POST,OPTIONS');self.send_header('Access-Control-Allow-Headers','Content-Type,Authorization');self.send_header('Cache-Control','no-store')
        if length is not None:self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(length))
    def reply(self,code,obj):
        b=json_bytes(obj);self.send_response(code);self.headers_common(len(b));self.end_headers();self.wfile.write(b)
    def do_OPTIONS(self): self.send_response(204);self.headers_common();self.end_headers()
    def read_json(self):
        try:return json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))) or b'{}')
        except:return {}
    def do_GET(self):
        path=urlparse(self.path).path
        if path=='/node':
            b=NODE_HTML.encode();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(b)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(b);return
        if path=='/api/health': self.reply(200,{'ok':True,'service':'SIGNALRESCUE gateway','time':now(),'version':'2.0'});return
        if path=='/api/roles': self.reply(200,{'ok':True,'roles':ROLE_DUTIES});return
        if path=='/api/state':
            with lock:self.reply(200,{'ok':True,'serverTime':now(),'staleAfter':STALE_AFTER,'nodes':[clean_node(n) for n in nodes.values()],'messages':messages[-300:],'acks':list(acks.values())[-100:]})
            return
        if path=='/api/inbox':
            nid=(parse_qs(urlparse(self.path).query).get('nodeId') or [''])[0]
            if not nid:return self.reply(400,{'ok':False,'error':'nodeId required'})
            with lock:
                role=role_of(nid); inbox=[m for m in messages[-500:] if m.get('recipientId')==nid or m.get('targetId')==nid]
                if role=='GATEWAY': inbox += [m for m in messages[-500:] if m.get('payloadType')=='SOS' and m.get('status') in ('gateway-received','gateway-delivered') and m not in inbox]
            self.reply(200,{'ok':True,'nodeId':nid,'role':role,'messages':inbox[-100:]});return
        if path=='/api/messages':
            with lock:self.reply(200,{'ok':True,'messages':messages[-300:]})
            return
        self.reply(404,{'ok':False,'error':'not found'})
    def do_POST(self):
        path=urlparse(self.path).path;data=self.read_json();ts=now()
        if path=='/api/register':
            nid=str(data.get('id') or 'NODE-'+uuid.uuid4().hex[:10].upper());role=normalize_role(data.get('role') or 'RELAY')
            if role not in ROLE_DUTIES:return self.reply(400,{'ok':False,'error':'Invalid role'})
            with lock:
                prev=nodes.get(nid,{})
                node={**prev,**data,'id':nid,'role':role,'lastSeen':ts,'registeredAt':prev.get('registeredAt',ts)};node.setdefault('name',nid);node.setdefault('transport','mobile');node.setdefault('gateway',role=='GATEWAY');nodes[nid]=node
            return self.reply(200,{'ok':True,'id':nid,'node':clean_node(node),'duty':ROLE_DUTIES[role]})
        if path=='/api/telemetry':
            nid=str(data.get('id',''))
            if not nid:return self.reply(400,{'ok':False,'error':'id required'})
            with lock:
                node=nodes.setdefault(nid,{'id':nid,'registeredAt':ts});node.update(data);node['role']=normalize_role(node.get('role') or 'RELAY');node['lastSeen']=ts;nodes[nid]=node
            return self.reply(200,{'ok':True,'node':clean_node(node)})
        if path in ('/api/send','/api/message'):
            mid=str(data.get('id') or 'MSG-'+uuid.uuid4().hex[:12].upper());source_id=str(data.get('sourceId') or '');
            if source_id=='WEB-DASHBOARD' and source_id not in nodes:
                nodes[source_id]={'id':source_id,'name':'SIGNALRESCUE Dashboard','role':'GATEWAY','gateway':True,'transport':'WEB','registeredAt':ts,'lastSeen':ts}
            source_role=normalize_role(data.get('sourceRole') or role_of(source_id));is_sos=(str(data.get('payloadType') or data.get('type') or '').upper()=='SOS' or str(data.get('priority') or '').upper()=='CRITICAL')
            if not source_id or source_id not in nodes:return self.reply(403,{'ok':False,'error':f'Node {source_id or "UNKNOWN"} is not registered; register the node first'})
            if is_sos and source_role not in ROLE_DUTIES:return self.reply(403,{'ok':False,'error':f'Role {source_role or "UNKNOWN"} is not permitted for SOS'})
            action=str(data.get('action') or ('ORIGINATE' if source_role in ('VICTIM','GATEWAY') else 'FORWARD')).upper()
            if is_sos:
                if action=='ORIGINATE' and source_role not in ('VICTIM','GATEWAY'):return self.reply(403,{'ok':False,'error':f'{source_role} duty is RECEIVE/FORWARD, not originate'})
                if action=='FORWARD' and source_role not in ('RELAY','GATEWAY'):return self.reply(403,{'ok':False,'error':f'{source_role} duty is not forwarding SOS'})
            msg={**data,'id':mid,'receivedAt':ts,'sourceId':source_id,'sourceRole':source_role,'action':action}
            if is_sos:
                payload=dict(msg.get('payload') or {});origin_id=msg.get('originId') or (source_id if source_role=='VICTIM' else payload.get('createdBy') or source_id);msg['originId']=origin_id;msg['originRole']=msg.get('originRole') or ('VICTIM' if source_role!='GATEWAY' else 'GATEWAY');msg['payload']=payload
                loc=location_from(msg)
                if loc: msg['victimLocation']=loc
                hops=list(msg.get('hopsTaken') or [])
                if source_id not in hops:hops.append(source_id)
                msg['hopsTaken']=hops
                if int(msg.get('ttl',8))<=0:msg['status']='ttl-expired'
                else:
                    nxt=choose_next_hop(msg,source_id)
                    if source_role=='GATEWAY':
                        msg['status']='gateway-received'
                        if action=='FORWARD' and nxt:msg['recipientId']=nxt;msg['status']='gateway-forwarded'
                        elif action=='ORIGINATE' and nxt:msg['recipientId']=nxt;msg['status']='gateway-forwarded'
                    elif nxt:
                        msg['recipientId']=nxt;msg['status']='forwarded' if action=='FORWARD' else 'sent-to-relay'
                    else:msg['status']='route-pending'
                msg['roleAction']=role_action(source_role,{'ORIGINATE':'sent SOS','FORWARD':'forwarded SOS'}.get(action,'transferred SOS'))
            else:
                msg['status']=data.get('status','received');msg['recipientId']=data.get('targetId') or data.get('recipientId')
            with lock:messages.append(msg);messages[:]=messages[-500:]
            self.reply(200,{'ok':True,'id':mid,'message':msg});return
        if path=='/api/ack':
            aid=str(data.get('id') or uuid.uuid4());ack={**data,'id':aid,'receivedAt':ts}
            with lock:
                acks[aid]=ack
                for m in reversed(messages):
                    if m.get('id')==data.get('ackFor'):m['status']='acknowledged';m['ackBy']=data.get('sourceId');break
            self.reply(200,{'ok':True,'ack':ack});return
        self.reply(404,{'ok':False,'error':'not found'})
    def log_message(self,fmt,*args):print('[gateway]',fmt%args)

if __name__=='__main__':
    print(f'SIGNALRESCUE gateway listening on http://127.0.0.1:{PORT}')
    print(f'LAN dashboard/API: http://<YOUR-LAN-IP>:{PORT}')
    ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
