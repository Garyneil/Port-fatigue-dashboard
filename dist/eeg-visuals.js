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
    const angle=reduced?.4:time*.00032;
    h.clearRect(0,0,400,330);
    const glow=h.createRadialGradient(200,160,20,200,160,170);glow.addColorStop(0,'rgba(22,136,154,.2)');glow.addColorStop(1,'rgba(4,18,31,0)');h.fillStyle=glow;h.fillRect(0,0,400,330);
    h.strokeStyle='rgba(54,224,208,.18)';h.beginPath();h.ellipse(200,289,115,21,0,0,Math.PI*2);h.stroke();
    // Head surface is an actual 3D ellipsoid mesh with depth-shaded faces.
    const surface=(lat,lon)=>[.7*Math.cos(lat)*Math.sin(lon),1.0*Math.sin(lat),.78*Math.cos(lat)*Math.cos(lon)];
    const faces=[];
    for(let a=-7;a<8;a++) for(let b=0;b<28;b++) {
      const pts=[[a,b],[a+1,b],[a+1,b+1],[a,b+1]].map(([i,j])=>projection(...surface(i*Math.PI/16,j*Math.PI/14),angle));
      faces.push({pts,z:pts.reduce((sum,p)=>sum+p[2],0)/4});
    }
    faces.sort((a,b)=>a.z-b.z).forEach(({pts,z})=>{h.beginPath();pts.forEach((p,i)=>i?h.lineTo(p[0],p[1]):h.moveTo(p[0],p[1]));h.closePath();h.fillStyle=`rgba(22,${Math.round(65+(z+1)*24)},${Math.round(83+(z+1)*31)},.82)`;h.fill();h.strokeStyle=`rgba(69,204,216,${z>0?.17:.05})`;h.lineWidth=.65;h.stroke();});
    // Nose, chin, neck and ears establish a recognizable head silhouette.
    curve([[-.11,.13,.76],[0,.17,1.03],[.11,.13,.76]],angle,'#72cbd1',1.7);
    curve([[-.17,-.23,.71],[0,-.27,.78],[.17,-.23,.71]],angle,'rgba(132,214,218,.55)',1.3);
    curve([[-.27,-.87,.12],[-.29,-1.12,.1],[-.56,-1.2,.08]],angle,'#448b9d',2);
    curve([[.27,-.87,.12],[.29,-1.12,.1],[.56,-1.2,.08]],angle,'#448b9d',2);
    [-1,1].forEach(side=>curve(Array.from({length:25},(_,i)=>{const a=i/24*Math.PI*2;return [side*(.7+.06*Math.cos(a)),-.03+.23*Math.sin(a),.02];}),angle,'#519dab',1.5));
    // EEG cap meridians and latitude straps sit above the cranial surface.
    for(let j=0;j<8;j++) curve(Array.from({length:41},(_,i)=>{const a=.04+i/40*1.46;return [.73*Math.cos(a)*Math.sin(j*Math.PI/4),1.04*Math.sin(a),.81*Math.cos(a)*Math.cos(j*Math.PI/4)];}),angle,'rgba(81,232,219,.62)',1.2);
    [.25,.6,.93].forEach(lat=>curve(Array.from({length:57},(_,j)=>[.73*Math.cos(lat)*Math.sin(j*Math.PI/28),1.04*Math.sin(lat),.81*Math.cos(lat)*Math.cos(j*Math.PI/28)]),angle,'rgba(85,221,219,.45)',1.2));
    const nodes=Object.entries(positions).slice(0,8).map(([name,[x,z]])=>{const y=Math.sqrt(Math.max(.02,1-x*x-z*z));return {name,p:projection(x*.73,y*1.04,z*.81,angle)};}).sort((a,b)=>a.p[2]-b.p[2]);
    nodes.forEach(({p})=>{h.beginPath();h.arc(p[0],p[1],p[2]>0?4:2.5,0,Math.PI*2);h.fillStyle=p[2]>0?'#91fff0':'#287e8a';h.shadowColor='#51eed6';h.shadowBlur=p[2]>0?10:0;h.fill();h.shadowBlur=0;});
    const scanY=reduced?158:78+(Math.sin(time*.0012)*.5+.5)*175;
    const scan=h.createLinearGradient(0,scanY-18,0,scanY+4);scan.addColorStop(0,'rgba(54,224,208,0)');scan.addColorStop(1,'rgba(54,224,208,.15)');h.fillStyle=scan;h.fillRect(70,scanY-18,260,22);h.strokeStyle='rgba(110,255,225,.8)';h.beginPath();h.ellipse(200,scanY,100,12,0,0,Math.PI*2);h.stroke();
    h.font='10px Segoe UI';h.fillStyle='#73aeb9';h.fillText('EEG CAP / 3D SCAN',20,27);h.fillText('结构示意',318,306);
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
