const N=+process.argv[2]||25, STEPS=+process.argv[3]||2000, TTL=8;
function id(i){return 'N'+i}
let nodes=Array.from({length:N},(_,i)=>({id:id(i),peers:new Set()}));
for(let i=0;i<N;i++)for(let j=i+1;j<N;j++)if(Math.random()<.14){nodes[i].peers.add(j);nodes[j].peers.add(i)}
function flood(src){let pkt={id:'P'+src+'-'+Math.random(),ttl:TTL,hops:[],seen:new Set([src])};let q=[src];while(q.length){let u=q.shift();pkt.hops.push(id(u));if(pkt.ttl--<=0)break;for(const v of nodes[u].peers)if(!pkt.seen.has(v)){pkt.seen.add(v);q.push(v)}}return pkt}
let delivered=0,total=0;for(let s=0;s<STEPS;s++){const src=Math.floor(Math.random()*N);const p=flood(src);total++;if(p.seen.size>N*.5)delivered++}
console.log(JSON.stringify({nodes:N,steps:STEPS,ttl:TTL,avgReachability:`${(delivered/total*100).toFixed(1)}%`,note:'Monte Carlo flooding harness; topology and loss are simulated, not radio-verified.'},null,2));
