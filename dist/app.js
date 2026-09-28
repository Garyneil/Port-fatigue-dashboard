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

  createHistory(); tickClock(); updateSimulation();
  setInterval(tickClock, 250); setInterval(updateSimulation, 2000);
})();
