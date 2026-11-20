'use strict';
const $ = id => document.getElementById(id);
const palette = ['#16a085','#e67e22','#2980b9','#9b59b6','#d35459'];
let source = null, sent = null, result = null, busy = false, ready = false;
function message(text = '') { $('message').textContent = text; }
function controls() {
  $('run').disabled = busy || !ready || !source;
  for (const id of ['apply','add']) $(id).disabled = busy || !ready;
  for (const id of ['file','size','refresh']) $(id).disabled = busy;
  document.querySelectorAll('#vocabulary input, #vocabulary button').forEach(e => e.disabled = busy || !ready);
  $('save-json').disabled = !result || busy;
  $('save-image').disabled = !result || busy;
  $('run').textContent = busy ? 'Working…' : 'Detect ↗';
}
async function api(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const errors = {429:'The server is busy. Wait a moment and try again.',503:'Detection is disabled. Start the detector container (make up).',413:'The sent image is too large. Reduce the sent size.'};
    let detail = '';
    try { detail = JSON.stringify((await response.json()).detail); } catch { /* Non-JSON server error. */ }
    throw new Error(errors[response.status] || `HTTP ${response.status}: ${detail || 'An error occurred on the server. Check the logs.'}`);
  }
  return response.json();
}
function addRow(entry = {prompt:'',label:''}) {
  const row = document.createElement('div'); row.className = 'vocab-row';
  for (const key of ['prompt','label']) {
    const input = document.createElement('input'); input.value = entry[key]; input.dataset.key = key;
    input.setAttribute('aria-label', key === 'prompt' ? 'English description' : 'Category name'); row.append(input);
  }
  const remove = document.createElement('button'); remove.textContent = '×'; remove.setAttribute('aria-label','Delete this row');
  remove.onclick = () => row.remove(); row.append(remove); $('vocabulary').append(row);
}
async function refresh() {
  busy = true; controls(); message();
  try {
    const status = await api('/detect/status'); ready = status.enabled;
    $('status').textContent = ready ? '● Connected to the detection server' : '○ Detection disabled';
    $('status').className = `badge ${ready ? 'ready' : ''}`;
    if (!ready) throw new Error('Detection is disabled. Start the detector container (make up).');
    $('config').textContent = `Device: ${status.device} / Inference size: ${status.imgsz} / Confidence threshold: ${status.conf}`;
    const vocabulary = await api('/detect/vocabulary');
    $('vocabulary').replaceChildren(); vocabulary.entries.forEach(addRow);
  } catch (error) { ready = false; $('status').className = 'badge'; $('status').textContent = '○ Detection unavailable'; message(error.message); }
  finally { busy = false; controls(); }
}
function resetResult() {
  result = null; sent = null; $('count').textContent = $('elapsed').textContent = $('dimensions').textContent = '—';
  $('json').textContent = 'Not run yet.'; $('results').replaceChildren();
}
function draw() {
  const image = sent || source; if (!image) return;
  const canvas = $('canvas'); canvas.width = image.width; canvas.height = image.height;
  const ctx = canvas.getContext('2d'); ctx.drawImage(image,0,0);
  if (result && $('boxes').checked) result.predictions.forEach((p,i) => {
    const [x1,y1,x2,y2] = p.box; const color = palette[i % palette.length];
    const fontSize = Math.max(14,canvas.width / 60);
    ctx.strokeStyle = color; ctx.lineWidth = Math.max(2,canvas.width / 400); ctx.strokeRect(x1,y1,x2-x1,y2-y1);
    ctx.font = `600 ${fontSize}px sans-serif`; const label = `${p.label} ${(p.score*100).toFixed(1)}%`;
    const w = ctx.measureText(label).width + 12, h = fontSize + 10;
    const x = Math.max(0,Math.min(x1,canvas.width-w)), y = Math.max(0,y1-h);
    ctx.fillStyle = color; ctx.fillRect(x,y,w,h); ctx.fillStyle = '#fff'; ctx.fillText(label,x+6,y+fontSize+2);
  });
  canvas.hidden = false; $('placeholder').hidden = true;
}
async function choose(file) {
  if (!file || busy) return;
  busy = true; controls(); message();
  try {
    if (!['image/jpeg','image/png','image/webp'].includes(file.type)) throw new Error('Choose a JPEG, PNG or WebP.');
    if (file.size > 40 * 1024 * 1024) throw new Error('Image files must be 40 MiB or less.');
    const next = await createImageBitmap(file);
    if (next.width * next.height > 40_000_000) { next.close(); throw new Error('Images must be 40 megapixels or less.'); }
    source?.close(); source = next; resetResult(); $('filename').textContent = file.name; draw();
  } catch (error) { message(error.message); }
  finally { $('file').value = ''; busy = false; controls(); }
}
$('file').onchange = event => choose(event.target.files[0]);
$('drop').onkeydown = event => { if (event.key === 'Enter' || event.key === ' ') {event.preventDefault(); if (!busy) $('file').click();} };
for (const name of ['dragover','dragleave','drop']) $('drop').addEventListener(name,event => {
  event.preventDefault(); $('drop').classList.toggle('over',name === 'dragover');
  if (name === 'drop') choose(event.dataTransfer.files[0]);
});
$('size').onchange = () => { resetResult(); draw(); controls(); };
$('boxes').onchange = draw;
$('refresh').onclick = refresh;
$('add').onclick = () => addRow();
$('apply').onclick = async () => {
  const entries = [...document.querySelectorAll('.vocab-row')].map(row => Object.fromEntries([...row.querySelectorAll('input')].map(input => [input.dataset.key,input.value.trim()])));
  if (!entries.length || entries.some(e => !e.prompt || !/^[a-z][a-z0-9_]*$/.test(e.label))) { message('Enter an English description and a category name. Category names use lowercase letters, digits and _, and must start with a letter.'); return; }
  busy = true; controls(); message();
  try { await api('/detect/vocabulary',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({entries})}); resetResult(); draw(); message('Vocabulary applied. You can re-run detection on the image.'); }
  catch(error) { message(error.message); }
  finally { busy = false; controls(); }
};
$('run').onclick = async () => {
  if (busy || !source || !ready) return;
  busy = true; resetResult(); draw(); controls(); message();
  try {
    const max = Number($('size').value), scale = max ? Math.min(1,max / Math.max(source.width,source.height)) : 1;
    const input = document.createElement('canvas'); input.width = Math.max(1,Math.round(source.width*scale)); input.height = Math.max(1,Math.round(source.height*scale));
    if (input.width * input.height > 16_000_000) throw new Error('Sent images must be 16 megapixels or less.');
    const ctx = input.getContext('2d'); ctx.fillStyle = '#fff'; ctx.fillRect(0,0,input.width,input.height); ctx.drawImage(source,0,0,input.width,input.height);
    const blob = await new Promise(resolve => input.toBlob(resolve,'image/jpeg',0.9));
    if (!blob) throw new Error('JPEG conversion failed.');
    sent = input; draw(); $('dimensions').textContent = `${input.width} × ${input.height}`;
    const start = performance.now();
    result = await api('/detect',{method:'POST',headers:{'Content-Type':'image/jpeg'},body:blob});
    $('elapsed').textContent = `${Math.round(performance.now()-start)} ms`; $('count').textContent = result.predictions.length;
    $('json').textContent = JSON.stringify(result,null,2); $('results').replaceChildren();
    if (!result.predictions.length) $('results').textContent = 'No detections. Try a different vocabulary or image.';
    result.predictions.forEach((p,i) => {
      const row = document.createElement('div'); row.className = 'result-row';
      const label = document.createElement('span'), swatch = document.createElement('span'); swatch.className = 'swatch'; swatch.style.background = palette[i%palette.length];
      label.append(swatch,document.createTextNode(p.label)); const score = document.createElement('strong'); score.textContent = `${(p.score*100).toFixed(1)}%`; row.append(label,score); $('results').append(row);
    }); draw();
  } catch(error) { message(error.message); }
  finally { busy = false; controls(); }
};
function download(blob,name) { const url = URL.createObjectURL(blob); const link = document.createElement('a'); link.href = url; link.download = name; link.click(); setTimeout(() => URL.revokeObjectURL(url),1000); }
$('save-json').onclick = () => download(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}),'predictions.json');
$('save-image').onclick = () => { const previous = $('boxes').checked; $('boxes').checked = true; draw(); $('canvas').toBlob(blob => { if (blob) download(blob,'detection.png'); }); $('boxes').checked = previous; draw(); };
// --- Live: what clients (the Quest) are sending to POST /detect ---
let liveTime = null;
function boxes(ctx, canvas, predictions) {
  predictions.forEach((p,i) => {
    const [x1,y1,x2,y2] = p.box; const color = palette[i % palette.length];
    const fontSize = Math.max(14,canvas.width / 40);
    ctx.strokeStyle = color; ctx.lineWidth = Math.max(2,canvas.width / 300); ctx.strokeRect(x1,y1,x2-x1,y2-y1);
    ctx.font = `600 ${fontSize}px sans-serif`; const label = `${p.label} ${(p.score*100).toFixed(0)}%`;
    const w = ctx.measureText(label).width + 12, h = fontSize + 10;
    const x = Math.max(0,Math.min(x1,canvas.width-w)), y = Math.max(0,y1-h);
    ctx.fillStyle = color; ctx.fillRect(x,y,w,h); ctx.fillStyle = '#fff'; ctx.fillText(label,x+6,y+fontSize+2);
  });
}
async function pollLive() {
  try {
    const live = await (await fetch('/detect/live', {cache:'no-store'})).json();
    const client = live.clients[0];
    if (!client) { $('live-status').textContent = 'No requests yet'; $('live-status').className = 'badge'; return; }
    const active = client.last_seen_ago < 3;
    $('live-status').textContent = active ? `● Receiving from ${client.host}` : `○ Last request ${client.last_seen_ago}s ago`;
    $('live-status').className = `badge ${active ? 'ready' : ''}`;
    $('live-clients').textContent = live.clients.map(c =>
      `${c.host}: ${c.requests} requests (ok ${c.ok}, busy/429 ${c.busy}, errors ${c.errors}, last status ${c.last_status}), last ${c.last_seen_ago}s ago`).join(' · ');
    $('live-fps').textContent = live.fps.toFixed(1);
    const last = live.last; if (!last) return;
    $('live-infer').textContent = `${Math.round(last.infer_ms)} ms`;
    $('live-size').textContent = last.size ? `${last.size[0]} × ${last.size[1]}` : '—';
    if (last.time === liveTime) return;
    liveTime = last.time;
    const image = await createImageBitmap(await (await fetch('/detect/live.jpg', {cache:'no-store'})).blob());
    const canvas = $('live-canvas'); canvas.width = image.width; canvas.height = image.height;
    const ctx = canvas.getContext('2d'); ctx.drawImage(image,0,0); image.close(); boxes(ctx, canvas, last.predictions);
    canvas.hidden = false; $('live-placeholder').hidden = true;
    $('live-results').replaceChildren();
    if (!last.predictions.length) $('live-results').textContent = 'No detections in the latest frame.';
    last.predictions.forEach((p,i) => {
      const row = document.createElement('div'); row.className = 'result-row';
      const label = document.createElement('span'), swatch = document.createElement('span'); swatch.className = 'swatch'; swatch.style.background = palette[i%palette.length];
      label.append(swatch,document.createTextNode(p.label)); const score = document.createElement('strong'); score.textContent = `${(p.score*100).toFixed(1)}%`; row.append(label,score); $('live-results').append(row);
    });
  } catch { /* Server restarting; try again next tick. */ }
  finally { setTimeout(pollLive, 700); }
}
refresh();
pollLive();
