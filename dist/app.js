(() => {
  const $ = (id) => document.getElementById(id);
  const pad = (n, size = 2) => String(n).padStart(size, '0');
  const state = { risk: 68, distance: 0.74, attention: 42, duration: 26, quality: 94, response: 612, workSeconds: 6138 };

  function tickClock() {
    const now = new Date();
    $('clock').textContent = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
    $('date').textContent = `${now.getFullYear()}/${pad(now.getMonth() + 1)}/${pad(now.getDate())}`;
    $('cameraTime').textContent = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}.${pad(now.getMilliseconds(), 3)}`;
    state.workSeconds += 1;
    $('workDuration').textContent = `${pad(Math.floor(state.workSeconds / 3600))}:${pad(Math.floor(state.workSeconds % 3600 / 60))}:${pad(state.workSeconds % 60)}`;
  }

  function seededJitter(scale) { return (Math.random() - 0.48) * scale; }
  function updateSimulation() {
    state.risk = Math.max(38, Math.min(94, state.risk + seededJitter(7)));
    state.distance = Math.max(.35, Math.min(.98, state.distance + seededJitter(.055)));
    state.attention = Math.max(24, Math.min(82, 100 - state.risk + seededJitter(8)));
    state.duration = state.risk >= 62 ? Math.min(60, state.duration + 2) : Math.max(0, state.duration - 4);
    state.quality = Math.round(Math.max(88, Math.min(98, state.quality + seededJitter(3))));
    state.response = Math.round(Math.max(460, Math.min(810, 430 + state.risk * 2.7 + seededJitter(30))));

    const risk = Math.round(state.risk), distance = state.distance.toFixed(2), attention = Math.round(state.attention);
    $('riskScore').textContent = risk;
    $('riskGauge').style.setProperty('--risk', risk);
    $('distanceValue').textContent = distance;
    $('distanceBar').style.width = `${state.distance * 100}%`;
    $('attentionValue').textContent = `${attention}%`;
    $('attentionBar').style.width = `${attention}%`;
    $('durationValue').textContent = `${state.duration} s`;
    $('durationBar').style.width = `${Math.min(100, state.duration * 2)}%`;
    $('signalQuality').textContent = state.quality;
    $('responseTime').textContent = state.response;

    const high = risk >= 82 && state.duration >= 30;
    const warning = risk >= 62;
    $('riskLabel').textContent = high ? '高风险' : warning ? '中高风险' : '状态稳定';
    $('riskAdvice').textContent = high ? '建议触发人工复核' : warning ? '建议加强观察' : '保持常规监测';
    $('decisionText').textContent = high ? '预警待复核 · 建议准备交班' : warning ? '持续观察 · 尚未触发交班预警' : '正常监测 · 无需干预';
    const color = high ? '#ff5e63' : warning ? '#ffb74d' : '#36e0d0';
    $('riskLabel').style.color = color;
    $('riskGauge').style.background = `conic-gradient(from 220deg, ${color} calc(${risk} * 2.8deg), rgba(101,139,157,.12) 0 280deg, transparent 0)`;
    $('decisionStrip').style.borderColor = color;

    const px = 54 + Math.min(1, state.distance) * 442;
    const velocity = Math.max(.06, Math.min(.42, .08 + risk / 300 + seededJitter(.04)));
    const py = 224 - velocity / .5 * 190;
    $('currentPoint').setAttribute('transform', `translate(${px.toFixed(1)} ${py.toFixed(1)})`);
  }

  function createHistory() {
    const group = $('historicalPoints');
    const points = [[.18,.10],[.24,.14],[.29,.09],[.35,.18],[.38,.13],[.43,.21],[.47,.16],[.55,.24],[.61,.19],[.67,.29],[.72,.25],[.81,.34],[.86,.39]];
    group.innerHTML = points.map(([x,y]) => `<circle cx="${54+x*442}" cy="${224-y/.5*190}" r="2.6"/>`).join('');
  }

  const canvas = $('portCanvas');
  const ctx = canvas.getContext('2d');
  let t = 0;
  function fitCanvas() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const rect = canvas.getBoundingClientRect();
    canvas.width = Math.max(1, Math.round(rect.width * dpr));
    canvas.height = Math.max(1, Math.round(rect.height * dpr));
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  function line(x1,y1,x2,y2,color,width=1){ctx.strokeStyle=color;ctx.lineWidth=width;ctx.beginPath();ctx.moveTo(x1,y1);ctx.lineTo(x2,y2);ctx.stroke()}
  function drawPort() {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    if (!w || !h) return requestAnimationFrame(drawPort);
    t += .008;
    const sky = ctx.createLinearGradient(0,0,0,h*.72);sky.addColorStop(0,'#102b3d');sky.addColorStop(.55,'#173c4b');sky.addColorStop(1,'#0a2332');ctx.fillStyle=sky;ctx.fillRect(0,0,w,h*.74);
    const glow = ctx.createRadialGradient(w*.77,h*.18,2,w*.77,h*.18,w*.32);glow.addColorStop(0,'rgba(115,196,207,.18)');glow.addColorStop(1,'rgba(10,33,46,0)');ctx.fillStyle=glow;ctx.fillRect(0,0,w,h*.65);
    ctx.fillStyle='#0a1c28';ctx.fillRect(0,h*.58,w,h*.18);
    for(let i=0;i<7;i++){const x=i*w/6+Math.sin(t+i)*4;line(x,h*.59,x+w*.08,h*.45,'rgba(51,101,119,.36)',2)}
    const water = ctx.createLinearGradient(0,h*.72,0,h);water.addColorStop(0,'#0a2633');water.addColorStop(1,'#061723');ctx.fillStyle=water;ctx.fillRect(0,h*.72,w,h*.28);
    for(let i=0;i<16;i++){const y=h*.75+i*h*.015;const off=Math.sin(t*2+i)*18;line(off,y,w*.96+off,y,'rgba(59,144,158,.11)',1)}
    ctx.fillStyle='#112431';ctx.beginPath();ctx.moveTo(w*.08,h*.64);ctx.lineTo(w*.67,h*.64);ctx.lineTo(w*.72,h*.75);ctx.lineTo(w*.04,h*.75);ctx.closePath();ctx.fill();line(w*.04,h*.75,w*.72,h*.75,'#315d69',2);
    const colors=['#b8643a','#315f79','#a38a42','#526a72','#87543d'];for(let r=0;r<3;r++)for(let c=0;c<7;c++){ctx.fillStyle=colors[(r+c)%colors.length];ctx.fillRect(w*(.1+c*.065),h*(.59-r*.055),w*.058,h*.045);ctx.strokeStyle='rgba(190,218,220,.18)';ctx.strokeRect(w*(.1+c*.065),h*(.59-r*.055),w*.058,h*.045)}
    drawCrane(w*.62,h*.18,w*.2,h*.5);drawCrane(w*.78,h*.27,w*.15,h*.39);
    const tx=w*(.26+(Math.sin(t*.7)*.5+.5)*.13);ctx.fillStyle='#d39a43';ctx.fillRect(tx,h*.69,w*.055,h*.025);ctx.fillStyle='#1c303a';ctx.fillRect(tx+w*.01,h*.675,w*.025,h*.018);ctx.fillStyle='#060b0f';ctx.beginPath();ctx.arc(tx+w*.012,h*.72,w*.007,0,Math.PI*2);ctx.arc(tx+w*.047,h*.72,w*.007,0,Math.PI*2);ctx.fill();
    ctx.fillStyle='rgba(8,18,25,.55)';ctx.fillRect(w*.71,h*.67,w*.25,h*.07);ctx.beginPath();ctx.moveTo(w*.68,h*.74);ctx.lineTo(w*.98,h*.74);ctx.lineTo(w*.92,h*.8);ctx.lineTo(w*.73,h*.8);ctx.closePath();ctx.fill();line(w*.68,h*.74,w*.98,h*.74,'rgba(88,178,188,.3)');
    for(let i=0;i<5;i++){ctx.fillStyle=i%2?'#263f4a':'#182f3a';ctx.fillRect(w*(.73+i*.045),h*.63,w*.04,h*.035)}
    const vignette=ctx.createRadialGradient(w/2,h/2,h*.22,w/2,h/2,h*.75);vignette.addColorStop(0,'rgba(0,0,0,0)');vignette.addColorStop(1,'rgba(0,5,12,.7)');ctx.fillStyle=vignette;ctx.fillRect(0,0,w,h);
    requestAnimationFrame(drawPort);
  }
  function drawCrane(x,y,cw,ch){ctx.save();ctx.strokeStyle='#294f5d';ctx.lineWidth=Math.max(2,cw*.018);ctx.lineJoin='miter';line(x,y+ch,x+cw*.1,y,'#315967',3);line(x+cw*.1,y,x+cw*.82,y,'#315967',3);line(x+cw*.1,y,x+cw*.35,y+ch,'#315967',4);line(x+cw*.28,y+ch,x+cw*.64,y+ch,'#264753',6);line(x+cw*.46,y,x+cw*.46,y+ch*.64,'rgba(63,114,127,.65)',2);ctx.fillStyle='#152e39';ctx.fillRect(x+cw*.39,y+ch*.18,cw*.14,ch*.1);ctx.restore()}

  window.addEventListener('resize', fitCanvas);
  fitCanvas(); createHistory(); tickClock(); updateSimulation(); drawPort();
  setInterval(tickClock, 250); setInterval(updateSimulation, 2000);
})();
