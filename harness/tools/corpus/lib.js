window.__H = (function(){
  function rnd(seed){ let s=seed; return function(){ s=(s*1664525+1013904223)>>>0; return s/4294967296; }; }
  function P(x,y,o){ return Object.assign({x:x,y:y,color:'#141414',size:7,erase:false}, o||{}); }
  function mk(runs){
    const f={strokes:[],strokeGroups:[],hold:1}; let t=0;
    runs.forEach(r=>{ if(!r.length) return;
      r.forEach((p,i)=>{ const q=Object.assign({},p); q.t=t; t+=16;
        if(i===0) q.start=true; else delete q.start; f.strokes.push(q); });
      f.strokeGroups.push(r.length); });
    return f;
  }
  function circle(cx,cy,r,n,a0,dir,o){
    n=n||40; a0=a0||0; dir=dir===undefined?1:dir; const out=[];
    for(let i=0;i<=n;i++){ const a=a0+dir*2*Math.PI*i/n;
      out.push(P(cx+r*Math.cos(a), cy+r*Math.sin(a), o)); }
    return out;
  }
  function ellipse(cx,cy,rx,ry,n,o){ n=n||40; const out=[];
    for(let i=0;i<=n;i++){ const a=2*Math.PI*i/n; out.push(P(cx+rx*Math.cos(a), cy+ry*Math.sin(a), o)); }
    return out; }
  function line(x1,y1,x2,y2,n,o){ n=n||20; const out=[];
    for(let i=0;i<=n;i++){ const u=i/n; out.push(P(x1+(x2-x1)*u, y1+(y2-y1)*u, o)); } return out; }
  function poly(pts,n,o){ // pts = [[x,y],...] open polyline, resampled per segment
    const out=[]; for(let s=0;s<pts.length-1;s++){ const [a,b]=[pts[s],pts[s+1]];
      const k = n||10; for(let i=(s?1:0);i<=k;i++){ const u=i/k;
        out.push(P(a[0]+(b[0]-a[0])*u, a[1]+(b[1]-a[1])*u, o)); } } return out; }
  function arcSeg(cx,cy,r,a0,a1,n,o){ n=n||20; const out=[];
    for(let i=0;i<=n;i++){ const a=a0+(a1-a0)*i/n; out.push(P(cx+r*Math.cos(a), cy+r*Math.sin(a), o)); } return out; }
  function rot(run, cx, cy, ang){ return run.map(p=>{ const dx=p.x-cx, dy=p.y-cy;
    return Object.assign({},p,{x:cx+dx*Math.cos(ang)-dy*Math.sin(ang), y:cy+dx*Math.sin(ang)+dy*Math.cos(ang)}); }); }
  function tr(run,dx,dy){ return run.map(p=>Object.assign({},p,{x:p.x+dx,y:p.y+dy})); }
  function sc(run,cx,cy,k){ return run.map(p=>Object.assign({},p,{x:cx+(p.x-cx)*k, y:cy+(p.y-cy)*k})); }
  function jit(run, amt, seed){ const r=rnd(seed||7); return run.map(p=>Object.assign({},p,
    {x:p.x+(r()-0.5)*amt, y:p.y+(r()-0.5)*amt})); }
  function noisyBlob(cx,cy,r,n,seed,wob){ const rr=rnd(seed); const out=[]; n=n||48;
    const ph=[]; for(let k=0;k<5;k++) ph.push(rr()*6.283);
    for(let i=0;i<=n;i++){ const a=2*Math.PI*i/n;
      let d=r; for(let k=0;k<5;k++) d += (wob||10)*Math.sin((k+2)*a+ph[k])/(k+1);
      d += (rr()-0.5)*3;
      out.push(P(cx+d*Math.cos(a), cy+d*Math.sin(a))); } return out; }
  return {P:P,mk:mk,circle:circle,ellipse:ellipse,line:line,poly:poly,arcSeg:arcSeg,
          rot:rot,tr:tr,sc:sc,jit:jit,noisyBlob:noisyBlob,rnd:rnd};
})();
