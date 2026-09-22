'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

class Element {
  constructor(tag) { this.tag = tag; this.children = []; this.value = ''; this.disabled = false; }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = nodes; }
  setAttribute() {}
  addEventListener() {}
}
function setup() {
  const elements = {};
  const document = {
    getElementById: id => elements[id] ||= new Element('div'),
    createElement: tag => new Element(tag),
    createDocumentFragment: () => new Element('fragment'),
  };
  const context = vm.createContext({document, console, Intl, setTimeout: () => 1, clearTimeout() {}});
  const source = fs.readFileSync('web/app.js', 'utf8').replace(/refresh\(\);\s*$/, '');
  vm.runInContext(source, context);
  elements.search.value = ''; elements.filter.value = 'all'; elements.sort.value = 'title';
  const missing = {key:'catalog-id', catalog_key:'catalog-id', arxiv_id:'1410.7698', title:'Paper',
    authors:[], filename:'1410.7698.pdf', available:false, status:'indexed', valid_pdf:true};
  const evaluate = code => vm.runInContext(code, context);
  context.fixture = missing;
  evaluate('papers = [fixture]; render();');
  function find(predicate, node = elements.papers) {
    if (predicate(node)) return node;
    for (const child of node.children || []) { const found = find(predicate, child); if (found) return found; }
  }
  return {context, evaluate, elements, missing, find};
}

test('download shows progress and changes to Open PDF after indexed success', async () => {
  const ui = setup();
  let finish;
  ui.context.fetch = async path => {
    if (path.startsWith('/api/download/')) return new Promise(resolve => { finish = resolve; });
    return {ok:true, json:async () => ({papers:[{...ui.missing, key:'local-id', available:true, size:100}],
      download:{key:'catalog-id', status:'complete'}, token:'token', message:'Ready'})};
  };
  const pending = ui.evaluate('downloadPaper(papers[0])');
  assert.match(ui.find(n => n.className === 'open').textContent, /Connecting/);
  assert.equal(ui.find(n => n.className === 'open').disabled, true);
  ui.evaluate("download = {key:'catalog-id',status:'downloading',bytes:50,total:100}; render();");
  assert.match(ui.find(n => n.className === 'open').textContent, /50%/);
  assert.equal(ui.find(n => n.tag === 'progress').value, 50);
  finish({ok:true, json:async () => ({ok:true})});
  await pending;
  const button = ui.find(n => n.className === 'open');
  assert.equal(button.textContent, 'Open PDF ↗');
  assert.equal(button.disabled, false);
  assert.equal(ui.find(n => n.className === 'preview').href, '/pdf/local-id');
  assert.equal(ui.find(n => n.tag === 'progress'), undefined);
});

test('failed download stays visible and offers retry', async () => {
  const ui = setup();
  ui.context.fetch = async path => path.startsWith('/api/download/')
    ? {ok:false, json:async () => ({error:'Download rejected'})}
    : {ok:true, json:async () => ({papers:[ui.missing], token:'token', message:'Ready',
        download:{key:'catalog-id',status:'failed',error:'Download rejected'}})};
  await ui.evaluate('downloadPaper(papers[0])');
  assert.equal(ui.find(n => n.className === 'open').textContent, '↓ Download PDF');
  assert.equal(ui.find(n => n.className === 'open').disabled, false);
  assert.equal(ui.elements.error.textContent, 'Download rejected');
  assert.ok(ui.find(n => n.className === 'download-error'));
});
