"""Self-contained educational LEO signal-flow animation."""
import streamlit.components.v1 as components


def show_leo_explainer():
    components.html('''<!doctype html><html><head><style>
body{margin:0;background:#071322;color:#e5eefb;font:15px system-ui}main{padding:20px}button,select{background:#18344f;color:white;border:1px solid #456480;border-radius:8px;padding:10px;margin:4px;cursor:pointer}button:focus{outline:2px solid #7dd3fc}.stage{font-size:20px;font-weight:700}p{line-height:1.5;color:#c2d3e7}svg{width:100%;max-height:400px}text{fill:#e5eefb;font-size:16px}.link{stroke-width:3;stroke-dasharray:8 7;opacity:.35}.active{opacity:1;stroke-width:5}#packet{filter:drop-shadow(0 0 6px white)}
</style></head><body><main>
<div><button id="play">▶ Play</button><button id="step">Next step →</button><button id="reset">Reset</button><label>Speed <select id="speed"><option value="1">Normal</option><option value="0.5">Slow</option><option value="2">Fast</option></select></label></div>
<svg viewBox="0 0 1000 470" role="img" aria-label="Animated LEO satellites linking a home terminal to a ground station">
<defs><g id="sat"><rect x="-48" y="-13" width="30" height="26" fill="#4197d6" stroke="#b3e2ff"/><rect x="18" y="-13" width="30" height="26" fill="#4197d6" stroke="#b3e2ff"/><rect x="-16" y="-23" width="32" height="46" rx="8" fill="#c4d3e1"/><circle r="6" fill="#fbbf24"/></g></defs>
<path d="M40 160 Q500 -30 960 160" fill="none" stroke="#698099" stroke-dasharray="10 8"/>
<text x="360" y="30">Satellites move along their orbits →</text>
<ellipse cx="220" cy="397" rx="180" ry="42" fill="#2494c8" opacity=".2"/><ellipse cx="770" cy="397" rx="190" ry="42" fill="#31c799" opacity=".2"/>
<path id="beamA" fill="#2494c8" opacity=".12"/><path id="beamB" fill="#31c799" opacity=".12"/>
<path id="uplink" class="link" stroke="#38bdf8" fill="none"/><path id="relay" class="link" stroke="#fbbf24" fill="none"/><path id="downlink" class="link" stroke="#34d399" fill="none"/>
<use id="satA" href="#sat"/><use id="satB" href="#sat"/><use id="satC" href="#sat"/>
<text x="110" y="255" fill="#38bdf8">Ground-station link</text><text x="380" y="105">Intersatellite link</text><text x="730" y="260">User-terminal link</text>
<path d="M180 340 Q220 400 260 340 L220 365 Z" fill="#a6c7dd" stroke="white"/><path d="M220 365 L220 400 M200 400 L240 400" stroke="white" stroke-width="5"/>
<text x="140" y="440">Ground station / internet</text>
<path d="M725 350 L770 310 L815 350 V400 H725 Z" fill="#398bb3" stroke="#b3e2ff"/><rect x="760" y="365" width="20" height="35" fill="#071322"/><path d="M700 355 Q680 380 665 355 L685 365 L685 395" stroke="white" fill="#a6c7dd" stroke-width="3"/>
<text x="660" y="440">Home + user terminal</text>
<circle id="packet" r="8" fill="white"/>
</svg>
<div class="stage" id="title" aria-live="polite"></div><p id="explanation"></p>
<p style="font-size:12px">Educational illustration: distances, coverage cones, movement, and packet timing are not to scale. Real connections depend on visibility, routing and radio conditions. Use Earth view for calculated orbital positions.</p>
</main><script>
const phases=[['1 · Home sends a request','Your terminal sends a radio signal up to a satellite in range.'],['2 · Satellites relay the request','An intersatellite link can carry the request to a satellite that can reach a ground station. Not every route needs this hop.'],['3 · Ground station reaches the internet','The satellite sends the request down to the ground station, which connects to the internet.'],['4 · The reply travels back up','The internet response travels from the ground station up to a satellite.'],['5 · Relay toward your home','The response is relayed across the satellite link toward the satellite serving your terminal.'],['6 · Your terminal receives the reply','The satellite sends the response down to your terminal and home network.'],['7 · Handover keeps the connection going','As one satellite moves out of range, the terminal switches to another satellite. The next request uses the new satellite.']];
let phase=0,progress=0,playing=false,last=0,orbit=0,switched=false;
const el=id=>document.getElementById(id);function pos(x){return [x,70+0.0004*(x-500)**2]};
function draw(){let a=pos(240+orbit),b=pos(650+orbit),c=pos(840+orbit);const user=switched?c:b;
for(const [id,p] of [['satA',a],['satB',b],['satC',c]])el(id).setAttribute('transform',`translate(${p[0]},${p[1]})`);
const line=(p,q)=>`M${p[0]} ${p[1]} L${q[0]} ${q[1]}`;
el('uplink').setAttribute('d',line([220,350],a));el('relay').setAttribute('d',line(a,user));el('downlink').setAttribute('d',line(user,[685,350]));
el('beamA').setAttribute('d',`M40 397 L${a[0]} ${a[1]} L400 397 Z`);el('beamB').setAttribute('d',`M580 397 L${user[0]} ${user[1]} L960 397 Z`);
const paths=[[[685,350],user],[user,a],[a,[220,350]],[[220,350],a],[a,user],[user,[685,350]]];const ids=['downlink','relay','uplink','uplink','relay','downlink'];
for(const id of ['uplink','relay','downlink'])el(id).setAttribute('class','link'+(ids[phase]===id?' active':''));
el('packet').style.display=phase===6?'none':'';if(phase<6){const [p,q]=paths[phase];el('packet').setAttribute('cx',p[0]+(q[0]-p[0])*progress);el('packet').setAttribute('cy',p[1]+(q[1]-p[1])*progress)}
el('title').textContent=phases[phase][0];el('explanation').textContent=phases[phase][1];}
function next(){if(phase===5)switched=!switched;phase=(phase+1)%7;progress=0;draw()}
el('play').onclick=()=>{playing=!playing;el('play').textContent=playing?'Pause':'▶ Play'};
el('step').onclick=()=>{playing=false;el('play').textContent='▶ Play';next()};el('reset').onclick=()=>{playing=false;phase=0;progress=0;orbit=0;switched=false;el('play').textContent='▶ Play';draw()};
function tick(t){const dt=last?Math.min((t-last)/1000,.1):0;last=t;if(playing){progress+=dt*Number(el('speed').value)/2.5;orbit=30*Math.sin(t/12000);if(progress>=1)next();draw()}requestAnimationFrame(tick)}draw();requestAnimationFrame(tick);
</script></body></html>''', height=680, scrolling=True)
