const state = { devices: [], selected: null, history: [] };
const $ = (id) => document.getElementById(id);
const number = (value, digits = 1) => value == null ? '—' : Number(value).toFixed(digits);
const since = (value) => value ? new Date(value).toLocaleString() : 'Never';

async function json(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
}

async function load() {
  try {
    state.devices = await json('/api/devices');
    if (!state.selected && state.devices.length) state.selected = state.devices[0].device_id;
    renderDevices();
    if (state.selected) await renderDetails();
    renderEvents(await json('/api/events?limit=30'));
  } catch (error) { console.error(error); }
}

function effectiveStatus(device) {
  if (device.stale && device.status === 'online') return 'stale';
  return device.status || 'unknown';
}

function renderDevices() {
  const root = $('device-list');
  if (!state.devices.length) { root.innerHTML = '<p class="empty">Waiting for telemetry…</p>'; return; }
  root.innerHTML = state.devices.map((device) => {
    const telemetry = device.latest_telemetry || {};
    const status = effectiveStatus(device);
    return `<article class="device-card ${device.device_id === state.selected ? 'active' : ''}" data-id="${device.device_id}">
      <header><strong>${device.device_id}</strong><span class="badge ${status}">${status.toUpperCase()}</span></header>
      <p>${number(telemetry.temperature_c)} °C · ${number(telemetry.humidity_percent)}% RH</p>
      <p>Last seen ${since(device.last_seen)}</p>
    </article>`;
  }).join('');
  root.querySelectorAll('.device-card').forEach((card) => card.addEventListener('click', async () => {
    state.selected = card.dataset.id; renderDevices(); await renderDetails();
  }));
}

async function renderDetails() {
  const device = await json(`/api/devices/${state.selected}`);
  state.history = await json(`/api/devices/${state.selected}/telemetry?limit=60`);
  const t = device.latest_telemetry || {};
  $('details').classList.remove('hidden');
  $('device-name').textContent = device.device_id;
  const status = effectiveStatus(device);
  $('device-status').textContent = status.toUpperCase();
  $('device-status').className = `badge ${status}`;
  $('temperature').textContent = number(t.temperature_c);
  $('humidity').textContent = number(t.humidity_percent);
  $('pressure').textContent = number(t.pressure_hpa);
  $('rssi').textContent = t.wifi_rssi_dbm ?? '—';
  $('last-seen').textContent = since(device.last_seen);
  $('uptime').textContent = t.uptime_seconds == null ? '—' : `${t.uptime_seconds}s`;
  $('boot-id').textContent = device.boot_id || '—';
  $('sequence').textContent = device.latest_sequence ?? '—';
  $('message-count').textContent = device.message_count;
  $('duplicate-count').textContent = device.duplicate_count;
  $('rejected-count').textContent = device.rejected_count;
  drawChart(state.history);
}

function drawChart(rows) {
  const canvas = $('chart'); const ctx = canvas.getContext('2d');
  const ratio = window.devicePixelRatio || 1; const width = canvas.clientWidth; const height = 300;
  canvas.width = width * ratio; canvas.height = height * ratio; ctx.scale(ratio, ratio);
  ctx.clearRect(0, 0, width, height); ctx.strokeStyle = '#263b55'; ctx.lineWidth = 1;
  for (let y = 30; y < height; y += 55) { ctx.beginPath(); ctx.moveTo(40, y); ctx.lineTo(width - 15, y); ctx.stroke(); }
  if (rows.length < 2) return;
  const plot = (key, color, min, max) => {
    ctx.strokeStyle = color; ctx.lineWidth = 2.5; ctx.beginPath();
    rows.forEach((row, index) => {
      const x = 40 + index * (width - 60) / (rows.length - 1);
      const y = 15 + (max - row[key]) * (height - 40) / (max - min);
      index ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
    }); ctx.stroke();
  };
  plot('temperature_c', '#38d9c5', 0, 50); plot('humidity_percent', '#55a7ff', 0, 100);
}

function renderEvents(events) {
  $('events').innerHTML = events.length ? events.map((event) => `<div class="event">
    <span class="event-type">${event.event_type}</span><span>${event.device_id || 'unknown'} · ${event.detail}</span>
    <time>${since(event.received_at)}</time></div>`).join('') : '<p class="empty">No events recorded.</p>';
}

function connectStream() {
  const source = new EventSource('/api/stream');
  source.onopen = () => { $('stream-dot').className = 'dot'; $('stream-label').textContent = 'Live'; };
  source.onerror = () => { $('stream-dot').className = 'dot warn'; $('stream-label').textContent = 'Reconnecting'; };
  ['telemetry', 'status', 'config_ack', 'rejected'].forEach((type) => source.addEventListener(type, load));
}

$('refresh').addEventListener('click', load);
window.addEventListener('resize', () => drawChart(state.history));
load(); connectStream(); setInterval(load, 15000);

