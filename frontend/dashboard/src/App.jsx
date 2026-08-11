import { useState, useEffect, useRef } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";

const BACKEND = "http://localhost:8000";
const WS_URL  = "ws://127.0.0.1:8000/ws/live";

const HAZARD = {
  pothole:         { color:"#FACC15", glow:"#FACC15", icon:"🕳", label:"POTHOLE"  },
  fog:             { color:"#38BDF8", glow:"#38BDF8", icon:"🌫", label:"FOG"      },
  fire:            { color:"#FB923C", glow:"#FB923C", icon:"🔥", label:"FIRE"     },
  stalled_vehicle: { color:"#A78BFA", glow:"#A78BFA", icon:"🚗", label:"STALLED" },
  unknown:         { color:"#FACC15", glow:"#FACC15", icon:"⚠",  label:"HAZARD"  },
};

function GlowPin({ h }) {
  const [hov, setHov] = useState(false);
  const info = HAZARD[h.hazard_type] || HAZARD.unknown;
  return (
    <>
      <CircleMarker center={[h.latitude,h.longitude]} radius={hov?26:16}
        pathOptions={{color:info.color,fillColor:"transparent",fillOpacity:0,weight:1.5,opacity:hov?0.8:0.3}}
        eventHandlers={{mouseover:()=>setHov(true),mouseout:()=>setHov(false)}}/>
      <CircleMarker center={[h.latitude,h.longitude]} radius={hov?11:7}
        pathOptions={{color:info.color,fillColor:info.color,fillOpacity:hov?1:0.9,weight:2}}
        eventHandlers={{mouseover:()=>setHov(true),mouseout:()=>setHov(false)}}>
        <Popup>
          <div style={{width:210,background:"#0F172A",border:`1.5px solid ${info.color}`,borderRadius:12,padding:"16px 18px",fontFamily:"'DM Mono',monospace",boxShadow:`0 0 32px ${info.color}55`,overflow:"hidden",position:"relative"}}>
            <div style={{position:"absolute",top:0,left:0,right:0,height:3,background:`linear-gradient(90deg,transparent,${info.color},transparent)`}}/>
            <div style={{fontSize:10,letterSpacing:"0.18em",color:info.color,marginBottom:10,display:"flex",alignItems:"center",gap:8}}>
              <span style={{width:7,height:7,borderRadius:"50%",background:info.color,display:"inline-block",boxShadow:`0 0 8px ${info.color}`}}/>
              {info.label} DETECTED
            </div>
            <div style={{fontSize:17,fontWeight:700,color:"#F1F5F9",marginBottom:10,letterSpacing:"0.04em"}}>{info.icon} NODE {h.node_id}</div>
            <div style={{display:"flex",justifyContent:"space-between",fontSize:11,color:"#64748B",marginBottom:6}}>
              <span>CONFIDENCE</span><span style={{color:info.color,fontWeight:700}}>{(h.confidence*100).toFixed(0)}%</span>
            </div>
            <div style={{height:4,background:"#1E293B",borderRadius:99,marginBottom:10,overflow:"hidden"}}>
              <div style={{width:`${h.confidence*100}%`,height:"100%",background:`linear-gradient(90deg,${info.color}88,${info.color})`,boxShadow:`0 0 8px ${info.color}`,borderRadius:99}}/>
            </div>
            <div style={{fontSize:9,color:"#334155",letterSpacing:"0.06em"}}>{h.latitude?.toFixed(5)}°N · {h.longitude?.toFixed(5)}°E</div>
          </div>
        </Popup>
      </CircleMarker>
    </>
  );
}

export default function App() {
  const [hazards,setHazards] = useState([]);
  const [feed,setFeed]       = useState([]);
  const [stats,setStats]     = useState({total_confirmed:0,by_type:{}});
  const [conn,setConn]       = useState(false);
  const [flash,setFlash]     = useState(null);
  const [time,setTime]       = useState("");
  const [booted,setBooted]   = useState(false);
  const [bootIdx,setBootIdx] = useState(0);
  const wsRef = useRef(null);

  const BOOT = [
    "> VIGILCLOUD OS v2.4 INITIALIZING...",
    "> NH-44 SENSOR ARRAY................[OK]",
    "> NEURAL DETECTION ENGINE...........[OK]",
    "> CROSS-NODE VERIFICATION NET.......[OK]",
    "> DRIVER ALERT SYSTEM...............[OK]",
    "> ALL 10 NODES ONLINE. LIVE.",
  ];

  useEffect(()=>{
    if(bootIdx<BOOT.length){const t=setTimeout(()=>setBootIdx(i=>i+1),320);return()=>clearTimeout(t);}
    else{const t=setTimeout(()=>setBooted(true),400);return()=>clearTimeout(t);}
  },[bootIdx]);

  useEffect(()=>{
    if(!booted)return;
    fetch(`${BACKEND}/hazards`).then(r=>r.json()).then(setHazards).catch(()=>{});
    fetch(`${BACKEND}/stats`).then(r=>r.json()).then(setStats).catch(()=>{});
    const t=setInterval(()=>setTime(new Date().toLocaleTimeString("en-IN",{hour12:false})),1000);
    return()=>clearInterval(t);
  },[booted]);

  useEffect(()=>{
    if(!booted)return;
    function connect(){
      const ws=new WebSocket(WS_URL);wsRef.current=ws;
      ws.onopen=()=>setConn(true);
      ws.onclose=()=>{setConn(false);setTimeout(connect,3000);};
      ws.onmessage=(e)=>{
        const ev=JSON.parse(e.data);
        setHazards(p=>[ev,...p.slice(0,49)]);
        setFeed(p=>[ev,...p.slice(0,29)]);
        setFlash(ev);setTimeout(()=>setFlash(null),5000);
        fetch(`${BACKEND}/stats`).then(r=>r.json()).then(setStats).catch(()=>{});
      };
    }
    connect();
    return()=>wsRef.current?.close();
  },[booted]);

  const ago=(iso)=>{const s=Math.floor((Date.now()-new Date(iso))/1000);return s<60?`${s}s ago`:`${Math.floor(s/60)}m ago`;};

  /* ── BOOT SCREEN ── */
  if(!booted) return(
    <div style={{height:"100vh",background:"#020817",display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",fontFamily:"'DM Mono',monospace"}}>
      <style>{`@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@700;800&display=swap');@keyframes blink{0%,100%{opacity:1}50%{opacity:0}}`}</style>
      <div style={{fontFamily:"'Syne',sans-serif",fontWeight:800,fontSize:64,letterSpacing:"0.15em",background:"linear-gradient(135deg,#FACC15,#FB923C)",WebkitBackgroundClip:"text",WebkitTextFillColor:"transparent",marginBottom:6,lineHeight:1}}>VIGILCLOUD</div>
      <div style={{fontSize:11,letterSpacing:"0.4em",color:"#1E3A5F",marginBottom:48}}>HIGHWAY INTELLIGENCE · NH-44</div>
      <div style={{width:480,background:"#0D1B2A",border:"1px solid #1E3A5F",borderRadius:12,padding:"22px 26px"}}>
        {BOOT.slice(0,bootIdx).map((l,i)=>(
          <div key={i} style={{fontSize:12,color:i===bootIdx-1?"#FACC15":"#1E4A6E",marginBottom:8,letterSpacing:"0.04em"}}>{l}</div>
        ))}
        {bootIdx<BOOT.length&&<span style={{display:"inline-block",width:8,height:14,background:"#FACC15",verticalAlign:"middle",animation:"blink 0.7s infinite"}}/>}
      </div>
      <div style={{width:480,height:3,background:"#0D1B2A",borderRadius:99,marginTop:14,overflow:"hidden"}}>
        <div style={{width:`${bootIdx/BOOT.length*100}%`,height:"100%",background:"linear-gradient(90deg,#FACC15,#FB923C)",boxShadow:"0 0 12px #FACC15",transition:"width 0.32s"}}/>
      </div>
    </div>
  );

  /* ── MAIN DASHBOARD ── */
  return(
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@700;800&display=swap');
        *{margin:0;padding:0;box-sizing:border-box;}
        body{background:#020817;overflow:hidden;}
        /* Use a LIGHT map style so you can actually see roads */
        .leaflet-container{background:#0D1B2A!important;}
        .leaflet-tile{filter:invert(1) hue-rotate(200deg) brightness(0.55) saturate(1.8) contrast(1.1);}
        .leaflet-popup-content-wrapper,.leaflet-popup-tip{background:transparent!important;border:none!important;box-shadow:none!important;padding:0!important;}
        .leaflet-popup-content{margin:0!important;}
        .leaflet-control-zoom a{background:#0D1B2A!important;color:#FACC15!important;border:1px solid #1E3A5F!important;font-size:16px!important;}
        ::-webkit-scrollbar{width:3px;}::-webkit-scrollbar-thumb{background:#FACC1533;border-radius:2px;}
        @keyframes pulse{0%,100%{opacity:1}50%{opacity:0.2}}
        @keyframes slideIn{from{opacity:0;transform:translateX(18px)}to{opacity:1;transform:translateX(0)}}
        @keyframes fadeUp{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
        @keyframes glow{0%,100%{box-shadow:0 0 8px #FACC1544}50%{box-shadow:0 0 20px #FACC15}}
      `}</style>

      <div style={{display:"flex",flexDirection:"column",height:"100vh",fontFamily:"'DM Mono',monospace"}}>

        {/* ── TOP BAR ── */}
        <div style={{height:60,background:"#020817",borderBottom:"1px solid #1E3A5F",display:"flex",alignItems:"center",padding:"0 22px",gap:18,flexShrink:0,position:"relative"}}>
          <div style={{position:"absolute",bottom:0,left:0,right:0,height:1,background:"linear-gradient(90deg,transparent,#FACC1566,transparent)"}}/>

          {/* Logo */}
          <div style={{display:"flex",alignItems:"center",gap:10,marginRight:4}}>
            <div style={{width:38,height:38,border:"2px solid #FACC15",borderRadius:10,display:"flex",alignItems:"center",justifyContent:"center",fontSize:18,background:"#FACC1511",animation:"glow 3s infinite"}}>⚡</div>
            <div>
              <div style={{fontFamily:"'Syne',sans-serif",fontWeight:800,fontSize:18,letterSpacing:"0.12em",background:"linear-gradient(135deg,#FACC15,#FB923C)",WebkitBackgroundClip:"text",WebkitTextFillColor:"transparent",lineHeight:1.1}}>VIGILCLOUD</div>
              <div style={{fontSize:8,letterSpacing:"0.25em",color:"#1E3A5F",marginTop:1}}>NHAI INTELLIGENCE</div>
            </div>
          </div>

          {/* Route */}
          <div style={{padding:"5px 14px",border:"1px solid #1E3A5F",borderRadius:6,fontSize:10,color:"#FACC15",letterSpacing:"0.12em",background:"#FACC1508"}}>NH-44 · DELHI → AGRA · 235 KM</div>

          <div style={{flex:1}}/>

          {/* Stat chips */}
          {[
            {label:"POTHOLES",k:"pothole",         c:"#FACC15"},
            {label:"FOG",     k:"fog",             c:"#38BDF8"},
            {label:"FIRE",    k:"fire",            c:"#FB923C"},
            {label:"STALLED", k:"stalled_vehicle", c:"#A78BFA"},
          ].map(({label,k,c})=>(
            <div key={k} style={{display:"flex",alignItems:"center",gap:10,padding:"6px 16px",border:`1px solid ${c}33`,borderRadius:8,background:`${c}0a`}}>
              <div style={{fontFamily:"'Syne',sans-serif",fontWeight:800,fontSize:22,color:c,lineHeight:1,textShadow:`0 0 16px ${c}88`}}>{stats.by_type?.[k]||0}</div>
              <div style={{fontSize:8,color:"#334155",letterSpacing:"0.12em"}}>{label}</div>
            </div>
          ))}

          {/* Total */}
          <div style={{display:"flex",alignItems:"center",gap:10,padding:"6px 18px",border:"1px solid #FACC1555",borderRadius:8,background:"#FACC1508"}}>
            <div style={{fontFamily:"'Syne',sans-serif",fontWeight:800,fontSize:22,color:"#F1F5F9",lineHeight:1}}>{stats.total_confirmed}</div>
            <div style={{fontSize:8,color:"#475569",letterSpacing:"0.12em"}}>TOTAL</div>
          </div>

          {/* Time */}
          <div style={{fontSize:14,color:"#334155",letterSpacing:"0.08em",padding:"0 12px",borderLeft:"1px solid #1E3A5F"}}>{time}</div>

          {/* Status */}
          <div style={{display:"flex",alignItems:"center",gap:7,padding:"5px 12px",border:`1px solid ${conn?"#FACC1533":"#FB923C33"}`,borderRadius:6}}>
            <div style={{width:7,height:7,borderRadius:"50%",background:conn?"#FACC15":"#FB923C",boxShadow:`0 0 10px ${conn?"#FACC15":"#FB923C"}`,animation:"pulse 1.5s infinite"}}/>
            <span style={{fontSize:10,color:conn?"#FACC15":"#FB923C",letterSpacing:"0.1em"}}>{conn?"LIVE":"SYNC"}</span>
          </div>
        </div>

        {/* ── FLASH ALERT ── */}
        {flash&&(()=>{
          const info=HAZARD[flash.hazard_type]||HAZARD.unknown;
          return(
            <div style={{background:`linear-gradient(90deg,${info.color}1a,${info.color}08,transparent)`,borderBottom:`2px solid ${info.color}99`,padding:"8px 22px",display:"flex",alignItems:"center",gap:14,flexShrink:0,animation:"fadeUp 0.2s ease"}}>
              <div style={{width:9,height:9,borderRadius:"50%",background:info.color,boxShadow:`0 0 14px ${info.color}`,animation:"pulse 0.5s infinite"}}/>
              <span style={{fontSize:10,fontWeight:700,letterSpacing:"0.18em",color:info.color}}>ALERT</span>
              <span style={{fontSize:12,color:"#CBD5E1"}}>{info.icon} {info.label} · <strong style={{color:info.color}}>NODE {flash.node_id}</strong> · <strong style={{color:info.color}}>{(flash.confidence*100).toFixed(0)}%</strong> CONFIDENCE</span>
              <div style={{flex:1}}/>
              <span style={{fontSize:10,color:info.color,opacity:0.7,letterSpacing:"0.1em"}}>▶ DRIVER ALERT DISPATCHED</span>
            </div>
          );
        })()}

        {/* ── BODY ── */}
        <div style={{display:"flex",flex:1,overflow:"hidden"}}>

          {/* MAP */}
          <div style={{flex:1,position:"relative"}}>
            {/* subtle grid */}
            <div style={{position:"absolute",inset:0,backgroundImage:"linear-gradient(rgba(250,204,21,0.03) 1px,transparent 1px),linear-gradient(90deg,rgba(250,204,21,0.03) 1px,transparent 1px)",backgroundSize:"56px 56px",pointerEvents:"none",zIndex:10}}/>
            {/* soft vignette */}
            <div style={{position:"absolute",inset:0,background:"radial-gradient(ellipse at center,transparent 40%,#02081799 100%)",pointerEvents:"none",zIndex:10}}/>
            {/* corner brackets */}
            {[[{top:14,left:14},{borderTop:"1.5px solid #FACC1566",borderLeft:"1.5px solid #FACC1566"}],[{top:14,right:14},{borderTop:"1.5px solid #FACC1566",borderRight:"1.5px solid #FACC1566"}],[{bottom:14,left:14},{borderBottom:"1.5px solid #FACC1566",borderLeft:"1.5px solid #FACC1566"}],[{bottom:14,right:14},{borderBottom:"1.5px solid #FACC1566",borderRight:"1.5px solid #FACC1566"}]].map(([pos,brd],i)=>(
              <div key={i} style={{position:"absolute",width:24,height:24,...pos,...brd,zIndex:20}}/>
            ))}
            <MapContainer center={[27.8,77.05]} zoom={9} style={{height:"100%",width:"100%"}}>
              <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution=""/>
              {hazards.map((h,i)=><GlowPin key={i} h={h}/>)}
            </MapContainer>
            <div style={{position:"absolute",top:18,left:18,zIndex:20,fontSize:9,color:"#FACC1566",letterSpacing:"0.18em"}}>NH-44 · LIVE SURVEILLANCE</div>
            <div style={{position:"absolute",bottom:18,left:18,zIndex:20,fontSize:9,color:"#1E3A5F",letterSpacing:"0.12em"}}>● {hazards.length} INCIDENTS · HOVER PINS FOR DETAIL</div>
          </div>

          {/* SIDEBAR */}
          <div style={{width:300,background:"#020817",borderLeft:"1px solid #1E3A5F",display:"flex",flexDirection:"column",overflow:"hidden"}}>

            <div style={{padding:"14px 18px",borderBottom:"1px solid #1E3A5F",display:"flex",alignItems:"center",justifyContent:"space-between",background:"#0D1B2A"}}>
              <span style={{fontFamily:"'Syne',sans-serif",fontWeight:800,fontSize:13,letterSpacing:"0.16em",color:"#F1F5F9"}}>LIVE FEED</span>
              <div style={{display:"flex",alignItems:"center",gap:6}}>
                <div style={{width:6,height:6,borderRadius:"50%",background:"#FACC15",animation:"pulse 1.5s infinite",boxShadow:"0 0 8px #FACC15"}}/>
                <span style={{fontSize:10,color:"#FACC15",letterSpacing:"0.1em"}}>{feed.length} EVENTS</span>
              </div>
            </div>

            <div style={{flex:1,overflowY:"auto"}}>
              {feed.length===0?(
                <div style={{padding:"60px 20px",textAlign:"center"}}>
                  <div style={{fontSize:30,marginBottom:14,opacity:0.3}}>📡</div>
                  <div style={{fontSize:10,color:"#1E3A5F",letterSpacing:"0.12em",lineHeight:2.2}}>AWAITING SENSOR DATA<br/>RUN SIMULATOR.PY<br/>TO BEGIN</div>
                </div>
              ):feed.map((h,i)=>{
                const info=HAZARD[h.hazard_type]||HAZARD.unknown;
                return(
                  <div key={i} style={{padding:"12px 16px",borderBottom:"1px solid #0D1B2A",display:"flex",gap:12,animation:i===0?"slideIn 0.3s ease":"none",background:i===0?"#0D1B2A":"transparent",position:"relative"}}>
                    {i===0&&<div style={{position:"absolute",left:0,top:0,bottom:0,width:3,background:info.color,boxShadow:`0 0 8px ${info.color}`}}/>}
                    <div style={{width:40,height:40,border:`1px solid ${info.color}44`,borderRadius:10,display:"flex",alignItems:"center",justifyContent:"center",fontSize:18,flexShrink:0,background:`${info.color}0d`}}>{info.icon}</div>
                    <div style={{flex:1,minWidth:0}}>
                      <div style={{fontFamily:"'Syne',sans-serif",fontWeight:800,fontSize:12,color:info.color,letterSpacing:"0.1em"}}>{info.label}</div>
                      <div style={{fontSize:10,color:"#334155",marginTop:2}}>NODE {h.node_id}</div>
                      <div style={{display:"flex",alignItems:"center",gap:8,marginTop:6}}>
                        <div style={{flex:1,height:3,background:"#0D1B2A",borderRadius:99}}>
                          <div style={{width:`${h.confidence*100}%`,height:"100%",background:info.color,borderRadius:99,boxShadow:i===0?`0 0 6px ${info.color}`:""}}/>
                        </div>
                        <span style={{fontSize:10,color:i===0?info.color:"#334155",minWidth:32}}>{(h.confidence*100).toFixed(0)}%</span>
                      </div>
                    </div>
                    <span style={{fontSize:9,color:"#1E3A5F",alignSelf:"flex-start",whiteSpace:"nowrap"}}>{h.timestamp?ago(h.timestamp):"now"}</span>
                  </div>
                );
              })}
            </div>

            {/* System panel */}
            <div style={{padding:"14px 18px",borderTop:"1px solid #1E3A5F",background:"#0D1B2A"}}>
              <div style={{fontSize:9,color:"#1E3A5F",letterSpacing:"0.18em",marginBottom:10}}>SYSTEM STATUS</div>
              {[
                {k:"BACKEND",   v:"ONLINE",             c:"#4ADE80"},
                {k:"ML ENGINE", v:"ADD BEST.PT",        c:"#FACC15"},
                {k:"NODES",     v:"10 / 10 ACTIVE",     c:"#4ADE80"},
                {k:"WEBSOCKET", v:conn?"CONNECTED":"RECONNECTING", c:conn?"#4ADE80":"#FB923C"},
              ].map(({k,v,c})=>(
                <div key={k} style={{display:"flex",justifyContent:"space-between",marginBottom:7}}>
                  <span style={{fontSize:9,color:"#1E3A5F",letterSpacing:"0.08em"}}>{k}</span>
                  <span style={{fontSize:9,color:c,letterSpacing:"0.06em"}}>● {v}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}