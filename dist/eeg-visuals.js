/* Procedural 3D head and scalp interpolation. No anatomical source localization. */
(() => {
  const head = document.getElementById('headCanvas'), scalp = document.getElementById('scalpCanvas');
  const h = head.getContext('2d'), s = scalp.getContext('2d');
  const positions = {F3:[-.43,-.48],Fz:[0,-.53],F4:[.43,-.48],C3:[-.58,0],Cz:[0,0],C4:[.58,0],P3:[-.43,.48],P4:[.43,.48],FT7:[-.87,-.34],FT8:[.87,-.34],T7:[-.94,0],T8:[.94,0],TP7:[-.86,.32],TP8:[.86,.32],CP1:[-.25,.26],CP2:[.25,.26],P1:[-.24,.5],Pz:[0,.56],P2:[.24,.5],PO3:[-.4,.72],POz:[0,.77],PO4:[.4,.72],O1:[-.3,.88],Oz:[0,.93],O2:[.3,.88]};
  let data = null, frame = 0;
  const reduced = typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;
  const color = v => {
    const stops = [[32,66,158],[22,154,210],[53,226,190],[245,213,90],[247,100,77]];
    const n = Math.max(0,Math.min(1,v))*4, i = Math.min(3,Math.floor(n)), t=n-i;
    return stops[i].map((c,k)=>Math.round(c+(stops[i+1][k]-c)*t));
  };
  function projection(x,y,z,angle) {
    const xx=x*Math.cos(angle)+z*Math.sin(angle), zz=z*Math.cos(angle)-x*Math.sin(angle);
    const yy=y*Math.cos(-.12)-zz*Math.sin(-.12), depth=y*Math.sin(-.12)+zz*Math.cos(-.12);
    const scale=116*3.8/(3.8-depth);
    return [200+xx*scale,158-yy*scale,depth];
  }
  function curve(points,angle,stroke,width=1) {
    h.beginPath(); points.forEach((v,i)=>{const p=projection(...v,angle); i?h.lineTo(p[0],p[1]):h.moveTo(p[0],p[1]);}); h.strokeStyle=stroke;h.lineWidth=width;h.stroke();
  }
  function drawHead(time) {
    const angle=reduced?.38:time*.00024+.38;
    h.clearRect(0,0,400,330);
    const glow=h.createRadialGradient(200,150,25,200,160,160);glow.addColorStop(0,'rgba(28,92,123,.16)');glow.addColorStop(1,'rgba(4,18,31,0)');h.fillStyle=glow;h.fillRect(0,0,400,330);
    const faces=[];
    const surface=(lat,lon,offset=0)=>{
      const y=Math.sin(lat), narrowing=y<-.25?1+(y+.25)*.35:1;
      const x=(.66+offset)*Math.cos(lat)*Math.sin(lon)*narrowing;
      let z=(.73+offset)*Math.cos(lat)*Math.cos(lon);
      if(Math.cos(lon)>.55) {
        // Sculpted brow, recessed eye sockets, nasal bridge, lips and chin.
        const g=(xc,yc,sx,sy)=>Math.exp(-Math.pow((x-xc)/sx,2)-Math.pow((y-yc)/sy,2));
        z+=.27*g(0,-.08,.10,.24)+.07*g(0,.25,.36,.08);
        z-=.08*(g(-.23,.16,.13,.09)+g(.23,.16,.13,.09));
        z+=.045*g(0,-.36,.22,.06)+.06*g(0,-.57,.23,.12);
      }
      return [x,y,z];
    };
    const addFace=(world,fill,stroke)=>{const pts=world.map(v=>projection(...v,angle));faces.push({pts,z:pts.reduce((v,p)=>v+p[2],0)/pts.length,fill,stroke});};
    // White display stand and neck, black collar matching the reference mannequin.
    for(let j=0;j<48;j++){
      const a=j*Math.PI/24,b=(j+1)*Math.PI/24;
      for(const [lo,hi,r,fill] of [[-1.25,-1.13,.42,'#d6e0e5'],[-1.13,-1.02,.33,'#161b22'],[-1.02,-.72,.28,'#dce4e7']])
        addFace([[r*Math.sin(a),lo,r*Math.cos(a)],[r*Math.sin(b),lo,r*Math.cos(b)],[r*Math.sin(b),hi,r*Math.cos(b)],[r*Math.sin(a),hi,r*Math.cos(a)]],fill);
    }
    for(let i=0;i<64;i++)for(let j=0;j<96;j++){
      const lat=-Math.PI/2+i*Math.PI/64,lon=j*Math.PI/48;
      const world=[[lat,lon],[lat+Math.PI/64,lon],[lat+Math.PI/64,lon+Math.PI/48],[lat,lon+Math.PI/48]].map(([a,b])=>surface(a,b));
      const center=surface(lat+Math.PI/128,lon+Math.PI/96);
      // Open forehead/face; fitted cap covers crown, sides and occiput.
      const front=Math.max(0,Math.cos(lon+Math.PI/96));
      const isCap=center[1]>(-.08+.54*front**3);
      const u=world[1].map((v,k)=>v-world[0][k]),v=world[3].map((v,k)=>v-world[0][k]);
      let normal=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];
      if(normal.reduce((a,n,k)=>a+n*center[k],0)<0)normal=normal.map(n=>-n);
      const length=Math.hypot(...normal)||1;normal=normal.map(n=>n/length);
      const nx=normal[0]*Math.cos(angle)+normal[2]*Math.sin(angle),nz=normal[2]*Math.cos(angle)-normal[0]*Math.sin(angle);
      const light=.22+.78*Math.max(0,-.45*nx+.45*normal[1]+.77*nz);
      const base=isCap?[13,17,23]:[118,132,142], gain=isCap?16:112;
      const rgb=base.map(v=>Math.min(248,Math.round(v+gain*light)));
      const fill=`rgb(${rgb.join(',')})`;
      addFace(world,fill,fill);
      faces[faces.length-1].cap=isCap&&nz>0;
    }
    // Ears and rear cap wiring are rendered in depth order with the head.
    [-1,1].forEach(side=>{
      for(let j=0;j<20;j++){
        const a=j*Math.PI/10,b=(j+1)*Math.PI/10;
        addFace([[side*.64,-.07,.06],[side*(.69+.055*Math.cos(a)),-.07+.21*Math.sin(a),.035],[side*(.69+.055*Math.cos(b)),-.07+.21*Math.sin(b),.035]],'#d3dce0');
      }
    });
    faces.sort((a,b)=>a.z-b.z).forEach(({pts,fill,stroke})=>{h.beginPath();pts.forEach((p,i)=>i?h.lineTo(p[0],p[1]):h.moveTo(p[0],p[1]));h.closePath();h.fillStyle=fill;h.fill();if(stroke){h.strokeStyle=stroke;h.lineWidth=.4;h.stroke();}});
    // Wires follow only the visible side of the black cap.
    const visibleLine=points=>{
      let segment=[];const flush=()=>{if(segment.length>1)curve(segment,angle,'#3773b5',1.05);segment=[];};
      points.forEach(v=>{const p=projection(...v,angle);if(p[2]>.10)segment.push(v);else flush();});flush();
    };
    for(let j=0;j<12;j++){
      const lon=j*Math.PI/6,low=Math.asin(-.07+.54*Math.max(0,Math.cos(lon))**3);
      visibleLine(Array.from({length:35},(_,i)=>surface(low+i/34*(Math.PI/2-low),lon,.025)));
    }
    [.62,1.05].forEach(lat=>visibleLine(Array.from({length:73},(_,j)=>surface(lat,j*Math.PI/36,.028))));
    const electrode=[];
    for(const lat of [.18,.61,.98,1.35])for(let j=0;j<(lat>1.2?4:8);j++){
      const lon=j*Math.PI/(lat>1.2?2:4),v=surface(lat,lon,.032),p=projection(...v,angle);
      if(p[2]>.05&&v[1]>(-.08+.54*Math.max(0,Math.cos(lon))**3))electrode.push(p);
    }
    electrode.sort((a,b)=>a[2]-b[2]).forEach(p=>{h.beginPath();h.ellipse(p[0],p[1],4.7,3.7,0,0,Math.PI*2);h.fillStyle='#477acb';h.fill();h.strokeStyle='#86a8e8';h.lineWidth=.7;h.stroke();h.beginPath();h.arc(p[0],p[1],1.3,0,Math.PI*2);h.fillStyle='#193563';h.fill();});
    // Black chin strap appears only on the front-facing portion of the mannequin.
    if(Math.cos(angle)>.25){
      curve([[-.57,.01,.30],[-.42,-.53,.42],[-.21,-.73,.40],[0,-.79,.39],[.21,-.73,.40],[.42,-.53,.42],[.57,.01,.30]],angle,'#151b24',9);
      curve([[-.24,-.35,.64],[0,-.39,.71],[.24,-.35,.64]],angle,'rgba(118,132,142,.65)',1);
      [-1,1].forEach(side=>curve([[side*.15,.16,.70],[side*.25,.17,.67],[side*.34,.14,.59]],angle,'rgba(102,121,135,.65)',1.5));
    }
    // Scan height is constrained to y=.48..98, above the open forehead.
    // Clip to cap faces, so the band never paints the face, ears or neck.
    const scanHeight=reduced?.74:.48+(Math.sin(time*.0014)*.5+.5)*.50;
    const scanCenter=projection(0,scanHeight,0,angle),radius=Math.sqrt(1-scanHeight*scanHeight);
    h.save();h.beginPath();
    faces.filter(f=>f.cap).forEach(({pts})=>{
      const area=pts.reduce((v,p,i)=>{const q=pts[(i+1)%pts.length];return v+p[0]*q[1]-q[0]*p[1];},0);
      const ordered=area<0?[...pts].reverse():pts;
      ordered.forEach((p,i)=>i?h.lineTo(p[0],p[1]):h.moveTo(p[0],p[1]));h.closePath();
    });h.clip();
    const band=h.createLinearGradient(0,scanCenter[1]-7,0,scanCenter[1]+7);band.addColorStop(0,'rgba(73,240,223,0)');band.addColorStop(.5,'rgba(73,240,223,.24)');band.addColorStop(1,'rgba(73,240,223,0)');h.fillStyle=band;h.fillRect(60,scanCenter[1]-7,280,14);
    curve(Array.from({length:65},(_,i)=>{const a=i*Math.PI/32;return [.68*radius*Math.sin(a),scanHeight,.75*radius*Math.cos(a)];}),angle,'rgba(112,255,234,.9)',1.2);h.restore();
    h.font='10px Segoe UI';h.fillStyle='#73aeb9';h.fillText('EEG CAP / CROWN SCAN',20,27);h.fillText('假人模特 · 结构示意',274,313);
  }
  function drawScalp() {
    s.clearRect(0,0,400,330);
    const cx=200,cy=162,r=116;
    s.fillStyle='#0a2130';s.beginPath();s.arc(cx,cy,r,0,Math.PI*2);s.fill();
    if(data) {
      const max=Math.max(...data.values.map(Math.abs),1e-12);
      const pixels=s.createImageData(232,232);
      for(let y=0;y<232;y++)for(let x=0;x<232;x++) {
        const px=(x-116)/116,py=(y-116)/116;if(px*px+py*py>1)continue;
        let value=0,weight=0;data.names.forEach((n,i)=>{const [ex,ey]=positions[n];const w=1/Math.pow(Math.max(.035,Math.hypot(px-ex,py-ey)),2);value+=w*Math.abs(data.values[i])/max;weight+=w;});
        const rgb=color(value/weight), k=(y*232+x)*4;pixels.data[k]=rgb[0];pixels.data[k+1]=rgb[1];pixels.data[k+2]=rgb[2];pixels.data[k+3]=218;
      }
      s.putImageData(pixels,cx-r,cy-r);
    }
    s.strokeStyle='#78c4cc';s.lineWidth=1.8;s.beginPath();s.arc(cx,cy,r,0,Math.PI*2);s.stroke();
    s.beginPath();s.moveTo(cx-12,cy-r+1);s.lineTo(cx,cy-r-18);s.lineTo(cx+12,cy-r+1);s.stroke();
    [-1,1].forEach(side=>{s.beginPath();s.ellipse(cx+side*(r+6),cy,7,24,0,0,Math.PI*2);s.stroke();});
    s.font='10px Segoe UI';s.fillStyle='#81a9b6';s.textAlign='center';s.fillText('前额',cx,19);s.fillText('L',56,cy);s.fillText('R',344,cy);
    const names=data?data.names:Object.keys(positions).slice(0,8);
    names.forEach(name=>{const [x,y]=positions[name],px=cx+x*r,py=cy+y*r;s.beginPath();s.arc(px,py,4,0,Math.PI*2);s.fillStyle=data?'#efffff':'#416875';s.fill();s.fillStyle=data?'#f4ffff':'#73959f';s.shadowColor='#06101d';s.shadowBlur=5;s.fillText(name,px,py-9);s.shadowBlur=0;});
    if(!data){s.fillStyle='#9cbfc6';s.font='12px Microsoft YaHei';s.fillText('等待有效脑电与电极位置',cx,cy+27);}
  }
  window.EEGVisual = {
    update(packet) {
      const names=packet?.channels, values=packet?.eeg;
      const valid=Array.isArray(names)&&names.length===8&&new Set(names).size===8&&names.every(n=>Object.prototype.hasOwnProperty.call(positions,n))&&Array.isArray(values)&&values.length===8&&values.every(Number.isFinite);
      data=valid?{names,values}:null;drawScalp();
      document.getElementById('scalpStatus').textContent=valid?(packet.demo?'仿真信号 · 相对幅值':'真实信号 · 相对幅值'):(packet?'电极位置未确认，暂不生成热图':'接口暂无数据传入');
      document.getElementById('scalpCaption').textContent=valid?'颜色表示当前采样点的绝对幅值相对最大值；电极之间为插值。':'电极布局仅作示意；等待已确认名称的8通道数据。';
    }
  };
  drawScalp();
  function animate(time){if(frame++%2===0)drawHead(time);requestAnimationFrame(animate);}requestAnimationFrame(animate);
})();
