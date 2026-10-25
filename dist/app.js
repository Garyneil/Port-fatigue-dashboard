(() => {
  const $ = id => document.getElementById(id);
  const pad = n => String(n).padStart(2, '0');
  const state = { demo: false, risk: 68, distance: .74, attention: 42, duration: 26, quality: 94, response: 612, workSeconds: 6138 };
  let generation = 0, socket = null, controller = null, receivedAt = 0, latest = null, polling = false;
  let endpoint = './api/eeg/latest';
  try { endpoint = localStorage.getItem('eegInterfaceUrl') || endpoint; } catch (_) {}
  $('interfaceUrl').value = endpoint;
  const number = v => typeof v === 'number' && Number.isFinite(v) ? v : null;
  const localService = ['127.0.0.1','localhost','[::1]'].includes(new URL(location.href).hostname);
  fetch(localService ? '/api/model/verification' : './model-verification.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error();return r.json();}).then(data=>{
    $('replayVerification').textContent=data.replays.map(r=>`${r.true_label==='alert'?'清醒标签':'困倦标签'} → ${r.fatigue_tendency==='alert'?'倾向清醒':r.fatigue_tendency==='drowsy'?'倾向疲劳':'暂不确定'} ${Math.round(r.drowsy_model_score*100)} 分`).join('；');
  }).catch(()=>{$('replayVerification').textContent='回放记录暂不可用';});
  const jitter = scale => (Math.random() - .48) * scale;
  let episode = {active:false,warning:0,high:0,recovery:0,last:null,risk:null};
  function renderCandidate(candidate) {
    if (!candidate) return;
    const status = candidate.status;
    if (candidate.model?.includes('疲劳分类')) {
      const active = status === 'fatigue_inference';
      const label = {drowsy:'倾向疲劳',alert:'倾向清醒',uncertain:'暂不确定'}[candidate.fatigue_tendency];
      $('candidateState').textContent = active ? label : status === 'calibrating' ? `初始参考采集中 · 剩余 ${candidate.remaining_seconds ?? '--'} 秒` : candidate.message || '等待头环数据';
      $('candidateValue').textContent = active ? `${Math.round(candidate.drowsy_model_score*100)} / 100` : '--';
      $('candidateNote').textContent = 'SADT 清醒/困倦行为标签训练 · 显示分类模型分数，尚未经概率校准；头环适用性仍在验证。';
      return;
    }
    const labels = {waiting_for_data:'等待头环数据',calibrating:`个体基线校准中 · ${candidate.remaining_seconds ?? '--'} 秒`,candidate_inference:'候选模型正在运行',rate_out_of_range:'采样帧率不匹配 · 暂停输出',packet_loss:'数据缺帧较多 · 暂停输出',model_missing:'未找到模型文件',model_unavailable:'候选模型未加载'};
    $('candidateState').textContent = labels[status] || candidate.message || '等待候选推理';
    $('candidateValue').textContent = status === 'candidate_inference' && number(candidate.predicted_reaction_time_seconds) != null
      ? `${candidate.predicted_reaction_time_seconds.toFixed(2)} s` : '--';
    const pct = number(candidate.training_reference_percentile);
    $('candidateNote').textContent = status === 'candidate_inference'
      ? `反应时间代理；在训练集反应时参考分布约第 ${Math.round(pct ?? 0)} 百分位。此结果不是疲劳概率或疲劳判定，头环外部验证未完成。`
      : `${candidate.message || '收集头环数据后开始校准。'}；输出为反应时间代理，不是疲劳概率，模型尚未完成头环外部验证。`;
  }
  function resetEpisode(){episode={active:false,warning:0,high:0,recovery:0,last:null,risk:null};}
  function pauseEpisode(){episode.last=null;episode.risk=null;episode.high=0;episode.recovery=0;}
  function trackRisk(risk, now=Date.now()) {
    if(risk==null){pauseEpisode();return {duration:null,highDuration:null};}
    const dt=episode.last==null?0:Math.max(0,Math.min(10,(now-episode.last)/1000));
    if(episode.active)episode.warning+=dt;
    if(episode.risk!=null&&episode.risk>=82&&risk>=82)episode.high+=dt;else episode.high=0;
    if(episode.active&&risk<58){episode.recovery=episode.risk!=null&&episode.risk<58?episode.recovery+dt:0;if(episode.recovery>=10){episode.active=false;episode.warning=0;episode.high=0;episode.recovery=0;}}
    else episode.recovery=0;
    if(!episode.active&&risk>=62){episode.active=true;episode.warning=0;}
    episode.last=now;episode.risk=risk;
    return {duration:episode.active?episode.warning:0,highDuration:episode.high};
  }
  function clearEvidence(message = '接口暂无数据传入') {
    pauseEpisode();
    if(latest == null && episode.active && message === '接口暂无数据传入') message='数据中断 · 计时暂停';
    window.EEGVisual?.update(null);
    ['riskScore','signalQuality','responseTime','workDuration'].forEach(id => { $(id).textContent = '--'; });
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
    const risk = number(data.risk), distance = number(data.distance), attention = number(data.attention);
    const tracked=trackRisk(risk),duration=tracked.duration;
    $('riskScore').textContent = risk == null ? '--' : Math.round(risk);
    $('signalQuality').textContent = number(data.quality) == null ? '--' : Math.round(data.quality);
    $('responseTime').textContent = number(data.response) == null ? '--' : Math.round(data.response);
    const seconds = number(data.workSeconds);
    $('workDuration').textContent = seconds == null ? '--' : `${pad(Math.floor(seconds / 3600))}:${pad(Math.floor(seconds % 3600 / 60))}:${pad(Math.floor(seconds % 60))}`;
    const high = risk != null && risk >= 82, warning = risk != null && risk >= 62;
    const color = risk == null ? '#7693a3' : high ? '#ff5e63' : warning ? '#ffb74d' : '#36e0d0';
    $('riskGauge').style.setProperty('--risk', risk ?? 0);
    $('riskGauge').style.background = `conic-gradient(from 220deg, ${color} calc(${risk ?? 0} * 2.8deg), rgba(101,139,157,.12) 0 280deg, transparent 0)`;
    $('riskLabel').textContent = risk == null ? '等待推理' : high ? '高风险' : warning ? '中高风险' : '状态稳定';
    $('riskAdvice').textContent = risk == null ? '已收到脑电，尚无推理结果' : high ? '建议触发人工复核' : warning ? '建议加强观察' : '保持常规监测';
    $('decisionText').textContent = risk == null ? '等待模型推理结果' : high && tracked.highDuration >= 30 ? '预警待复核 · 建议准备交班' : high ? '高风险观察 · 等待持续时间确认' : warning ? '持续观察 · 尚未触发交班预警' : '正常监测 · 无需干预';
    $('riskLabel').style.color = color; $('decisionStrip').style.borderColor = color;
    $('currentPoint').style.color = color;
    $('currentPoint').setAttribute('fill', color);
    $('currentPoint').setAttribute('stroke', color);
    const velocity = number(data.velocity);
    $('currentPoint').style.display = risk == null || velocity == null ? 'none' : '';
    if (risk != null && velocity != null) $('currentPoint').setAttribute('transform', `translate(${54 + Math.max(0, Math.min(100, risk)) / 100 * 442} ${224 - Math.min(.5, velocity) / .5 * 190})`);
  }
  function simulate() {
    window.EEGVisual?.update({demo:true,channels:['F3','Fz','F4','C3','Cz','C4','P3','P4'],eeg:Array.from({length:8},(_,i)=>Math.sin(Date.now()/500+i)*20)});
    state.risk = Math.max(38, Math.min(94, state.risk + jitter(7)));
    state.distance = Math.max(.35, Math.min(.98, state.distance + jitter(.055)));
    state.attention = Math.max(24, Math.min(82, 100 - state.risk + jitter(8)));

    state.quality = Math.round(Math.max(88, Math.min(98, state.quality + jitter(3)))); state.response = Math.round(430 + state.risk * 2.7 + jitter(30));
    renderMetrics({ ...state, velocity: Math.max(.06, Math.min(.42, .08 + state.risk / 300 + jitter(.04))) });
    $('sourceStatus').textContent = '仿真演示已开启 · 当前展示模拟数据'; $('systemStatus').textContent = '仿真演示中'; $('streamStatus').textContent = 'EEG · SIMULATED';
    $('operatorName').textContent = 'OP-017 · 模拟席位 A'; $('calibrationStatus').textContent = '仿真校准状态'; $('eegFormat').textContent = '8 通道 · 仿真输入'; $('eegSamples').textContent = Array.from({length:8}, (_,i) => `CH${i+1}: ${(Math.sin(Date.now()/500+i)*20).toFixed(2)}`).join('  ');
  }
  function acceptPacket(packet, token) {
    if (state.demo || token !== generation) return;
    if (packet && packet.device === 'Sichiray Gemini') renderCandidate(packet.candidate_inference);
    const stamp = packet && Date.parse(packet.timestamp), age = Date.now() - stamp;
    const raw = packet && packet.eeg;
    const validRaw = Array.isArray(raw) && [2, 8].includes(raw.length) && raw.every(v => number(v) != null);
    const probability = packet && number(packet.fatigue_probability), validPrediction = probability != null && probability >= 0 && probability <= 1;
    if (!packet || packet.source !== 'real' || packet.has_data !== true || !Number.isFinite(stamp) || age < -2000 || age > 10000 || (!validRaw && !validPrediction)) { latest = null; receivedAt = 0; clearEvidence(); return; }
    latest = packet; receivedAt = stamp;
    window.EEGVisual?.update(packet);
    $('eegSamples').textContent = validRaw ? raw.map((v,i) => `${packet.channels?.[i] || `CH${i+1}`}: ${v.toFixed(2)}`).join('  ') : '--';
    const optional = (key, min, max) => { const v = number(packet[key]); return v != null && v >= min && v <= max ? v : null; };
    renderMetrics({risk: validPrediction ? probability * 100 : null, distance: optional('distance',0,100), attention: optional('attention',0,100), duration: optional('duration',0,86400), quality: optional('quality',0,100), response: optional('response_ms',0,60000), workSeconds: optional('work_seconds',0,864000), velocity: optional('velocity',0,100)});
    $('sourceStatus').textContent = validPrediction ? '真实脑电接口已接收 · 显示模型推理结果' : '真实脑电接口已接收 · 等待模型推理结果';
    $('systemStatus').textContent = '真实脑电数据已接入'; $('streamStatus').textContent = 'EEG · REAL DATA';
    $('operatorName').textContent = typeof packet.operator === 'string' ? packet.operator : '当前设备';
    $('calibrationStatus').textContent = packet.calibrated === true ? '接口报告：校准完成' : '尚未确认校准';
    $('eegFormat').textContent = `${validRaw ? raw.length : "--"} 通道${number(packet.sample_rate_hz) != null ? ` · ${packet.sample_rate_hz} Hz` : ''}`;
    if (packet.device === 'Sichiray Gemini') {
      const wear = packet.wear_status === 'failed' ? '佩戴失败' : packet.wear_status === 'ok' ? '佩戴正常' : `佩戴状态待确认（${packet.wear_code}）`;
      $('operatorName').textContent = 'Sichiray 双子座 · Fp1 / Fp2';
      $('calibrationStatus').textContent = `${wear} · 电池 ${number(packet.battery_voltage) ?? '--'} V`;
      $('eegFormat').textContent = `2 通道 · 硬件 250 Hz · 串口 ${number(packet.stream_rate_hz) ?? '--'} 包/s · ADC 原始计数`;
      $('eegSamples').textContent += ` | 设备专注度 ${number(packet.device_attention) ?? '--'} · 放松度 ${number(packet.device_relaxation) ?? '--'}（设备原值）`;
      $('sourceStatus').textContent = `头环实时读取 · ${wear} · 已接收 ${packet.sample_count} 包`;
      const candidate = packet.candidate_inference;
      const active = candidate?.status === 'fatigue_inference';
      const score = active ? number(candidate.drowsy_model_score) : null;
      const label = {drowsy:'倾向疲劳',alert:'倾向清醒',uncertain:'暂不确定'}[candidate?.fatigue_tendency];
      $('riskAdvice').textContent = active ? 'SADT 双通道分类器 · 头环实验性结果' : candidate?.message || '等待疲劳分类结果';
      $('riskScore').textContent = score == null ? '--' : Math.round(score*100);
      $('riskLabel').textContent = active ? label : '等待判定';
      const color = candidate?.fatigue_tendency === 'drowsy' ? '#ffb74d' : candidate?.fatigue_tendency === 'alert' ? '#36e0d0' : '#7693a3';
      $('riskLabel').style.color = color;
      $('riskGauge').style.background = `conic-gradient(from 220deg, ${color} calc(${score == null ? 0 : score*100} * 2.8deg), rgba(101,139,157,.12) 0 280deg, transparent 0)`;
      $('decisionText').textContent = active ? `${label} · 分类分数 ${Math.round(score*100)}/100 · 实验结果` : candidate?.message || '等待模型所需数据';
    }

  }
  function disconnect() {
    resetEpisode();
    generation += 1; controller?.abort(); controller = null;
    if (socket) { socket.onmessage = null; socket.onclose = null; socket.onerror = null; socket.close(); socket = null; }
    latest = null; receivedAt = 0; polling = false;
  }
  async function poll() {
    if (state.demo || socket || polling || !endpoint) return;
    if (!localService && endpoint === './api/eeg/latest') return;
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
  setInterval(() => { if (state.demo) simulate(); else if (!socket) { if (/^wss?:/i.test(endpoint)) connect(); else poll(); } },250);
})();
