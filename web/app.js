'use strict';
const $ = id => document.getElementById(id);
let papers = [], token = '', ascending = false, timer;
const collator = new Intl.Collator(undefined, {numeric: true, sensitivity: 'base'});
function el(tag, cls, text) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text) node.textContent = text;
  return node;
}
function render() {
  const terms = $('search').value.toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
  const filter = $('filter').value, sort = $('sort').value;
  const selected = papers.filter(p => (filter === 'all' || (filter === 'local' ? p.available : filter === 'missing' ? !p.available : filter === 'rated' ? p.rating > 0 : filter === 'indexed' ? p.status === 'indexed' : p.status !== 'indexed' || !p.valid_pdf)) && terms.every(t => [p.title, ...p.authors, p.filename, p.arxiv_id || '', p.abstract].join(' ').toLocaleLowerCase().includes(t)));
  selected.sort((a,b) => {
    let av = sort === 'authors' ? a.authors[0] || '' : a[sort];
    let bv = sort === 'authors' ? b.authors[0] || '' : b[sort];
    if (!av && bv) return 1;
    if (av && !bv) return -1;
    const c = ['mtime', 'rating'].includes(sort) ? av - bv : collator.compare(av || '', bv || '');
    return (ascending ? c : -c) || collator.compare(a.filename, b.filename);
  });
  $('papers').replaceChildren();
  const fragment = document.createDocumentFragment();
  for (const p of selected) {
    const row = el('tr'), info = el('td'), file = el('td', 'file'), date = el('td', 'date'), actions = el('td', 'actions');
    const title = el('button', 'paper-title', p.title || 'Metadata not yet available');
    title.addEventListener('click', () => p.available ? openPaper(p, title) : downloadPaper(p, title));
    const authorText = p.authors.length > 8 ? p.authors.slice(0, 6).join(', ') + `, +${p.authors.length - 6} more` : p.authors.join(', ');
    info.append(title, el('div', 'authors', authorText || 'Authors unavailable'));
    const details = el('details');
    details.append(el('summary', '', p.authors.length > 8 ? 'Paper details & all authors' : 'Paper details'));
    if (p.authors.length > 8) details.append(el('p', '', p.authors.join(', ')));
    if (p.abstract) details.append(el('p', '', p.abstract));
    if (p.note) details.append(el('p', 'note', p.note));
    if (p.excerpt && !p.title) details.append(el('p', '', p.excerpt));
    if (p.arxiv_id) {const link = el('a', '', 'View on arXiv ↗'); link.href = 'https://arxiv.org/abs/' + p.arxiv_id; link.target = '_blank'; link.rel = 'noopener'; details.append(link);}
    info.append(details);
    const rating = el('select', 'rating');
    rating.setAttribute('aria-label', 'Rating for ' + (p.title || p.filename));
    for (let n = 0; n <= 5; n++) { const option = el('option', '', n ? '★'.repeat(n) : 'Not rated'); option.value = n; rating.append(option); }
    rating.value = p.rating || 0;
    rating.addEventListener('change', async () => {
      rating.disabled = true;
      try {await post('/api/rate/' + p.catalog_key, {rating:Number(rating.value)}); showError(''); await refresh();}
      catch(e) {showError(e.message); rating.value = p.rating || 0;}
      finally {rating.disabled = false;}
    });
    info.append(rating);
    file.append(el('div', 'filename', p.filename), el('div', 'file-meta', `${p.available ? (p.size/1024/1024).toFixed(1) + ' MB · On this computer' : 'Not on this computer'}${p.arxiv_id ? ' · ' + p.arxiv_id : ''}`));
    file.title = p.path;
    if (p.status !== 'indexed' || !p.valid_pdf) file.append(el('span', 'badge', !p.valid_pdf ? 'Check download' : 'Needs metadata'));
    date.textContent = p.published || '—';
    const open = el('button', 'open', p.available ? 'Open in Acrobat ↗' : '↓ Download PDF');
    open.disabled = !p.available && !p.arxiv_id;
    open.addEventListener('click', () => p.available ? openPaper(p, open) : downloadPaper(p, open));
    const preview = el('a', 'preview', 'Browser preview'); preview.href = '/pdf/' + p.key; preview.target = '_blank'; preview.rel = 'noopener';
    actions.append(open); if (p.available) actions.append(preview); row.append(info, file, date, actions); fragment.append(row);
  }
  $('papers').append(fragment);
  $('results').textContent = `${selected.length} of ${papers.length} entries`;
  $('empty').hidden = selected.length > 0;
  $('direction').textContent = ascending ? '↑' : '↓';
}
async function post(path, payload) {
  const response = await fetch(path, {method:'POST', headers:{'X-Shelf-Token':token, 'Content-Type':'application/json'}, body: payload ? JSON.stringify(payload) : undefined});
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || 'Request failed');
  return body;
}
function showError(message) { $('error').textContent = message; $('error').hidden = !message; }
async function openPaper(p, button) {
  button.disabled = true;
  try { await post('/api/open/' + p.key); showError(''); }
  catch (e) { showError(e.message); }
  finally { button.disabled = false; }
}
async function downloadPaper(p, button) {
  const label = button.textContent;
  button.disabled = true; button.textContent = 'Downloading…';
  try {await post('/api/download/' + p.catalog_key); showError(''); await refresh();}
  catch(e) {showError(e.message);}
  finally {button.disabled = false; button.textContent = label;}
}
async function refresh() {
  clearTimeout(timer);
  try {
    const response = await fetch('/api/papers');
    if (!response.ok) throw new Error('Could not load the library.');
    const data = await response.json(); token = data.token;
    const changed = JSON.stringify(papers) !== JSON.stringify(data.papers);
    papers = data.papers;
    $('count').textContent = `${papers.length} ${papers.length === 1 ? "entry" : "entries"} on your shelf`;
    $('folder').textContent = data.directory;
    $('catalog').textContent = 'Catalog: ' + data.catalog;
    $('status').textContent = data.scanning ? data.message + '…' : data.message;
    $('updated').textContent = data.last_scan ? 'Last scan ' + data.last_scan : '';
    $('rescan').disabled = data.scanning || data.syncing;
    $('sync').disabled = data.scanning || data.syncing;
    $('sync').textContent = data.syncing ? 'Syncing…' : '⇅ Sync with GitHub';
    $('rescan').textContent = data.scanning ? 'Scanning…' : '↻ Rescan folder';
    if (data.error) showError(data.error);
    if (changed || !$('papers').children.length) render();
    timer = setTimeout(refresh, (data.scanning || data.syncing) ? 1500 : 10000);
  } catch(e) { showError(e.message + ' Make sure shelf.py is running.'); timer = setTimeout(refresh, 5000); }
}
$('search').addEventListener('input', render);
$('filter').addEventListener('change', render);
$('sort').addEventListener('change', () => {ascending = !['published','mtime','rating'].includes($('sort').value); render();});
$('direction').addEventListener('click', () => {ascending = !ascending; render();});
$('sync').addEventListener('click', async () => {try {showError(''); await post('/api/sync'); await refresh();} catch(e) {showError(e.message);}});
$('rescan').addEventListener('click', async () => {try {showError(''); await post('/api/scan'); await refresh();} catch(e) {showError(e.message);}});
refresh();
