// Run: node interface/test_frontend.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'dist/index.html'), 'utf8');
const script = fs.readFileSync(path.join(root, 'dist/app.js'), 'utf8');
const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map(m => m[1]);
const nodes = new Map(ids.map(id => [id, { textContent:'', innerHTML:'', value:'', disabled:false, attrs:{}, events:{}, style:{setProperty(){}}, setAttribute(k,v){this.attrs[k]=v;}, addEventListener(k,v){this.events[k]=v;} }]));
const timers = [], requests = [], sockets = [];
let now = 1800000000000;
class FakeDate extends Date { constructor(...args){super(...(args.length ? args : [now]));} static now(){return now;} }
class FakeSocket { constructor(url){this.url=url;sockets.push(this);} close(){this.closed=true;} }
const context = vm.createContext({window:{},document:{body:{dataset:{}},getElementById(id){assert(nodes.has(id),id);return nodes.get(id);}},location:{href:'http://127.0.0.1:8765/'},localStorage:{getItem(){return null;},setItem(){}},Date:FakeDate,Math,Number,String,Array,JSON,URL,AbortController,WebSocket:FakeSocket,fetch(url,options){if(url==='/api/model/verification')return Promise.resolve({ok:true,json:async()=>({replays:[]})});return new Promise(resolve=>requests.push({url,options,resolve}));},setTimeout(){return 1;},clearTimeout(){},setInterval(fn){timers.push(fn);}});
const el = id => nodes.get(id);
const flush = () => new Promise(resolve => setImmediate(resolve));
const packet = extra => ({source:'real',has_data:true,timestamp:new Date(now).toISOString(),eeg:[1,2,3,4,5,6,7,8],sample_rate_hz:250,...extra});
const respond = (index, body) => requests[index].resolve({ok:true,json:async()=>body});
(async()=>{
  vm.runInContext(script,context);
  assert.equal(el('riskScore').textContent,'--');
  assert.equal(el('sourceStatus').textContent,'接口暂无数据传入');
  assert.equal(requests.length,1);
  el('demoToggle').events.click();
  assert.equal(el('demoToggle').attrs['aria-pressed'],'true');
  assert(Number.isFinite(Number(el('riskScore').textContent)));
  respond(0,packet({fatigue_probability:.01})); await flush();
  assert.equal(el('streamStatus').textContent,'EEG · SIMULATED','Late request must not overwrite demo');
  timers[1](); assert.equal(requests.length,1,'Demo must not fetch real data');
  el('demoToggle').events.click(); assert.equal(el('riskScore').textContent,'--');
  respond(1,packet()); await flush();
  assert.equal(el('riskScore').textContent,'--','Raw EEG cannot invent fatigue risk');
  assert.equal(el('riskLabel').textContent,'等待推理');
  assert(el('eegSamples').textContent.includes('CH8: 8.00'));
  timers[1](); respond(2,packet({fatigue_probability:.73})); await flush();
  assert.equal(el('riskScore').textContent,73);
  now+=11000;timers[0]();assert.equal(el('riskScore').textContent,'--');
  assert.equal(el('sourceStatus').textContent,'数据中断 · 计时暂停');
  timers[1](); respond(3,packet({timestamp:new Date(now-20000).toISOString(),fatigue_probability:.95})); await flush();
  assert.equal(el('riskScore').textContent,'--','Reject stale server data');
  el('interfaceUrl').value='ws://127.0.0.1:8766';el('interfaceForm').events.submit({preventDefault(){}});
  sockets[0].onmessage({data:JSON.stringify(packet({fatigue_probability:.42}))});
  assert.equal(el('riskScore').textContent,42);
  for (const risk of [61.9,62,81.9,82,95]) {
    sockets[0].onmessage({data:JSON.stringify(packet({fatigue_probability:risk/100,distance:.1,velocity:.2,duration:0}))});
    const expected=risk>=82?'#ff5e63':risk>=62?'#ffb74d':'#36e0d0';
    assert.equal(el('riskLabel').style.color,expected);
    assert.equal(el('currentPoint').attrs.fill,expected);
    const x=Number(el('currentPoint').attrs.transform.match(/translate\(([^ ]+)/)[1]);
    assert(Math.abs(x-(54+risk/100*442))<1e-8,'Plot must use same risk score, independent of distance');
  }
  sockets[0].onmessage({data:'invalid JSON'});assert.equal(el('riskScore').textContent,'--');
  const headset = extra => packet({device:'Sichiray Gemini', eeg:[1,2],
    monitor_seconds:754,stream_rate_hz:48,wear_code:1,
    stream_health:{estimated_missing_frames:0,time_discontinuity:false,sequence_discontinuity:false},
    candidate_inference:{status:'fatigue_inference',model:'SADT 疲劳分类',
      drowsy_model_score:.37,fatigue_tendency:'alert',prediction_timestamp:now/1000}, ...extra});
  sockets[0].onmessage({data:JSON.stringify(headset())});
  assert.equal(el('riskScore').textContent,37);
  assert.equal(el('workDuration').textContent,'00:12:34');
  assert.equal(el('signalQuality').textContent,'采集正常');
  assert.equal(el('responseTime').textContent,'实时更新');
  assert.equal(el('predictionAge').textContent,'最近有效判定：0 秒前');
  sockets[0].onmessage({data:JSON.stringify(headset({candidate_inference:{
    status:'packet_loss',model:'SADT 疲劳分类',display_stale:true,
    drowsy_model_score:.37,fatigue_tendency:'alert',prediction_timestamp:now/1000-5,message:'数据缺失，显示上次结果'}}))});
  assert.equal(el('riskScore').textContent,37);
  assert.equal(el('signalQuality').textContent,'数据不连续');
  assert.equal(el('responseTime').textContent,'保留上次结果');
  assert.equal(el('predictionAge').textContent,'最近有效判定：5 秒前');
  assert.equal(el('candidateValue').textContent,'37 / 100');
  assert(el('riskAdvice').textContent.includes('上次结果'));
  sockets[0].onmessage({data:'invalid JSON'});
  assert.equal(el('riskScore').textContent,37,'Transport outage preserves last device score');
  sockets[0].onmessage({data:JSON.stringify(headset({has_data:false,candidate_inference:{
    status:'data_interrupted',model:'SADT 疲劳分类',display_stale:true,
    drowsy_model_score:.37,fatigue_tendency:'alert',message:'显示上次结果'}}))});
  assert.equal(el('riskScore').textContent,37);
  sockets[0].onmessage({data:JSON.stringify(headset({candidate_inference:{
    status:'fatigue_inference',model:'SADT 疲劳分类',drowsy_model_score:.29,fatigue_tendency:'alert',prediction_timestamp:now/1000}}))});
  assert.equal(el('riskScore').textContent,29,'Recovered inference replaces held score');
  assert.equal(el('responseTime').textContent,'实时更新');
  assert(!el('riskAdvice').textContent.includes('上次'));
  sockets[0].onmessage({data:JSON.stringify(headset({has_data:false,candidate_inference:{
    status:'waiting_for_data',model:'SADT 疲劳分类'}}))});
  assert.equal(el('riskScore').textContent,'--','Explicit stop/session reset clears previous result');
  el('demoToggle').events.click();assert(sockets[0].closed);
  const tracker=script.slice(script.indexOf('  let episode ='),script.indexOf('  function clearEvidence'));
  const trackerContext=vm.createContext({Date,Math});vm.runInContext(tracker,trackerContext);
  const track=(r,t)=>vm.runInContext(`trackRisk(${r},${t})`,trackerContext);
  assert.equal(track(62,0).duration,0);
  assert.equal(track(70,5000).duration,5);
  assert.equal(track(60,7000).duration,7,'Brief dip must retain episode');
  track(57,8000);assert.equal(track(57,17000).duration,17);
  assert.equal(track(57,18000).duration,0,'Ten seconds of recovery ends episode');
  track(82,20000);track(82,30000);track(82,40000);assert.equal(track(82,50000).highDuration,30);
  vm.runInContext('pauseEpisode()',trackerContext);
  assert.equal(track(85,90000).duration,30,'Outage must not add elapsed time');
  assert.equal(track(85,90000).highDuration,0,'High-risk confirmation restarts after outage');
  assert.equal(track(70,92000).duration,32);
  console.log('PASS: default real mode, no data, demo toggle, race isolation, real EEG, real probability, stale data, WebSocket and malformed messages.');
})().catch(e=>{console.error(e);process.exitCode=1;});
