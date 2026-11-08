/* Installed before app.js. Native IPC only: no fetch to localhost, no bound port. */
'use strict';
if (window.SourcebookAndroid?.request && window.SourcebookAndroid?.isOffline()) {
    const pending = new Map(); let serial=0;
    const chunks=new Map();
    window.__sourcebookNativeChunk=(id,offset,total,chunk)=>{let state=chunks.get(id);if(offset===0){state={text:'',total};chunks.set(id,state);}if(!state||state.text.length!==offset||total>40*1024*1024){chunks.delete(id);const p=pending.get(String(id));pending.delete(String(id));p?.reject(new Error('Invalid native response chunks'));return;}state.text+=chunk;if(state.text.length===total){chunks.delete(id);try{window.__sourcebookNativeReply(id,JSON.parse(state.text));}catch(e){const p=pending.get(String(id));pending.delete(String(id));p?.reject(e);}}};
    window.__sourcebookNativeReply=(id,reply)=>{
        const request=pending.get(String(id));if(!request)return;pending.delete(String(id));
        try{const raw=atob(reply.body);const bytes=Uint8Array.from(raw,c=>c.charCodeAt(0));request.resolve(new Response(bytes,{status:reply.status,headers:{'content-type':reply.type}}));}catch(e){request.reject(e);}
    };
    window.fetch=(input,options={})=>{
        const url=new URL(typeof input==='string'?input:input.url,location.href);
        if(url.origin!==location.origin||!url.pathname.startsWith('/api/'))return Promise.reject(new Error('Network access is disabled in this offline APK'));
        return new Promise((resolve,reject)=>{const id=String(++serial);pending.set(id,{resolve,reject});try{window.SourcebookAndroid.request(id,options.method||'GET',url.pathname+url.search,options.body||'');}catch(e){pending.delete(id);reject(e);}});
    };
    sessionStorage.setItem('sourcebook-token','local-android-session-no-network');
    document.documentElement.classList.add('offline-app');
}
