const $ = (s) => document.querySelector(s);
const state = { sector: 'all', status: 'all', q: '' };
let sectors = {};

const esc = (s) =>
  String(s == null ? '' : s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const cls = (s) => 'st st-' + String(s).replace(/\s+/g, '-').toLowerCase();

async function init() {
  const cfg = await fetch('/api/config').then((r) => r.json());
  sectors = cfg.sectors;

  const mode = $('#mode');
  if (cfg.live) {
    mode.textContent = 'LIVE — pulling real jobs';
    mode.className = 'badge live';
  } else {
    mode.textContent = 'SAMPLE DATA — add Adzuna keys in .env for real jobs (see SETUP.md)';
    mode.className = 'badge sample';
  }

  const sel = $('#sector');
  sel.innerHTML =
    '<option value="all">All sectors</option>' +
    Object.entries(sectors).map(([k, v]) => `<option value="${k}">${esc(v)}</option>`).join('') +
    '<option value="other">Other</option>';
  sel.onchange = () => { state.sector = sel.value; load(); };
  $('#status').onchange = (e) => { state.status = e.target.value; load(); };
  $('#q').oninput = (e) => { state.q = e.target.value; load(); };

  $('#refresh').onclick = async () => {
    const btn = $('#refresh');
    btn.disabled = true;
    btn.textContent = 'Checking…';
    const r = await fetch('/api/refresh', { method: 'POST' }).then((x) => x.json());
    btn.disabled = false;
    btn.textContent = 'Check for new jobs';
    alert(
      r.mode === 'live'
        ? `${r.added} new job(s) found. ${r.total} leads in total.`
        : 'Sample mode: no live jobs. Add Adzuna keys in .env (see SETUP.md).'
    );
    load();
  };

  load();
}

async function load() {
  const jobs = await fetch('/api/leads?' + new URLSearchParams(state)).then((r) => r.json());
  $('#count').textContent = jobs.length + ' lead' + (jobs.length === 1 ? '' : 's');
  const tb = $('#rows');
  tb.innerHTML = '';
  if (!jobs.length) {
    tb.innerHTML = '<tr><td colspan="9">No leads match this filter yet.</td></tr>';
    return;
  }
  jobs.forEach((j) => tb.appendChild(row(j)));
}

function row(j) {
  const tr = document.createElement('tr');
  const posted = j.posted
    ? new Date(j.posted).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })
    : '';

  tr.innerHTML =
    `<td>${esc(posted)}</td>` +
    `<td>${j.url ? `<a href="${esc(j.url)}" target="_blank" rel="noopener">${esc(j.title)}</a>` : esc(j.title)}` +
    `<div class="sub">${esc(j.source || '')}</div></td>` +
    `<td>${esc(j.company)}</td>` +
    `<td>${esc(j.location)}</td>` +
    `<td>${esc(j.salary || '')}</td>` +
    `<td><span class="tag">${esc(sectors[j.sector] || j.sector)}</span></td>` +
    `<td class="c-status"></td><td class="c-contact"></td><td class="c-notes"></td>`;

  // Status dropdown
  const st = document.createElement('select');
  ['New', 'Calling today', 'Called', 'Left message', 'Emailed', 'Not relevant', 'Client won'].forEach((o) => {
    const op = document.createElement('option');
    op.value = o;
    op.textContent = o;
    if (o === j.status) op.selected = true;
    st.appendChild(op);
  });
  st.className = cls(j.status);
  st.onchange = () => {
    st.className = cls(st.value);
    save(j.id, { status: st.value });
  };
  tr.querySelector('.c-status').appendChild(st);

  // HR contact name + phone
  const c = tr.querySelector('.c-contact');
  c.innerHTML =
    `<input class="in" placeholder="HR name" value="${esc(j.contact || '')}">` +
    `<input class="in" placeholder="Phone" value="${esc(j.phone || '')}">`;
  const [cName, cPhone] = c.querySelectorAll('input');
  cName.onchange = () => save(j.id, { contact: cName.value });
  cPhone.onchange = () => save(j.id, { phone: cPhone.value });

  // Notes
  const n = tr.querySelector('.c-notes');
  n.innerHTML = `<textarea class="in notes" placeholder="Call notes">${esc(j.notes || '')}</textarea>`;
  n.querySelector('textarea').onchange = (e) => save(j.id, { notes: e.target.value });

  return tr;
}

function save(id, patch) {
  fetch('/api/leads/' + encodeURIComponent(id), {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch)
  }).catch(() => {});
}

init();
