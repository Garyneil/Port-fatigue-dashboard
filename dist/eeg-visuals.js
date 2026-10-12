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
  const capPhoto = new Image();
  capPhoto.src='./assets/eeg-cap-outline.png';
  function drawHead(time) {
    h.clearRect(0,0,400,330);
    if(!capPhoto.complete||!capPhoto.naturalWidth)return;
    const scale=Math.min(400/capPhoto.naturalWidth,330/capPhoto.naturalHeight);
    const w=capPhoto.naturalWidth*scale,ht=capPhoto.naturalHeight*scale,x=(400-w)/2,y=(330-ht)/2;
    h.drawImage(capPhoto,x,y,w,ht);
    h.save();h.translate(x,y);h.scale(w/479,ht/421);
    // Clip the scan to the upper fabric cap in the supplied reference photo.
    h.beginPath();h.moveTo(80,170);h.bezierCurveTo(88,102,137,50,222,39);h.bezierCurveTo(300,26,363,64,393,133);h.bezierCurveTo(402,155,407,177,402,202);h.lineTo(358,201);h.lineTo(293,185);h.lineTo(214,178);h.lineTo(148,174);h.closePath();h.clip();
    const sy=reduced?115:48+(Math.sin(time*.0015)*.5+.5)*145;
    const band=h.createLinearGradient(0,sy-12,0,sy+12);band.addColorStop(0,'rgba(66,255,230,0)');band.addColorStop(.5,'rgba(66,255,230,.38)');band.addColorStop(1,'rgba(66,255,230,0)');h.fillStyle=band;h.fillRect(65,sy-12,355,24);
    h.beginPath();h.moveTo(65,sy);h.lineTo(420,sy);h.strokeStyle='#8bffe9';h.lineWidth=2;h.shadowColor='#4fffdc';h.shadowBlur=9;h.stroke();h.restore();
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
    }
  };
  drawScalp();
  function animate(time){if(frame++%2===0)drawHead(time);requestAnimationFrame(animate);}requestAnimationFrame(animate);
})();
