const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { JSDOM } = require('jsdom');
const html = fs.readFileSync(path.join(__dirname, '../web/index.html'), 'utf8');
const script = fs.readFileSync(path.join(__dirname, '../web/app.js'), 'utf8');
const tick = () => new Promise(resolve => setTimeout(resolve, 15));
function boot() {
  const dom = new JSDOM(html, { url: 'http://sourcebook.test/', runScripts: 'outside-only' });
  const { window: w } = dom;
  w.HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open', ''); };
  w.HTMLDialogElement.prototype.close = function () { this.removeAttribute('open'); };
  w.HTMLElement.prototype.scrollIntoView = function () {};
  w.confirm = () => true;
  const requests = [];
  let notebook = { id: 'test-notebook', title: 'Research', description: '', sources: [], messages: [], notes: [], artifacts: [], created: 1, updated: 1 };
  w.fetch = async (url, options) => {
    const payload = options.body ? JSON.parse(options.body) : undefined;
    requests.push({ url, method: options.method, payload, token: options.headers.Authorization });
    let data;
    if (url === '/api/config') data = { model: 'test-model', configured: true, api_key_set: true };
    else if (url === '/api/notebooks') data = [{ ...notebook, source_count: notebook.sources.length }];
    else if (url.endsWith('/sources') && options.method === 'POST') { data = { id: 'source-1', title: payload.title, content: payload.content, kind: payload.kind }; notebook.sources.push(data); }
    else if (url.endsWith('/chat') && options.method === 'POST') {
      data = { id: 'answer-1', role: 'assistant', content: '<img src=x onerror=alert(1)> Answer [1]', evidence: [{ number: 1, source_id: 'source-1', title: 'Source', excerpt: '<script>alert(1)</script> Facts' }] };
      notebook.messages.push({ id: 'q', role: 'user', content: payload.question, evidence: [] }, data);
    } else data = notebook;
    return { ok: true, status: 200, headers: new w.Headers({ 'content-type': 'application/json' }), json: async () => JSON.parse(JSON.stringify(data)) };
  };
  w.sessionStorage.setItem('sourcebook-token', 'test-token-with-enough-characters');
  w.eval(script);
  return { dom, w, requests };
}
test('loads authenticated notebook library and opens workspace', async () => {
  const { dom, w, requests } = boot();
  await tick();
  assert.equal(w.document.querySelectorAll('.notebook-card').length, 1);
  assert.equal(w.document.querySelector('#model-status').textContent, 'test-model · Connected');
  w.document.querySelector('.notebook-card').click(); await tick();
  assert.equal(w.document.querySelector('#workspace').hidden, false);
  assert.equal(w.document.querySelectorAll('.studio-tool').length, 11);
  assert.ok(requests.every(r => r.token === 'Bearer test-token-with-enough-characters'));
  dom.window.close();
});
test('adds pasted source, asks with selection, and safely renders model/citation text', async () => {
  const { dom, w, requests } = boot(); await tick();
  w.document.querySelector('.notebook-card').click(); await tick();
  w.document.querySelector('#add-source').click();
  const form = w.document.querySelector('#modal form');
  form.querySelector('input').value = 'Test source'; form.querySelector('textarea').value = 'Source facts';
  form.dispatchEvent(new w.Event('submit', { cancelable: true })); await tick();
  assert.equal(w.document.querySelectorAll('.source-row').length, 1);
  assert.equal(w.document.querySelector('#selected-count').textContent, '1 source selected');
  w.document.querySelector('#question').value = 'What are the facts?';
  w.document.querySelector('#chat-form').dispatchEvent(new w.Event('submit', { cancelable: true })); await tick();
  assert.equal(w.document.querySelectorAll('.message').length, 2);
  assert.equal(w.document.querySelectorAll('#messages img').length, 0);
  assert.ok(w.document.querySelector('.message.assistant').textContent.includes('<img'));
  const chat = requests.find(r => r.url.endsWith('/chat'));
  assert.deepEqual(chat.payload.source_ids, ['source-1']);
  w.document.querySelector('.citation').click();
  assert.ok(w.document.querySelector('#modal .preview').textContent.includes('<script>'));
  assert.equal(w.document.querySelectorAll('#modal-body script').length, 0);
  dom.window.close();
});
test('disconnect removes access token and visible research data', async () => {
  const { dom, w } = boot(); await tick();
  w.document.querySelector('#settings-button').click(); await tick();
  w.document.querySelector('#modal .secondary').click();
  assert.equal(w.sessionStorage.getItem('sourcebook-token'), null);
  assert.equal(w.document.querySelectorAll('.notebook-card').length, 0);
  assert.equal(w.document.querySelector('#modal-title').textContent, 'Welcome to your workspace');
  dom.window.close();
});
