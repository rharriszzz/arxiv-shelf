'use strict';
const $ = id => document.getElementById(id);
const collator = new Intl.Collator(undefined, {numeric:true, sensitivity:'base'});
let papers = [], ascending = false;

function el(tag, cls, text) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text) node.textContent = text;
  return node;
}
function ratingFor(key) {
  const ratings = JSON.parse(localStorage.getItem('arxiv-shelf-ratings') || '{}');
  return Number(ratings[key] || 0);
}
function saveRating(key, value) {
  const ratings = JSON.parse(localStorage.getItem('arxiv-shelf-ratings') || '{}');
  if (value) ratings[key] = value;
  else delete ratings[key];
  localStorage.setItem('arxiv-shelf-ratings', JSON.stringify(ratings));
}
function render() {
  const terms = $('search').value.toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
  const filter = $('filter').value, sort = $('sort').value;
  const selected = papers.filter(p => {
    const rating = ratingFor(p.catalog_key);
    const matchesFilter = filter === 'all' || (filter === 'rated' ? rating > 0 : rating === 0);
    const text = [p.title, ...(p.authors || []), ...(p.filenames || []), p.arxiv_id || '', p.abstract || ''].join(' ').toLocaleLowerCase();
    return matchesFilter && terms.every(term => text.includes(term));
  });
  selected.sort((a, b) => {
    let av = sort === 'authors' ? (a.authors || [])[0] || '' : sort === 'rating' ? ratingFor(a.catalog_key) : a[sort] || '';
    let bv = sort === 'authors' ? (b.authors || [])[0] || '' : sort === 'rating' ? ratingFor(b.catalog_key) : b[sort] || '';
    if (!av && bv) return 1;
    if (av && !bv) return -1;
    const c = sort === 'rating' ? av - bv : collator.compare(String(av), String(bv));
    return (ascending ? c : -c) || collator.compare(a.title || '', b.title || '');
  });
  const body = $('papers');
  body.replaceChildren();
  const fragment = document.createDocumentFragment();
  for (const p of selected) {
    const row = el('tr'), info = el('td'), file = el('td', 'file'), date = el('td', 'date'), actions = el('td', 'actions');
    const title = el('a', 'paper-title', p.title || 'Title unavailable');
    title.href = p.arxiv_id ? `https://arxiv.org/abs/${encodeURI(p.arxiv_id)}` : '#';
    title.target = '_blank'; title.rel = 'noopener';
    info.append(title, el('div', 'authors', (p.authors || []).join(', ') || 'Authors unavailable'));
    if (p.abstract) {
      const details = el('details');
      details.append(el('summary', '', 'Abstract'));
      details.append(el('p', '', p.abstract));
      info.append(details);
    }
    const rating = el('select', 'rating');
    rating.setAttribute('aria-label', `Rating for ${p.title || p.arxiv_id || 'paper'}`);
    for (let n = 0; n <= 5; n++) { const option = el('option', '', n ? '★'.repeat(n) : 'Not rated'); option.value = n; rating.append(option); }
    rating.value = ratingFor(p.catalog_key);
    rating.addEventListener('change', () => { saveRating(p.catalog_key, Number(rating.value)); render(); });
    info.append(rating);
    file.append(el('div', 'filename', (p.filenames || []).join(', ') || 'Filename unavailable'));
    if (p.arxiv_id) file.append(el('div', 'file-meta', p.arxiv_id));
    date.textContent = p.published || '—';
    if (p.arxiv_id) {
      const pdf = el('a', 'open', 'Open PDF ↗');
      pdf.href = `https://arxiv.org/pdf/${encodeURI(p.arxiv_id)}`;
      pdf.target = '_blank'; pdf.rel = 'noopener'; actions.append(pdf);
    }
    row.append(info, file, date, actions); fragment.append(row);
  }
  body.append(fragment);
  $('results').textContent = `${selected.length} of ${papers.length} papers`;
  $('empty').hidden = selected.length > 0;
  $('direction').textContent = ascending ? '↑' : '↓';
}
async function start() {
  try {
    const response = await fetch('/catalog.json', {cache:'no-store'});
    if (!response.ok) throw new Error('The catalog could not be loaded.');
    const catalog = await response.json();
    papers = Object.values(catalog.papers || {});
    $('count').textContent = `${papers.length} ${papers.length === 1 ? 'paper' : 'papers'} on your shelf`;
    $('updated').textContent = catalog.updated ? `Catalog snapshot · ${catalog.updated}` : 'Catalog snapshot';
    $('status').textContent = 'Choose a paper to read its abstract or open it on arXiv.';
    render();
  } catch (error) {
    $('count').textContent = 'Library unavailable';
    $('error').textContent = error.message;
    $('error').hidden = false;
  }
}
$('search').addEventListener('input', render);
$('filter').addEventListener('change', render);
$('sort').addEventListener('change', () => { ascending = !['published','rating'].includes($('sort').value); render(); });
$('direction').addEventListener('click', () => { ascending = !ascending; render(); });
start();
