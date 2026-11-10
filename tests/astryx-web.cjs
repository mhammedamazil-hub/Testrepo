const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {JSDOM}=require('jsdom');
const root=path.join(__dirname,'../web/');
const wait=()=>new Promise(r=>setTimeout(r,40));
function boot(){
 const dom=new JSDOM(fs.readFileSync(root+'index.html','utf8'),{url:'https://sourcebook.test/',runScripts:'outside-only',pretendToBeVisual:true});const w=dom.window;
 w.matchMedia=()=>({matches:false,addEventListener(){},removeEventListener(){},addListener(){},removeListener(){}});
 w.ResizeObserver=class{observe(){}unobserve(){}disconnect(){}};
 w.HTMLDialogElement.prototype.showModal=function(){this.setAttribute('open','');};w.HTMLDialogElement.prototype.close=function(){this.removeAttribute('open');this.dispatchEvent(new w.Event('close'));};
 w.HTMLElement.prototype.scrollIntoView=function(){};w.confirm=()=>true;
 const calls=[];const notebook={id:'one',title:'Research',sources:[],source_count:0,messages:[],notes:[],artifacts:[],created:1,updated:1};
 w.fetch=async(url,options={})=>{const payload=options.body?JSON.parse(options.body):undefined;calls.push({url,method:options.method,payload});let data=url==='/api/config'?{model:'test',configured:true}:url==='/api/notebooks'?[notebook]:url==='/api/ai'?{providers:[],assignments:{},tasks:['default','chat','quiz']}:url==='/api/ai/models'?{models:['real-model']}:url==='/api/ai/test'?{model:'real-model',latency_ms:12}:notebook;return{ok:true,status:200,headers:new w.Headers({'content-type':'application/json'}),json:async()=>data};};
 w.sessionStorage.setItem('sourcebook-token','test-session');
 w.eval(fs.readFileSync(root+'astryx.js','utf8'));w.eval(fs.readFileSync(root+'app.js','utf8'));
 return{dom,w,calls};
}
function button(w,label){return [...w.document.querySelectorAll('button')].find(b=>b.getAttribute('aria-label')===label||b.textContent.trim()===label);}
test('real Astryx components and custom built theme load in the packaged application',async()=>{
 const{dom,w}=boot();await wait();assert.ok(w.SourcebookDesign.version.includes('Astryx'));assert.equal(w.document.documentElement.dataset.astryxTheme,'sourcebook');assert.ok(w.document.querySelectorAll('.astryx-button').length>10);assert.ok(button(w,'New notebook'));assert.ok(w.document.querySelector('.astryx-segmented-control'));dom.window.close();
});
test('Astryx provider form edits and saves credentials to Rust, never browser storage',async()=>{
 const{dom,w,calls}=boot();await wait();w.document.querySelector('#settings-button').click();await wait();button(w,'Add connection').click();await wait();const model=w.document.querySelector('.ax-provider-card input[placeholder="Load models or enter an exact ID"]'),key=w.document.querySelector('.ax-provider-card input[type=password]');assert.ok(model);assert.ok(key);function edit(input,value){Object.getOwnPropertyDescriptor(w.HTMLInputElement.prototype,'value').set.call(input,value);input.dispatchEvent(new w.Event('input',{bubbles:true}));}
 edit(model,'real-model');edit(key,'test-only-secret');await wait();button(w,'Save changes').click();await wait();const save=calls.find(c=>c.url==='/api/ai'&&c.method==='PUT');assert.ok(save,'Astryx form must reach the existing Rust save endpoint');assert.equal(save.payload.providers[0].model,'real-model');assert.equal(save.payload.providers[0].api_key,'test-only-secret');assert.equal(save.payload.assignments.default,save.payload.providers[0].id);assert.ok(!JSON.stringify({...w.localStorage,...w.sessionStorage}).includes('test-only-secret'));dom.window.close();
});
test('Astryx settings close releases provider inputs while keeping the global Theme mounted',async()=>{
 const{dom,w}=boot();await wait();w.document.querySelector('#settings-button').click();await wait();assert.ok(w.document.querySelector('.ax-settings'));w.document.querySelector('#close-modal').click();await wait();assert.equal(w.document.querySelector('.ax-settings'),null);assert.equal(w.document.documentElement.dataset.astryxTheme,'sourcebook');dom.window.close();
});
