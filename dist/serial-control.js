(() => {
  const button = document.getElementById('serialToggle');
  const label = document.getElementById('serialStatus');
  const recalibrate = document.getElementById('recalibrateButton');
  if (!['127.0.0.1','localhost','[::1]'].includes(location.hostname)) {
    button.textContent = '真实设备请使用本地包';
    label.textContent = '下载并启动 Windows 演示包后，可连接头环。';
    return;
  }
  let enabled = false, busy = false;
  function render(data) {
    enabled = data.enabled;
    button.textContent = enabled ? '关闭串口' : '打开串口';
    button.disabled = false;
    recalibrate.disabled = !enabled;
    const status = {closed:'已关闭，可供其他软件使用', streaming:'正在接收数据', waiting:'正在连接／等待数据', disconnected:'连接失败，正在重试（可关闭）'};
    label.textContent = `${data.port} · ${status[data.connection_status] || data.connection_status}`;
  }
  async function refresh() {
    if (busy) return;
    busy = true;
    try {
      const response = await fetch('/api/serial/status', {cache:'no-store'});
      if (!response.ok) throw Error();
      render(await response.json());
    } catch (_) {
      button.disabled = true; button.textContent = '串口控制不可用';
      recalibrate.disabled = true;
      label.textContent = '请使用本机头环服务打开此页面';
    } finally { busy = false; }
  }
  button.addEventListener('click', async () => {
    if (busy) return;
    busy = true; button.disabled = true;
    button.textContent = enabled ? '正在关闭…' : '正在打开…';
    try {
      const response = await fetch(`/api/serial/${enabled ? 'close' : 'open'}`, {
        method:'POST', headers:{'X-Serial-Control':'1'}
      });
      if (!response.ok) throw Error();
      render(await response.json());
    } catch (_) {
      label.textContent = '操作失败，请重试或检查本机服务';
      button.textContent = enabled ? '关闭串口' : '打开串口'; button.disabled = false;
    } finally { busy = false; }
  });
  recalibrate.addEventListener('click', async () => {
    if (busy) return;
    busy = true;
    recalibrate.disabled = true;
    try {
      const response = await fetch('/api/model/recalibrate', {
        method:'POST', headers:{'X-Serial-Control':'1'}
      });
      if (!response.ok) throw Error();
      label.textContent = '重新校准已开始，正在采集新的个人参考。';
    } catch (_) {
      label.textContent = '重新校准失败，请检查本机服务后重试。';
    } finally {
      busy = false;
      recalibrate.disabled = !enabled;
    }
  });
  refresh(); setInterval(refresh,1000);
})();
