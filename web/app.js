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
  const selected = papers.filter(p => (filter === 'all' || (filter === 'indexed' ? p.status === 'indexed' : p.status !== 'indexed' || !p.valid_pdf)) && terms.every(t => [p.title, ...p.authors, p.filename, p.arxiv_id || '', p.abstract].join(' ').toLocaleLowerCase().includes(t)));
  selected.sort((a,b) => {
    let av = sort === 'authors' ? a.authors[0] || '' : a[sort];
    let bv = sort === 'authors' ? b.authors[0] || '' : b[sort];
    if (!av && bv) return 1;
    if (av && !bv) return -1;
    const c = sort === 'mtime' ? av - bv : collator.compare(av || '', bv || '');
    return (ascending ? c : -c) || collator.compare(a.filename, b.filename);
  });
  $('papers').replaceChildren();
  const fragment = document.createDocumentFragment();
  for (const p of selected) {
    const row = el('tr'), info = el('td'), file = el('td', 'file'), date = el('td', 'date'), actions = el('td', 'actions');
    const title = el('button', 'paper-title', p.title || 'Metadata not yet available');
    title.addEventListener('click', () => openPaper(p, title));
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
    file.append(el('div', 'filename', p.filename), el('div', 'file-meta', `${(p.size/1024/1024).toFixed(1)} MB${p.arxiv_id ? ' · ' + p.arxiv_id : ''}`));
    file.title = p.path;
    if (p.status !== 'indexed' || !p.valid_pdf) file.append(el('span', 'badge', !p.valid_pdf ? 'Check download' : 'Needs metadata'));
    date.textContent = p.published || '—';
    const open = el('button', 'open', 'Open in Acrobat ↗');
    open.addEventListener('click', () => openPaper(p, open));
    const preview = el('a', 'preview', 'Browser preview'); preview.href = '/pdf/' + p.key; preview.target = '_blank'; preview.rel = 'noopener';
    actions.append(open, preview); row.append(info, file, date, actions); fragment.append(row);
  }
  $('papers').append(fragment);
  $('results').textContent = `${selected.length} of ${papers.length} files`;
  $('empty').hidden = selected.length > 0;
  $('direction').textContent = ascending ? '↑' : '↓';
}
async function post(path) {
  const response = await fetch(path, {method:'POST', headers:{'X-Shelf-Token':token}});
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
async function refresh() {
  clearTimeout(timer);
  try {
    const response = await fetch('/api/papers');
    if (!response.ok) throw new Error('Could not load the library.');
    const data = await response.json(); token = data.token;
    const changed = JSON.stringify(papers) !== JSON.stringify(data.papers);
    papers = data.papers;
    $('count').textContent = `${papers.length} papers on your shelf`;
    $('folder').textContent = data.directory;
    $('status').textContent = data.scanning ? data.message + '…' : data.message;
    $('updated').textContent = data.last_scan ? 'Last scan ' + data.last_scan : '';
    $('rescan').disabled = data.scanning;
    $('rescan').textContent = data.scanning ? 'Scanning…' : '↻ Rescan folder';
    if (data.error) showError(data.error);
    if (changed || !$('papers').children.length) render();
    if (data.scanning) timer = setTimeout(refresh, 1500);
  } catch(e) { showError(e.message + ' Make sure shelf.py is running.'); timer = setTimeout(refresh, 5000); }
}
$('search').addEventListener('input', render);
$('filter').addEventListener('change', render);
$('sort').addEventListener('change', () => {ascending = !['published','mtime'].includes($('sort').value); render();});
$('direction').addEventListener('click', () => {ascending = !ascending; render();});
$('rescan').addEventListener('click', async () => {try {showError(''); await post('/api/scan'); await refresh();} catch(e) {showError(e.message);}});
refresh();
