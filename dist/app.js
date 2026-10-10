(() => {
  const $ = id => document.getElementById(id);
  const pad = n => String(n).padStart(2, '0');
  const state = { demo: false, risk: 68, distance: .74, attention: 42, duration: 26, quality: 94, response: 612, workSeconds: 6138 };
  let generation = 0, socket = null, controller = null, receivedAt = 0, latest = null, polling = false;
  let endpoint = './api/eeg/latest';
  try { endpoint = localStorage.getItem('eegInterfaceUrl') || endpoint; } catch (_) {}
  $('interfaceUrl').value = endpoint;
  const number = v => typeof v === 'number' && Number.isFinite(v) ? v : null;
  const jitter = scale => (Math.random() - .48) * scale;
  const width = (id, v) => { $(id).style.width = `${v == null ? 0 : Math.max(0, Math.min(100, v))}%`; };
  function clearEvidence(message = '接口暂无数据传入') {
    ['riskScore','distanceValue','attentionValue','durationValue','signalQuality','responseTime','workDuration'].forEach(id => { $(id).textContent = '--'; });
    ['distanceBar','attentionBar','durationBar'].forEach(id => width(id, null));
    $('riskGauge').style.setProperty('--risk', 0);
    $('riskGauge').style.background = 'conic-gradient(from 220deg, rgba(101,139,157,.12) 0 280deg, transparent 0)';
    $('riskLabel').textContent = '等待数据'; $('riskLabel').style.color = '#7693a3';
    $('riskAdvice').textContent = message; $('decisionText').textContent = message;
    $('decisionStrip').style.borderColor = '#385464';
    $('currentPoint').style.display = 'none'; $('historicalPoints').innerHTML = '';
    $('sourceStatus').textContent = message; $('systemStatus').textContent = '等待脑电接口';
    $('streamStatus').textContent = 'EEG · WAITING'; $('operatorName').textContent = '--';
    $('calibrationStatus').textContent = '等待校准状态'; $('eegFormat').textContent = '等待设备数据'; $('eegSamples').textContent = '--';
  }
  function renderMetrics(data) {
    const risk = number(data.risk), distance = number(data.distance), attention = number(data.attention), duration = number(data.duration);
    $('riskScore').textContent = risk == null ? '--' : Math.round(risk);
    $('distanceValue').textContent = distance == null ? '--' : distance.toFixed(2);
    $('attentionValue').textContent = attention == null ? '--' : `${Math.round(attention)}%`;
    $('durationValue').textContent = duration == null ? '--' : `${Math.round(duration)} s`;
    $('signalQuality').textContent = number(data.quality) == null ? '--' : Math.round(data.quality);
    $('responseTime').textContent = number(data.response) == null ? '--' : Math.round(data.response);
    const seconds = number(data.workSeconds);
    $('workDuration').textContent = seconds == null ? '--' : `${pad(Math.floor(seconds / 3600))}:${pad(Math.floor(seconds % 3600 / 60))}:${pad(Math.floor(seconds % 60))}`;
    width('distanceBar', distance == null ? null : distance * 100); width('attentionBar', attention); width('durationBar', duration == null ? null : duration * 2);
    const high = risk != null && risk >= 82 && duration != null && duration >= 30, warning = risk != null && risk >= 62;
    const color = risk == null ? '#7693a3' : high ? '#ff5e63' : warning ? '#ffb74d' : '#36e0d0';
    $('riskGauge').style.setProperty('--risk', risk ?? 0);
    $('riskGauge').style.background = `conic-gradient(from 220deg, ${color} calc(${risk ?? 0} * 2.8deg), rgba(101,139,157,.12) 0 280deg, transparent 0)`;
    $('riskLabel').textContent = risk == null ? '等待推理' : high ? '高风险' : warning ? '中高风险' : '状态稳定';
    $('riskAdvice').textContent = risk == null ? '已收到脑电，尚无推理结果' : high ? '建议触发人工复核' : warning ? '建议加强观察' : '保持常规监测';
    $('decisionText').textContent = risk == null ? '等待模型推理结果' : high ? '预警待复核 · 建议准备交班' : warning ? '持续观察 · 尚未触发交班预警' : '正常监测 · 无需干预';
    $('riskLabel').style.color = color; $('decisionStrip').style.borderColor = color;
    const velocity = number(data.velocity);
    $('currentPoint').style.display = distance == null || velocity == null ? 'none' : '';
    if (distance != null && velocity != null) $('currentPoint').setAttribute('transform', `translate(${54 + Math.min(1, distance) * 442} ${224 - Math.min(.5, velocity) / .5 * 190})`);
  }
  function simulate() {
    state.risk = Math.max(38, Math.min(94, state.risk + jitter(7)));
    state.distance = Math.max(.35, Math.min(.98, state.distance + jitter(.055)));
    state.attention = Math.max(24, Math.min(82, 100 - state.risk + jitter(8)));
    state.duration = state.risk >= 62 ? Math.min(60, state.duration + 2) : Math.max(0, state.duration - 4);
    state.quality = Math.round(Math.max(88, Math.min(98, state.quality + jitter(3)))); state.response = Math.round(430 + state.risk * 2.7 + jitter(30));
    renderMetrics({ ...state, velocity: Math.max(.06, Math.min(.42, .08 + state.risk / 300 + jitter(.04))) });
    $('sourceStatus').textContent = '仿真演示已开启 · 当前展示模拟数据'; $('systemStatus').textContent = '仿真演示中'; $('streamStatus').textContent = 'EEG · SIMULATED';
    $('operatorName').textContent = 'OP-017 · 模拟席位 A'; $('calibrationStatus').textContent = '仿真校准状态'; $('eegFormat').textContent = '8 通道 · 仿真输入'; $('eegSamples').textContent = Array.from({length:8}, (_,i) => `CH${i+1}: ${(Math.sin(Date.now()/500+i)*20).toFixed(2)}`).join('  ');
  }
  function acceptPacket(packet, token) {
    if (state.demo || token !== generation) return;
    const stamp = packet && Date.parse(packet.timestamp), age = Date.now() - stamp;
    const raw = packet && packet.eeg;
    const validRaw = Array.isArray(raw) && raw.length === 8 && raw.every(v => number(v) != null);
    const probability = packet && number(packet.fatigue_probability), validPrediction = probability != null && probability >= 0 && probability <= 1;
    if (!packet || packet.source !== 'real' || packet.has_data !== true || !Number.isFinite(stamp) || age < -2000 || age > 10000 || (!validRaw && !validPrediction)) { latest = null; receivedAt = 0; clearEvidence(); return; }
    latest = packet; receivedAt = stamp;
    $('eegSamples').textContent = validRaw ? raw.map((v,i) => `CH${i+1}: ${v.toFixed(2)}`).join('  ') : '--';
    const optional = (key, min, max) => { const v = number(packet[key]); return v != null && v >= min && v <= max ? v : null; };
    renderMetrics({risk: validPrediction ? probability * 100 : null, distance: optional('distance',0,100), attention: optional('attention',0,100), duration: optional('duration',0,86400), quality: optional('quality',0,100), response: optional('response_ms',0,60000), workSeconds: optional('work_seconds',0,864000), velocity: optional('velocity',0,100)});
    $('sourceStatus').textContent = validPrediction ? '真实脑电接口已接收 · 显示模型推理结果' : '真实脑电接口已接收 · 等待模型推理结果';
    $('systemStatus').textContent = '真实脑电数据已接入'; $('streamStatus').textContent = 'EEG · REAL DATA';
    $('operatorName').textContent = typeof packet.operator === 'string' ? packet.operator : '当前设备';
    $('calibrationStatus').textContent = packet.calibrated === true ? '接口报告：校准完成' : '尚未确认校准';
    $('eegFormat').textContent = `8 通道${number(packet.sample_rate_hz) != null ? ` · ${packet.sample_rate_hz} Hz` : ''}`;
  }
  function disconnect() {
    generation += 1; controller?.abort(); controller = null;
    if (socket) { socket.onmessage = null; socket.onclose = null; socket.onerror = null; socket.close(); socket = null; }
    latest = null; receivedAt = 0; polling = false;
  }
  async function poll() {
    if (state.demo || socket || polling || !endpoint) return;
    const token = generation, request = new AbortController(); controller = request; polling = true;
    const timeout = setTimeout(() => request.abort(), 4000);
    try {
      const url = new URL(endpoint, location.href); if (!['http:','https:'].includes(url.protocol)) throw Error();
      const response = await fetch(url.href, {cache:'no-store',signal:request.signal}); if (!response.ok) throw Error();
      acceptPacket(await response.json(), token);
    } catch (_) { if (!state.demo && token === generation) { latest = null; receivedAt = 0; clearEvidence(); } }
    finally { clearTimeout(timeout); if (token === generation) { polling = false; controller = null; } }
  }
  function connect() {
    if (state.demo) return; clearEvidence();
    let url; try { url = new URL(endpoint, location.href); } catch (_) { return; }
    if (['ws:','wss:'].includes(url.protocol)) {
      const token = generation;
      try {
        const connection = new WebSocket(url.href); socket = connection;
        connection.onmessage = event => { try { acceptPacket(JSON.parse(event.data), token); } catch (_) { if (!state.demo && token === generation) { latest = null; receivedAt = 0; clearEvidence(); } } };
        const failed = () => { if (!state.demo && token === generation && socket === connection) { socket = null; connection.onmessage = null; connection.onclose = null; connection.onerror = null; connection.close(); latest = null; receivedAt = 0; clearEvidence(); } };
        connection.onerror = failed; connection.onclose = failed;
      } catch (_) { socket = null; }
    } else { poll(); }
  }
  $('demoToggle').addEventListener('click', () => {
    disconnect(); state.demo = !state.demo; document.body.dataset.demo = String(state.demo);
    $('demoToggle').setAttribute('aria-pressed', String(state.demo)); $('demoState').textContent = state.demo ? '开启' : '关闭';
    $('inputBadge').textContent = state.demo ? '仿真演示' : '真实接口'; $('dataMode').textContent = state.demo ? '数据模式：仿真演示' : '数据模式：真实接口'; $('interfaceUrl').disabled = state.demo;
    if (state.demo) { $('historicalPoints').innerHTML = [[.18,.1],[.35,.18],[.47,.16],[.61,.19],[.81,.34]].map(([x,y]) => `<circle cx="${54+x*442}" cy="${224-y/.5*190}" r="2.6"/>`).join(''); simulate(); }
    else { clearEvidence(); connect(); }
  });
  $('interfaceForm').addEventListener('submit', event => {
    event.preventDefault(); if (state.demo) return;
    const next = $('interfaceUrl').value.trim() || './api/eeg/latest';
    try { const url = new URL(next,location.href); if (!['http:','https:','ws:','wss:'].includes(url.protocol)) throw Error(); } catch (_) { $('sourceStatus').textContent = '请输入有效的脑电接口地址'; return; }
    endpoint = next; try { localStorage.setItem('eegInterfaceUrl', endpoint); } catch (_) {} disconnect(); connect();
  });
  function clock() {
    const now = new Date(); $('clock').textContent = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
    $('date').textContent = `${now.getFullYear()}/${pad(now.getMonth()+1)}/${pad(now.getDate())}`; $('cameraTime').textContent = $('clock').textContent;
    if (state.demo) state.workSeconds += 1;
    if (!state.demo && latest && Date.now() - receivedAt > 10000) { latest = null; receivedAt = 0; clearEvidence(); }
  }
  clearEvidence(); clock(); connect(); setInterval(clock,1000);
  setInterval(() => { if (state.demo) simulate(); else if (!socket) { if (/^wss?:/i.test(endpoint)) connect(); else poll(); } },2000);
})();
