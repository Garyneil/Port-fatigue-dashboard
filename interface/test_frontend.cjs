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
const context = vm.createContext({document:{body:{dataset:{}},getElementById(id){assert(nodes.has(id),id);return nodes.get(id);}},location:{href:'http://127.0.0.1:8765/'},localStorage:{getItem(){return null;},setItem(){}},Date:FakeDate,Math,Number,String,Array,JSON,URL,AbortController,WebSocket:FakeSocket,fetch(url,options){return new Promise(resolve=>requests.push({url,options,resolve}));},setTimeout(){return 1;},clearTimeout(){},setInterval(fn){timers.push(fn);}});
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
  assert.equal(el('sourceStatus').textContent,'接口暂无数据传入');
  timers[1](); respond(3,packet({timestamp:new Date(now-20000).toISOString(),fatigue_probability:.95})); await flush();
  assert.equal(el('riskScore').textContent,'--','Reject stale server data');
  el('interfaceUrl').value='ws://127.0.0.1:8766';el('interfaceForm').events.submit({preventDefault(){}});
  sockets[0].onmessage({data:JSON.stringify(packet({fatigue_probability:.42}))});
  assert.equal(el('riskScore').textContent,42);
  sockets[0].onmessage({data:'invalid JSON'});assert.equal(el('riskScore').textContent,'--');
  el('demoToggle').events.click();assert(sockets[0].closed);
  console.log('PASS: default real mode, no data, demo toggle, race isolation, real EEG, real probability, stale data, WebSocket and malformed messages.');
})().catch(e=>{console.error(e);process.exitCode=1;});
