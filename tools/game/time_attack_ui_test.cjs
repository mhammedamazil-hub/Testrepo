// Real DOM/CSS + actual AlpineInput, without loading WebGL. Not renderer evidence.
const fs=require('fs'),path=require('path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),{chromium:pw}=require(path.join(root,'.cache/browser/node_modules/playwright-core'));
(async()=>{
 const {default:chromium}=await import(path.join(root,'.cache/browser/node_modules/@sparticuz/chromium/build/index.js'));
 const libs=[path.join(root,'.cache/browser-runtime/usr/lib/x86_64-linux-gnu'),path.join(root,'.cache/software-graphics/runtime/usr/lib/x86_64-linux-gnu'),'/tmp'].join(':');
 const browser=await pw.launch({executablePath:await chromium.executablePath(),env:{...process.env,LD_LIBRARY_PATH:libs},args:['--no-sandbox','--disable-dev-shm-usage'],headless:true});const checks=[];
 try{
  for(const viewport of [{width:360,height:800},{width:724,height:1280},{width:932,height:430}]){
   const context=await browser.newContext({viewport,isMobile:true,hasTouch:true}),page=await context.newPage(),cdp=await context.newCDPSession(page);
   await page.setContent(fs.readFileSync(path.join(root,'engine/index.html'),'utf8').replace(/<script[^>]*>[\s\S]*?<\/script>/g,''));await page.addStyleTag({content:fs.readFileSync(path.join(root,'engine/src/style.css'),'utf8')});
   await page.addScriptTag({content:fs.readFileSync(path.join(root,'engine/src/input.js'),'utf8').replace('export class AlpineInput','window.AlpineInput=class AlpineInput')});
   await page.evaluate(()=>{document.body.dataset.phase='playing';document.body.classList.add('driving');document.getElementById('loading').hidden=true;window.input=new AlpineInput(document.getElementById('canvas'),action=>{if(action==='steering')input.setSteeringMode(input.steeringMode==='wheel'?'arrows':'wheel');},()=>{});});
   const box=s=>page.locator(s).boundingBox(),center=async s=>{const b=await box(s);return {x:b.x+b.width/2,y:b.y+b.height/2};};
   const touch=(type,points=[])=>cdp.send('Input.dispatchTouchEvent',{type,touchPoints:points.map((p,i)=>({id:p.id||i+1,x:p.x,y:p.y,radiusX:4,radiusY:4,force:1}))});
   for(const flying of [false,true])for(const mode of ['wheel','arrows']){
    await page.evaluate(f=>document.body.classList.toggle('flight',f),flying);
    await page.evaluate(mode=>input.setSteeringMode(mode),mode);
    const ids=['.race-top','.route-instruction',...(!flying?['#trial-readout']:[]),'#gas-pedal','#brake-pedal','#drive-utilities',mode==='wheel'?'#steering-wheel':'#steering-arrows','#telemetry',...(flying?['#boost-control','.lift-rocker','#land-control','#flight-readout','.minimap']:[])];const boxes=[];
    for(const id of ids){const b=await box(id);assert.ok(b&&b.x>=0&&b.y>=0&&b.x+b.width<=viewport.width+1&&b.y+b.height<=viewport.height+1,`${id} outside ${JSON.stringify(viewport)}`);boxes.push({id,...b});}
    for(let i=0;i<boxes.length;i++)for(let j=i+1;j<boxes.length;j++){const a=boxes[i],b=boxes[j];assert.ok(!(a.x<b.x+b.width&&a.x+a.width>b.x&&a.y<b.y+b.height&&a.y+a.height>b.y),`${a.id} overlaps ${b.id}`);}
    const gas=await center('#gas-pedal');
    if(mode==='wheel'){
     const w=await box('#steering-wheel'),start={x:w.x+w.width/2,y:w.y+10},end={x:w.x+w.width-10,y:w.y+w.height/2};
     await touch('touchStart',[{id:1,...start},{id:2,...gas}]);await touch('touchMove',[{id:1,...end},{id:2,...gas}]);
     const value=await page.evaluate(()=>input.sample(true,false));assert.ok(value.x>.5&&value.throttle===1,'Wheel and gas must work together');
    }else{
     const left=await center('[data-hold="left"]');await touch('touchStart',[{id:1,...left},{id:2,...gas}]);const v=await page.evaluate(()=>input.sample(true,false));assert.equal(v.x,-1);assert.equal(v.throttle,1);
    }
    await touch('touchCancel');await page.waitForFunction(()=>input.sample(true,false).x===0&&input.sample(true,false).throttle===0);const clear=await page.evaluate(()=>input.sample(true,false));assert.equal(clear.x,0);assert.equal(clear.throttle,0);
    const brake=await center('#brake-pedal');await touch('touchStart',[{id:3,...brake}]);assert.equal((await page.evaluate(()=>input.sample(true,false))).brake,true);await page.evaluate(()=>window.dispatchEvent(new Event('blur')));await touch('touchEnd');assert.equal((await page.evaluate(()=>input.sample(true,false))).brake,false);
    checks.push({viewport,mode,flying,layout_and_multitouch:true,cancel_and_blur:true});
   }
   await page.evaluate(()=>{document.body.classList.remove('driving','flight');input.clear();});assert.ok(await page.locator('#joystick').isVisible());assert.equal(await page.locator('#gas-pedal').isVisible(),false);
   await page.evaluate(()=>{document.body.dataset.phase='menu';document.getElementById('menu').hidden=false;});
   const lobby=await box('.lobby-sidebar'),vehicle=await box('.lobby-vehicle');assert.ok(lobby.y+lobby.height<=viewport.height&&vehicle.x+vehicle.width<=viewport.width);assert.ok(!(lobby.x<vehicle.x+vehicle.width&&lobby.x+lobby.width>vehicle.x&&lobby.y<vehicle.y+vehicle.height&&lobby.y+lobby.height>vehicle.y),'Lobby panels overlap');
   await context.close();
  }
  fs.writeFileSync(path.join(root,'docs/game/time-attack-v5/ui-input-validation.json'),JSON.stringify({scope:'Real Chromium DOM/CSS and actual AlpineInput event handlers. No WebGL or hardware performance claim.',checks,passed:true},null,2)+'\n');console.log('BEYOND_ROAD_UI_LAYOUT_AND_MULTITOUCH_PASS',checks.length);
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
