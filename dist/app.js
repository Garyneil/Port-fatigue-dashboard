(() => {
  const $ = (id) => document.getElementById(id);
  const pad = (n, size = 2) => String(n).padStart(size, '0');
  const state = {
    neuralRisk: 68,
    risk: 68,
    distance: 0.74,
    attention: 42,
    duration: 26,
    quality: 94,
    response: 612,
    perclos: 24,
    cameraOn: true,
    perclosEnabled: true,
    workSeconds: 6138
  };

  function tickClock() {
    const now = new Date();
    $('clock').textContent = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
    $('date').textContent = `${now.getFullYear()}/${pad(now.getMonth() + 1)}/${pad(now.getDate())}`;
    $('cameraTime').textContent = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}.${pad(now.getMilliseconds(), 3)}`;
    state.workSeconds += 1;
    $('workDuration').textContent = `${pad(Math.floor(state.workSeconds / 3600))}:${pad(Math.floor(state.workSeconds % 3600 / 60))}:${pad(state.workSeconds % 60)}`;
  }

  function seededJitter(scale) { return (Math.random() - 0.48) * scale; }

  function renderModalityState() {
    const perclosActive = state.cameraOn && state.perclosEnabled;
    const cameraToggle = $('cameraToggle');
    const perclosToggle = $('perclosToggle');

    cameraToggle.classList.toggle('is-active', state.cameraOn);
    cameraToggle.setAttribute('aria-pressed', String(state.cameraOn));
    $('cameraStatus').textContent = state.cameraOn ? '已开启' : '未开启';

    perclosToggle.classList.toggle('is-active', perclosActive);
    perclosToggle.classList.toggle('is-unavailable', !state.cameraOn);
    perclosToggle.setAttribute('aria-pressed', String(perclosActive));
    perclosToggle.setAttribute('aria-disabled', String(!state.cameraOn));
    $('perclosStatus').textContent = perclosActive ? '已启用' : '未启用';

    $('perclosEvidence').classList.toggle('is-disabled', !perclosActive);
    $('perclosValue').textContent = perclosActive ? `${Math.round(state.perclos)}%` : '--';
    $('perclosBar').style.width = perclosActive ? `${state.perclos}%` : '0%';
    $('perclosNote').textContent = perclosActive
      ? '操作员摄像头可用，当前参与风险融合'
      : '当前不参与风险评估，系统仅采用 EEG 黎曼证据';
    $('fusionStatus').textContent = perclosActive
      ? '当前采用 EEG 黎曼证据 + PERCLOS 多模态融合评估'
      : 'PERCLOS 权重已置零 · 当前仅采用 EEG 黎曼证据评估';
  }

  function updateSimulation() {
    state.neuralRisk = Math.max(38, Math.min(94, state.neuralRisk + seededJitter(7)));
    state.perclos = Math.max(6, Math.min(42, state.perclos + seededJitter(3.2)));
    const perclosRisk = Math.max(0, Math.min(100, (state.perclos - 8) * 4));
    state.risk = state.cameraOn && state.perclosEnabled
      ? state.neuralRisk * 0.8 + perclosRisk * 0.2
      : state.neuralRisk;
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
    renderModalityState();

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

  $('cameraToggle').addEventListener('click', () => {
    state.cameraOn = !state.cameraOn;
    state.perclosEnabled = state.cameraOn;
    updateSimulation();
  });

  $('perclosToggle').addEventListener('click', () => {
    if (!state.cameraOn) return;
    state.perclosEnabled = !state.perclosEnabled;
    updateSimulation();
  });

  createHistory(); tickClock(); updateSimulation();
  setInterval(tickClock, 250); setInterval(updateSimulation, 2000);
})();
