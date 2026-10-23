(() => {
  const button = document.getElementById('serialToggle');
  const label = document.getElementById('serialStatus');
  let enabled = false, busy = false;
  function render(data) {
    enabled = data.enabled;
    button.textContent = enabled ? '关闭串口' : '打开串口';
    button.disabled = false;
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
  refresh(); setInterval(refresh,1000);
})();
