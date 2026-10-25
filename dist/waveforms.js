(() => {
  const $ = id => document.getElementById(id);
  if (!['127.0.0.1','localhost','[::1]'].includes(location.hostname)) {
    $('waveStatus').textContent = '在线展示页 · 真实设备波形请使用 Windows 演示包';
    return;
  }
  let rows=[], cursor=0, session=null, busy=false, seconds=30;
  const charts=[['filteredWave',r=>r.eeg_filtered,['#38dfc6','#58aaff'],false],['attentionWave',r=>[r.attention],['#f5bc60'],true],['relaxationWave',r=>[r.relaxation],['#b49aff'],true]];
  function draw() {
    const end=Date.now()/1000, start=end-seconds;
    rows=rows.filter(r=>r.time>=end-65);
    const visible=rows.filter(r=>r.time>=start && r.time<=end);
    for (const [id, values, colors, fixed] of charts) {
      const canvas=$(id), w=canvas.clientWidth, h=canvas.clientHeight, ratio=devicePixelRatio||1;
      canvas.width=w*ratio;canvas.height=h*ratio;
      const c=canvas.getContext('2d');c.scale(ratio,ratio);
      const left=65,right=w-14,top=15,bottom=h-30;
      let min=0,max=100;
      if(!fixed){min=Infinity;max=-Infinity;for(const row of visible) for(const v of values(row)){min=Math.min(min,v);max=Math.max(max,v);}if(!Number.isFinite(min)){min=-1;max=1;}const margin=Math.max((max-min)*.1,1);min-=margin;max+=margin;}
      const x=t=>left+(t-start)/seconds*(right-left),y=v=>bottom-(v-min)/(max-min)*(bottom-top);
      c.font='11px Segoe UI';c.lineWidth=1;
      for(let i=0;i<=4;i++){const yy=top+(bottom-top)*i/4;c.strokeStyle='#203b49';c.beginPath();c.moveTo(left,yy);c.lineTo(right,yy);c.stroke();c.fillStyle='#8aabbc';c.textAlign='right';c.fillText((max-(max-min)*i/4).toFixed(fixed?0:1),left-8,yy+4);}
      for(let i=0;i<=4;i++){const xx=left+(right-left)*i/4;c.fillStyle='#8aabbc';c.textAlign='center';c.fillText(`${Math.round(-seconds+seconds*i/4)} s`,xx,h-9);}
      c.save();c.beginPath();c.rect(left,top,right-left,bottom-top);c.clip();
      for(let i=1;i<visible.length;i++){const a=visible[i-1],b=visible[i];if(b.time-a.time<=.5 && b.wear_code===0){c.fillStyle='rgba(255,95,100,.09)';c.fillRect(x(a.time),top,Math.max(1,x(b.time)-x(a.time)),bottom-top);}}
      colors.forEach((color,index)=>{c.strokeStyle=color;c.lineWidth=1.3;c.beginPath();let prev=null;for(const r of visible){const v=values(r)[index];if(!Number.isFinite(v)){prev=null;continue;}if(!prev||r.time-prev.time>.5||r.id!==prev.id+1)c.moveTo(x(r.time),y(v));else c.lineTo(x(r.time),y(v));prev=r;}c.stroke();});
      c.restore();if(!visible.length){c.fillStyle='#8aabbc';c.textAlign='center';c.fillText('等待真实数据',w/2,h/2);}
    }
  }
  async function poll(){
    if(busy)return;busy=true;
    try{
      if(document.body.dataset.demo==='true'){rows=[];cursor=0;session=null;$('waveStatus').textContent='仿真模式 · 真实波形暂停';return;}
      const response=await fetch(`/api/eeg/samples?after=${cursor}`,{cache:'no-store',signal:AbortSignal.timeout(3000)});
      if(!response.ok)throw Error();const data=await response.json();
      if(session!==null && session!==data.session){rows=[];cursor=0;session=data.session;return;}
      session=data.session;
      for(const row of data.samples){if(row.id>cursor && Number.isFinite(row.time) && Array.isArray(row.eeg_filtered)&&row.eeg_filtered.length===2&&row.eeg_filtered.every(Number.isFinite)&&Number.isFinite(row.attention)&&Number.isFinite(row.relaxation))rows.push(row);}
      cursor=data.cursor;
      const last=rows.at(-1),fresh=last&&Date.now()/1000-last.time<2&&data.connection_status==='streaming';
      $('waveStatus').textContent=data.connection_status==='closed'?'串口已关闭 · 保留最近波形':fresh?`实时接收 · ${last.wear_code===0?'佩戴失败':`佩戴码 ${last.wear_code}`} ${data.truncated?'· 历史缓存有缺口':''}`:'等待数据／数据中断';
      $('filteredValue').textContent=fresh?`Fp1 ${last.eeg_filtered[0].toFixed(2)} / Fp2 ${last.eeg_filtered[1].toFixed(2)}`:'--';
      $('attentionWaveValue').textContent=fresh?last.attention.toFixed(2):'--';$('relaxationWaveValue').textContent=fresh?last.relaxation.toFixed(2):'--';
    }catch(_){$('waveStatus').textContent='波形接口不可用／连接中断';['filteredValue','attentionWaveValue','relaxationWaveValue'].forEach(id=>$(id).textContent='--');}
    finally{busy=false;draw();}
  }
  $('waveWindow').addEventListener('change',e=>{seconds=Number(e.target.value);draw();});
  window.addEventListener('resize',draw);poll();setInterval(poll,250);
})();
