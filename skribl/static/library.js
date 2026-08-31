/* ============================================================================
   A tiny Skribl replay engine. Each "skribl" is a list of timed strokes in a
   0..1 box; the player reveals them over time (the app's draw-on replay), and
   the cards render the finished drawing. Riso inks on a dark ground, per the
   app's drawing palette — the artwork never follows the chrome theme.
   ========================================================================== */
const INK = { pink:'#ff48b0', orange:'#ff6c2f', yellow:'#ffe800', green:'#00a95c', blue:'#0078bf', white:'#f4f4ff' };

/* deterministic per-seed rng so a drawing looks the same every render */
function rng(seed){ let s = seed>>>0 || 1; return () => { s ^= s<<13; s^=s>>>17; s^=s<<5; s>>>=0; return s/4294967296; }; }

/* stroke helpers operate in 0..1 space; return {color,width,pts:[[x,y]..]} */
const P = (...pts) => pts;
function circle(cx,cy,r,n=40){ const a=[]; for(let i=0;i<=n;i++){const t=i/n*Math.PI*2; a.push([cx+Math.cos(t)*r, cy+Math.sin(t)*r*1]);} return a; }
function arc(cx,cy,r,a0,a1,n=24){ const a=[]; for(let i=0;i<=n;i++){const t=a0+(a1-a0)*i/n; a.push([cx+Math.cos(t)*r, cy+Math.sin(t)*r]);} return a; }
const S = (color,width,pts) => ({color,width,pts});

/* ---- the motifs. Each returns an array of strokes. Bold, few, recognisable. -- */
const MOTIFS = {
  bolt(){ // pirate frequency — bolt in a ring
    return [
      S(INK.blue,3.4, circle(.5,.5,.40)),
      S(INK.pink,1.8, circle(.512,.512,.40)),
      S(INK.white,4.6, P([.56,.14],[.40,.5],[.52,.5],[.44,.86],[.66,.44],[.54,.44],[.56,.14])),
      S(INK.yellow,1.6, P([.40,.30],[.60,.30])), S(INK.yellow,1.6, P([.38,.42],[.58,.42])),
      S(INK.orange,1.4, arc(.5,.5,.30,-2.4,-0.7)),
    ];
  },
  cassette(){
    return [
      S(INK.orange,3.6, P([.16,.26],[.84,.26],[.86,.74],[.14,.74],[.16,.26])),
      S(INK.white,2.4, P([.24,.36],[.76,.36],[.76,.56],[.24,.56],[.24,.36])),
      S(INK.blue,3.2, circle(.37,.46,.055,20)), S(INK.blue,3.2, circle(.63,.46,.055,20)),
      S(INK.pink,2.0, P([.30,.66],[.70,.66])),
      S(INK.yellow,2.0, P([.30,.30],[.34,.30])),
    ];
  },
  smiley(){
    return [
      S(INK.yellow,4.4, circle(.5,.5,.36)),
      S(INK.white,4.0, P([.34,.40],[.40,.46])), S(INK.white,4.0, P([.40,.40],[.34,.46])),
      S(INK.white,4.0, P([.60,.40],[.66,.46])), S(INK.white,4.0, P([.66,.40],[.60,.46])),
      S(INK.pink,4.4, arc(.5,.50,.20,0.5,2.64)),
    ];
  },
  eye(){
    return [
      S(INK.white,3.4, P([.18,.5],[.5,.32],[.82,.5],[.5,.68],[.18,.5])),
      S(INK.blue,3.4, circle(.5,.5,.11,26)),
      S(INK.pink,5.0, circle(.5,.5,.045,16)),
      ...[...Array(9)].map((_,i)=>{const a=i/9*Math.PI*2; return S(INK.yellow,1.4, P([.5+Math.cos(a)*.30,.5+Math.sin(a)*.30],[.5+Math.cos(a)*.40,.5+Math.sin(a)*.40]));}),
    ];
  },
  boombox(){
    return [
      S(INK.white,3.4, P([.12,.28],[.88,.28],[.88,.76],[.12,.76],[.12,.28])),
      S(INK.blue,3.0, circle(.32,.54,.11,24)), S(INK.pink,3.0, circle(.68,.54,.11,24)),
      S(INK.orange,2.0, circle(.32,.54,.04,14)), S(INK.orange,2.0, circle(.68,.54,.04,14)),
      S(INK.yellow,2.4, P([.44,.40],[.56,.40])),
      S(INK.green,3.0, P([.30,.20],[.5,.13],[.70,.20])),
    ];
  },
  moth(){
    return [
      S(INK.white,2.6, P([.5,.24],[.5,.78])),
      S(INK.pink,3.2, P([.5,.34],[.20,.24],[.14,.5],[.30,.62],[.5,.5])),
      S(INK.pink,3.2, P([.5,.34],[.80,.24],[.86,.5],[.70,.62],[.5,.5])),
      S(INK.blue,2.4, P([.5,.5],[.26,.72],[.40,.80],[.5,.66])),
      S(INK.blue,2.4, P([.5,.5],[.74,.72],[.60,.80],[.5,.66])),
      S(INK.yellow,2.2, P([.5,.24],[.44,.15])), S(INK.yellow,2.2, P([.5,.24],[.56,.15])),
    ];
  },
  hand(){
    return [
      S(INK.white,3.6, P([.34,.86],[.34,.44],[.30,.30],[.36,.30],[.40,.46])),
      S(INK.white,3.6, P([.40,.46],[.42,.16],[.49,.16],[.50,.48])),
      S(INK.white,3.6, P([.50,.48],[.54,.14],[.61,.14],[.60,.48])),
      S(INK.white,3.6, P([.60,.48],[.66,.24],[.72,.26],[.66,.52])),
      S(INK.white,3.6, P([.34,.56],[.24,.50],[.22,.58],[.34,.66])),
      S(INK.pink,3.4, P([.34,.86],[.66,.86],[.68,.60])),
      S(INK.yellow,1.8, arc(.5,.48,.42,-2.5,-0.6)),
    ];
  },
  stack(){ // sound system speaker stack
    return [
      S(INK.white,3.2, P([.28,.10],[.72,.10],[.72,.90],[.28,.90],[.28,.10])),
      S(INK.blue,3.0, circle(.5,.28,.11,24)),
      S(INK.pink,3.0, circle(.5,.54,.13,26)),
      S(INK.orange,2.2, circle(.5,.76,.075,20)),
      S(INK.yellow,1.8, P([.28,.40],[.72,.40])), S(INK.yellow,1.8, P([.28,.66],[.72,.66])),
    ];
  },
  flower(){
    return [
      ...[...Array(6)].map((_,i)=>{const a=i/6*Math.PI*2; return S(INK.pink,3.4, P([.5,.5],[.5+Math.cos(a)*.34,.5+Math.sin(a)*.34],[.5+Math.cos(a+.5)*.18,.5+Math.sin(a+.5)*.18],[.5,.5]));}),
      S(INK.yellow,4.0, circle(.5,.5,.09,22)),
      S(INK.green,3.2, P([.5,.59],[.52,.9])),
      S(INK.green,2.4, P([.52,.74],[.66,.68])),
    ];
  },
  tag(){ // wildstyle scribble tag
    return [
      S(INK.orange,5.0, P([.14,.62],[.22,.36],[.30,.62],[.34,.40],[.30,.66],[.44,.34],[.42,.66])),
      S(INK.orange,5.0, P([.42,.66],[.54,.36],[.56,.64],[.66,.36],[.64,.66],[.80,.34])),
      S(INK.pink,2.4, P([.16,.68],[.82,.40])),
      S(INK.white,1.8, P([.20,.30],[.26,.26])), S(INK.white,1.8, P([.70,.30],[.76,.26])),
      S(INK.blue,2.0, P([.12,.74],[.86,.74])),
    ];
  },
  static(){ // glitch TV
    return [
      S(INK.white,3.2, P([.16,.24],[.84,.24],[.84,.72],[.16,.72],[.16,.24])),
      S(INK.blue,2.2, P([.22,.34],[.78,.34])), S(INK.pink,2.2, P([.22,.44],[.62,.44])),
      S(INK.yellow,2.2, P([.30,.54],[.78,.54])), S(INK.green,2.2, P([.22,.62],[.52,.62])),
      S(INK.white,2.6, P([.44,.72],[.40,.82],[.60,.82],[.56,.72])),
      S(INK.orange,2.4, P([.66,.16],[.78,.08])),
    ];
  },
  wave(){ // waveform
    return [
      ...[...Array(11)].map((_,i)=>{ const x=.12+i*.076; const h=.10+((i*37)%9)/9*.30; return S([INK.pink,INK.blue,INK.yellow,INK.green][i%4],4.2,P([x,.5-h],[x,.5+h])); }),
      S(INK.white,1.6, P([.08,.5],[.92,.5])),
    ];
  },
};

const GROUNDS = ['#14122b','#0f1a1e','#1a1020','#101626','#191322','#0d1712'];

/* ---- render a motif to a canvas, optionally revealing up to progress p(0..1) --*/
function draw(canvas, sk, p){
  const dpr = Math.min(window.devicePixelRatio||1, 2);
  const cw = canvas.clientWidth || canvas.width, ch = canvas.clientHeight || canvas.height;
  if(canvas.width !== Math.round(cw*dpr)){ canvas.width = Math.round(cw*dpr); canvas.height = Math.round(ch*dpr); }
  const ctx = canvas.getContext('2d');
  ctx.setTransform(dpr,0,0,dpr,0,0);
  ctx.fillStyle = sk.ground; ctx.fillRect(0,0,cw,ch);
  ctx.lineCap='round'; ctx.lineJoin='round';
  const R = rng(sk.seed);
  const jit = () => (R()-.5)* (cw*0.006);
  const strokes = sk.strokes;
  // total point budget for progress
  const total = strokes.reduce((a,s)=>a+s.pts.length,0);
  let seen = 0, lastPt = null;
  const target = p==null ? total : Math.max(1, Math.floor(total*p));
  for(const s of strokes){
    ctx.strokeStyle = s.color; ctx.lineWidth = s.width * (cw/220);
    ctx.beginPath();
    for(let i=0;i<s.pts.length;i++){
      if(seen>=target){ break; }
      const x = s.pts[i][0]*cw + jit(), y = s.pts[i][1]*ch + jit();
      if(i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
      lastPt = [x,y]; seen++;
    }
    ctx.stroke();
    if(seen>=target) break;
  }
  return lastPt;  // for the nib
}

/* ---- the library data: real-looking skribls -------------------------------*/
const RAW = [
  ['Pirate Frequency','bolt','pad',41,null,'2d'],
  ['3AM Transmission','wave','flip',12,24,'4d'],
  ['Acid Regular','smiley','pad',18,null,'6d'],
  ['Dubplate','cassette','pad',33,null,'1w'],
  ['Third Eye Open','eye','flip',9,18,'1w'],
  ['Blockparty','boombox','pad',52,null,'2w'],
  ['Nightmoth','moth','flip',7,14,'2w'],
  ['Respect','hand','pad',28,null,'3w'],
  ['Soundsystem','stack','flip',15,30,'3w'],
  ['Bloom','flower','pad',22,null,'1mo'],
  ['Untitled Tag','tag','pad',19,null,'1mo'],
  ['No Signal','static','flip',6,12,'2mo'],
];
let ID = 0;
const SKRIBLS = RAW.map((r,i) => ({
  id:'sk'+(ID++), title:r[0], motif:r[1], kind:r[2], dur:r[3], pages:r[4], date:r[5],
  seed: (i*2654435761)>>>0, ground: GROUNDS[i%GROUNDS.length],
  strokes: MOTIFS[r[1]](),
}));

/* ---- icons ---------------------------------------------------------------*/
const IC_PAD = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3.5a2.1 2.1 0 0 1 3 3L8.5 18 4 20l2-4.5z"/></svg>';
const IC_FLIP = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M12 6.5C9.5 4.9 6.4 4.6 3 5.2v13c3.4-.6 6.5-.3 9 1.3 2.5-1.6 5.6-1.9 9-1.3v-13c-3.4-.6-6.5-.3-9 1.3z"/><path d="M12 6.5v13.3"/></svg>';
const fmt = s => Math.floor(s/60)+':'+String(s%60).padStart(2,'0');
const metaLine = sk => sk.kind==='flip' ? (sk.pages+' pages · '+sk.dur+' fps') : ('plays '+fmt(sk.dur));

/* ---- build the grid ------------------------------------------------------*/
const grid = document.getElementById('grid');
const cards = new Map();
const PAGE = 4;               // one row; the rest is behind a More button
let visible = PAGE;
const moreWrap = document.getElementById('moreWrap');
function buildGrid(){
  grid.innerHTML='';
  moreWrap.innerHTML='';
  cards.clear();
  const q = (document.getElementById('search').value||'').toLowerCase().trim();
  const shown = SKRIBLS.filter(s => (FILTER==='all'||s.kind===FILTER) && (!q || s.title.toLowerCase().includes(q)));
  document.getElementById('libCnt').textContent = shown.length + (shown.length===1?' skribl':' skribls');
  if(!shown.length){ grid.innerHTML = '<div class="empty">No skribls match that.</div>'; return; }
  const page = shown.slice(0, visible);
  for(const sk of page){
    const el = document.createElement('button');
    el.className = 'card' + (sk.id===current.id?' active':'');
    el.innerHTML =
      '<div class="art"><canvas></canvas>'+
        '<span class="badge">'+(sk.kind==='flip'?IC_FLIP:IC_PAD)+(sk.kind==='flip'?'Flip':'Pad')+'</span>'+
        '<span class="playing"><span>Now playing</span></span>'+
      '</div>'+
      '<div class="body"><div class="ct">'+sk.title+'</div>'+
        '<div class="cm"><span class="dur">'+(sk.kind==='flip'?sk.pages+'p':fmt(sk.dur))+'</span><span>·</span><span>'+sk.date+'</span></div>'+
      '</div>';
    el.addEventListener('click', () => load(sk, true));
    grid.appendChild(el);
    cards.set(sk.id, el);
    draw(el.querySelector('canvas'), sk, null);   // static full render
  }
  const remaining = shown.length - page.length;
  if(remaining > 0){
    const btn = document.createElement('button');
    btn.className = 'more';
    btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9l6 6 6-6"/></svg>'
      + 'Show ' + Math.min(PAGE, remaining) + ' more <span class="rem">(' + remaining + ' left)</span>';
    btn.addEventListener('click', () => { visible += PAGE; buildGrid(); });
    moreWrap.appendChild(btn);
  }
}

/* ---- the player ----------------------------------------------------------*/
let current = SKRIBLS[0];
let FILTER = 'all';
let playing = false, raf = null, startT = 0, playDurMs = 0, loop = true;
const stage = document.getElementById('stageCanvas');
const nib = document.getElementById('nib');

function setActiveCard(){
  cards.forEach((el,id)=> el.classList.toggle('active', id===current.id));
}
function load(sk, autoplay){
  current = sk;
  document.getElementById('pTitle').textContent = sk.title;
  const k = document.getElementById('pKind');
  k.className = 'kind '+sk.kind; k.innerHTML = (sk.kind==='flip'?IC_FLIP:IC_PAD)+(sk.kind==='flip'?'Flip':'Pad');
  document.getElementById('pMeta').textContent = metaLine(sk);
  playDurMs = (sk.kind==='flip' ? Math.max(3.2, sk.pages/sk.dur*4) : Math.min(7, Math.max(3.5, sk.dur/8))) * 1000;
  setActiveCard();
  stop(); draw(stage, sk, 1); setScrub(1); setElapsed(1);
  if(autoplay) play();
}
function setScrub(p){ document.getElementById('scrubFill').style.width = (p*100)+'%'; }
function realTotal(sk){ return sk.kind==='flip' ? Math.max(1, Math.round(sk.pages/sk.dur)) : sk.dur; }
function setElapsed(p){
  const T = realTotal(current);
  document.getElementById('tElapsed').textContent = fmt(Math.round(T*p))+' / '+fmt(T);
}
function frame(now){
  const p = Math.min(1, (now-startT)/playDurMs);
  const last = draw(stage, current, p);
  setScrub(p); setElapsed(p);
  if(last){ const wrap = stage.getBoundingClientRect();
    nib.style.opacity = p<1?1:0;
    nib.style.left = (last[0]/ (stage.width/(Math.min(window.devicePixelRatio||1,2))) *100)+'%';
    nib.style.top = (last[1]/ (stage.height/(Math.min(window.devicePixelRatio||1,2))) *100)+'%';
  }
  if(p<1){ raf = requestAnimationFrame(frame); }
  else { nib.style.opacity=0; if(loop){ startT = performance.now(); raf = requestAnimationFrame(frame); } else stop(); }
}
function play(){
  if(playing) return; playing = true; setPlayIcon(true);
  startT = performance.now(); raf = requestAnimationFrame(frame);
}
function stop(){
  playing = false; setPlayIcon(false); nib.style.opacity=0;
  if(raf) cancelAnimationFrame(raf); raf=null;
}
function setPlayIcon(on){
  document.getElementById('playIcon').innerHTML = on
    ? '<path d="M6 5h4v14H6zM14 5h4v14h-4z"/>'
    : '<path d="M8 5v14l11-7z"/>';
  document.getElementById('btnPlay').title = on?'Pause':'Play';
}

/* controls */
document.getElementById('btnPlay').addEventListener('click', ()=> playing?stop():play());
document.getElementById('btnRestart').addEventListener('click', ()=>{ stop(); startT=performance.now(); play(); });
document.getElementById('btnLoop').addEventListener('click', function(){ loop=!loop; this.classList.toggle('on',loop); this.setAttribute('aria-pressed',String(loop)); });
document.getElementById('btnShare').addEventListener('click', function(){ const t=this.title; this.title='Copied link'; setTimeout(()=>this.title=t,1200); });
document.getElementById('scrub').addEventListener('click', (e)=>{ const r=e.currentTarget.getBoundingClientRect(); const p=Math.max(0,Math.min(1,(e.clientX-r.left)/r.width)); stop(); draw(stage,current,p); setScrub(p); setElapsed(p); });
document.querySelectorAll('.chip').forEach(c => c.addEventListener('click', function(){
  document.querySelectorAll('.chip').forEach(x=>x.classList.remove('active')); this.classList.add('active');
  FILTER = this.dataset.filter; visible = PAGE; buildGrid();
}));
document.getElementById('search').addEventListener('input', ()=>{ visible = PAGE; buildGrid(); });
window.addEventListener('resize', ()=>{ drawAvatar(); if(!playing) draw(stage,current,1); cards.forEach((el,id)=>{ const sk=SKRIBLS.find(s=>s.id===id); if(sk) draw(el.querySelector('canvas'),sk,null); }); });

/* avatar — a little skribl of its own */
const AVATAR = {seed:99, ground:'#14122b', strokes: MOTIFS.bolt()};
function drawAvatar(){ draw(document.getElementById('avatarCanvas'), AVATAR, null); }
document.getElementById('statCount').textContent = SKRIBLS.length;

/* boot — draw after a frame so the canvases have their laid-out size */
buildGrid();
load(SKRIBLS[0], false);
requestAnimationFrame(() => {
  drawAvatar();
  draw(stage, current, 1);
  cards.forEach((el,id)=>{ const sk=SKRIBLS.find(s=>s.id===id); if(sk) draw(el.querySelector('canvas'),sk,null); });
});
setElapsed(0); setScrub(0);
