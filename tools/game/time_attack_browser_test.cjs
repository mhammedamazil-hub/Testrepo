/* Actual WebGL + real touch + real physics. CPU QA steps simulation separately
 * from expensive render readbacks. It is NOT real-time/phone/FPS evidence. */
const fs=require('fs'),path=require('path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),out=path.join(root,'docs/game/time-attack-v5');
const {chromium:pw}=require(path.join(root,'.cache/browser/node_modules/playwright-core'));
(async()=>{
 const {default:chromium}=await import(path.join(root,'.cache/browser/node_modules/@sparticuz/chromium/build/index.js'));
 const libs=[path.join(root,'.cache/browser-runtime/usr/lib/x86_64-linux-gnu'),path.join(root,'.cache/software-graphics/runtime/usr/lib/x86_64-linux-gnu'),'/tmp'].join(':');
 const browser=await pw.launch({executablePath:await chromium.executablePath(),env:{...process.env,LD_LIBRARY_PATH:libs},args:['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist'],headless:true});
 const context=await browser.newContext({viewport:{width:1200,height:630},hasTouch:true,isMobile:true}),page=await context.newPage(),cdp=await context.newCDPSession(page),errors=[],checks=[];
 page.on('pageerror',e=>{errors.push(e.message);console.log('ERROR',e.message);});page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
 await page.addInitScript(()=>{localStorage.setItem('alpine-graphics','performance');localStorage.setItem('alpine-steering','wheel');window.requestAnimationFrame=()=>0;});
 const check=(name,value)=>{assert.ok(value,name);checks.push({name,passed:true});console.log('PASS',name);};
 const state=()=>page.evaluate(()=>window.alpineTelemetry),wait=(fn,arg)=>page.waitForFunction(fn,arg,{timeout:240000,polling:100});
 const center=async s=>{const b=await page.locator(s).boundingBox();assert.ok(b,'Visible '+s);return {x:b.x+b.width/2,y:b.y+b.height/2};},tap=async s=>{const p=await center(s);await page.touchscreen.tap(p.x,p.y);};
 const touch=(type,points=[])=>cdp.send('Input.dispatchTouchEvent',{type,touchPoints:points.map(p=>({...p,radiusX:4,radiusY:4,force:1}))});
 const startSteps=()=>page.evaluate(()=>{clearInterval(window.qaTimer);window.qaTimer=setInterval(()=>{const g=window.alpineGame;if(g.phase==='playing')g.tick(1/60);g.hud();g.telemetry();},16);});
 const resize=async viewport=>{await page.setViewportSize(viewport);await wait(()=>Math.abs(alpineGame.camera.aspect-innerWidth/innerHeight)<.001);};
 const render=()=>page.evaluate(()=>{const g=window.alpineGame;for(let i=0;i<90;i++)g.updateCamera(1/60);g.world.update(g.camera,1/60);g.world.person.visible=g.phase!=='menu'&&!g.physics.inVehicle;for(const [i,marker] of g.world.markers.entries())marker.visible=g.phase!=='menu'&&!g.physics.flight.active&&i===g.checkpoint;for(const [i,gate] of g.world.flightGates.entries())gate.visible=g.phase==='playing'&&g.physics.flight.active&&i===g.flightChallenge.next;g.renderScene(1/60);g.hud();g.telemetry();});
 async function capture(name){await page.evaluate(()=>clearInterval(window.qaTimer));await render();const shot=await cdp.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});fs.writeFileSync(path.join(out,name+'.png'),Buffer.from(shot.data,'base64'));console.log('CAPTURED',name);await startSteps();}
 let failure,final;
 try{
  await page.goto(process.env.GAME_URL||'http://127.0.0.1:3001/',{waitUntil:'domcontentloaded'});await wait(()=>window.alpineReady);
  await startSteps();await capture('launcher-ui');
  check('Preserve drawing buffer is disabled without a resolution change',!(await state()).preserve_drawing_buffer);
  check('Track kerbs, corner boards, start structure and frozen scenery are present',await page.evaluate(()=>alpineGame.world.trackArt.kerbs===2&&alpineGame.world.trackArt.boards>6&&alpineGame.world.staticNodes>50));
  check('Night shafts pass is fully bypassed',(await state()).night_pass_bypassed);
  check('Added instanced grass is present',(await state()).meadow_instances>10000);
  check('Unchanged HUD refreshes retain existing text and gear DOM nodes',await page.evaluate(()=>{const g=alpineGame;g.hud();const a=document.getElementById('gear').firstChild,b=document.getElementById('reverse-gear').firstChild;for(let i=0;i<30;i++)g.hud();return a===document.getElementById('gear').firstChild&&b===document.getElementById('reverse-gear').firstChild;}));
  await tap('#lobby-garage');check('Lobby garage is functional',await page.locator('#garage-panel').isVisible());await tap('#garage-panel .drawer-close');
  await tap('#lobby-settings');check('Lobby settings are functional',await page.locator('#settings-panel').isVisible());await tap('#settings-panel .drawer-close');
  check('Game initializes with actual graded terrain, four contacts and dynamic car',(await state()).wheel_contacts===4&&(await state()).car_dynamic);
  await page.evaluate(()=>clearInterval(window.qaTimer));
  const comparison=await page.evaluate(()=>{
   const g=alpineGame,gl=g.renderer.getContext(),width=gl.drawingBufferWidth,height=gl.drawingBufferHeight,baseline=new Uint8Array(width*height*4),optimized=new Uint8Array(baseline.length),update=g.rays.update;let updates=0;g.rays.update=function(...args){updates++;return update.apply(this,args);};
   g.effects.enabled=true;g.effects.renderToScreen=true;g.clearEffects.enabled=false;g.clearEffects.renderToScreen=false;g.rays.blendMode.opacity.value=0;g.world.frame++;g.renderScene(0);gl.readPixels(0,0,width,height,gl.RGBA,gl.UNSIGNED_BYTE,baseline);const before={...g.gpuStats,shaft_updates:updates};
   g.syncEffects();updates=0;g.world.frame++;g.renderScene(0);gl.readPixels(0,0,width,height,gl.RGBA,gl.UNSIGNED_BYTE,optimized);const after={...g.gpuStats,shaft_updates:updates};g.rays.update=update;let sum=0,max=0,nonblack=0;for(let i=0;i<baseline.length;i+=4){if(baseline[i]+baseline[i+1]+baseline[i+2]>6)nonblack++;for(let c=0;c<3;c++){const d=Math.abs(baseline[i+c]-optimized[i+c]);sum+=d;max=Math.max(max,d);}}
   return {scope:'Same actual night scene, grass, camera, render dimensions, shadows, texture and reflection sizes. Historical zero-opacity shafts pipeline vs disabled shafts/ACES-only pipeline. Synchronous same-render readback with preserveDrawingBuffer false. Not device FPS or a whole-version GPU benchmark.',width,height,before,after,mean_absolute_channel_error:sum/(width*height*3),maximum_channel_error:max,nonblack_pixels:nonblack,quality:g.quality};
  });
  fs.writeFileSync(path.join(out,'night-pass-comparison.json'),JSON.stringify(comparison,null,2)+'\n');check('Night optimization removes real rendering work',comparison.after.calls<comparison.before.calls&&comparison.before.shaft_updates===1&&comparison.after.shaft_updates===0);check('Identical-quality night image is preserved in A/B readback',comparison.maximum_channel_error<=2&&comparison.mean_absolute_channel_error<.1&&comparison.nonblack_pixels>10000);await startSteps();
  await page.evaluate(()=>clearInterval(window.qaTimer));
  const batching=await page.evaluate(()=>{
   const g=alpineGame,batch=g.world.vehicleBatch,gl=g.renderer.getContext(),width=gl.drawingBufferWidth,height=gl.drawingBufferHeight,a=new Uint8Array(width*height*4),b=new Uint8Array(a.length);
   batch.setEnabled(false);g.world.frame++;g.renderScene(0);gl.readPixels(0,0,width,height,gl.RGBA,gl.UNSIGNED_BYTE,a);const before={...g.gpuStats};
   batch.setEnabled(true);batch.update();g.world.frame++;g.renderScene(0);gl.readPixels(0,0,width,height,gl.RGBA,gl.UNSIGNED_BYTE,b);const after={...g.gpuStats};let sum=0,max=0,changed=0;for(let i=0;i<a.length;i+=4){let large=false;for(let c=0;c<3;c++){const d=Math.abs(a[i+c]-b[i+c]);sum+=d;max=Math.max(max,d);if(d>4)large=true;}if(large)changed++;}
   return {scope:'Same actual night scene, grass, camera, resolution, textures, original vehicle geometry and materials, shadows and reflections. Original opaque nodes versus exact same-material native multi-draw batches. Transparent glass unchanged. Edge rasterization differences are measured, not hidden. Not FPS.',available:batch.enabled,batches:batch.batch_count,batched_source_meshes:batch.source_meshes,before,after,mean_absolute_channel_error:sum/(width*height*3),maximum_channel_error:max,changed_pixel_fraction:changed/(width*height),width,height};
  });fs.writeFileSync(path.join(out,'vehicle-batch-comparison.json'),JSON.stringify(batching,null,2)+'\n');check('Opaque batching preserves the visible image',batching.mean_absolute_channel_error<.15&&batching.changed_pixel_fraction<.001);check('Native batching reduces recorded draw submissions when available',!batching.available||batching.after.calls<batching.before.calls);await page.evaluate(()=>clearInterval(window.qaTimer));
  const staticComparison=await page.evaluate(()=>{
   const g=alpineGame,gl=g.renderer.getContext(),width=gl.drawingBufferWidth,height=gl.drawingBufferHeight,a=new Uint8Array(width*height*4),b=new Uint8Array(a.length),roots=g.world.staticRoots;
   const set=enabled=>roots.forEach(r=>r.traverse(n=>{n.matrixAutoUpdate=!enabled;n.matrixWorldAutoUpdate=!enabled;}));
   const measure=()=>{const times=[];for(let run=0;run<5;run++){const t=performance.now();for(let i=0;i<200;i++)g.scene.updateMatrixWorld();times.push(performance.now()-t);}return times.sort((a,b)=>a-b)[2];};
   set(false);const beforeCPU=measure();g.world.frame++;g.renderScene(0);gl.readPixels(0,0,width,height,gl.RGBA,gl.UNSIGNED_BYTE,a);const before={...g.gpuStats};
   set(true);const afterCPU=measure();g.world.frame++;g.renderScene(0);gl.readPixels(0,0,width,height,gl.RGBA,gl.UNSIGNED_BYTE,b);const after={...g.gpuStats};let sum=0,max=0;for(let i=0;i<a.length;i++){const d=Math.abs(a[i]-b[i]);sum+=d;max=Math.max(max,d);}
   return {scope:'Same scene/camera/quality and all content retained. A/B of static matrix updates. Forest remains one instanced mesh (the exploratory cell split was rejected for extra draw overhead). 200 scene.updateMatrixWorld calls, median five runs; not game FPS or device GPU timing.',static_nodes:g.world.staticNodes,before,after,before_matrix_ms:beforeCPU,after_matrix_ms:afterCPU,mean_channel_error:sum/a.length,max_channel_error:max,width,height};
  });fs.writeFileSync(path.join(out,'static-forest-comparison.json'),JSON.stringify(staticComparison,null,2)+'\n');check('Frozen static transforms preserve exact pixels',staticComparison.max_channel_error===0);check('Static optimization retains every draw and triangle',staticComparison.after.triangles===staticComparison.before.triangles&&staticComparison.after.calls===staticComparison.before.calls);await startSteps();
  await tap('#start');await wait(()=>window.alpineTelemetry.in_vehicle);check('Time trial starts with a three-second stationary countdown',await page.evaluate(()=>alpineGame.trial.countdown>0&&Math.abs(alpineGame.physics.speed)<.15));await wait(()=>alpineTelemetry.race_countdown===0);await resize({width:932,height:430});
  check('Full-bleed landscape aspect matches visible viewport',await page.evaluate(()=>Math.abs(alpineGame.camera.aspect-innerWidth/innerHeight)<.001));
  const gas=await center('#gas-pedal'),wheel=await page.locator('#steering-wheel').boundingBox(),from=(await state()).car_position;
  await touch('touchStart',[{id:1,x:wheel.x+wheel.width/2,y:wheel.y+10},{id:2,...gas}]);await touch('touchMove',[{id:1,x:wheel.x+wheel.width-10,y:wheel.y+wheel.height/2},{id:2,...gas}]);
  await wait(p=>Math.hypot(alpineTelemetry.car_position.x-p.x,alpineTelemetry.car_position.z-p.z)>.7,from);
  check('Wheel and pedal touch drive the actual dynamic car',(await state()).input.x>.5);await touch('touchEnd');
  const brake=await center('#brake-pedal');await touch('touchStart',[{id:3,...brake}]);await wait(()=>Math.abs(alpineTelemetry.speed)<.15);await touch('touchEnd');check('Dedicated brake pedal stops the car',true);
  await tap('#reverse-gear');check('Explicit D/R selector selects reverse',await page.evaluate(()=>alpineGame.input.gear===-1));await touch('touchStart',[{id:4,...gas}]);await wait(()=>alpineTelemetry.speed<-.5);await touch('touchEnd');check('Gas pedal drives in selected reverse gear',true);
  const elapsed=(await state()).elapsed;await tap('[data-command="reset"]');await wait(()=>alpineTelemetry.wheel_contacts===4&&Math.abs(alpineTelemetry.speed)<.2);check('Nearest recovery preserves lap time and clears motion',(await state()).elapsed>=elapsed&&Math.abs((await state()).speed)<.2);check('Recovery returns to road with four contacts',(await state()).wheel_contacts===4);
  await capture('landscape-wheel');await tap('#steering-switch');await wait(()=>alpineTelemetry.steering_mode==='arrows');check('Both steering modes switch in live gameplay',(await state()).steering_mode==='arrows');
  const left=await center('[data-hold="left"]');await touch('touchStart',[{id:5,...left},{id:6,...gas}]);await wait(()=>alpineTelemetry.input.x===-1&&alpineTelemetry.speed>.3);check('Polygon button and gas preserve full independent steering',true);await touch('touchCancel');await wait(()=>alpineTelemetry.input.x===0&&alpineTelemetry.input.throttle===0);check('Touch cancellation releases steering and pedal',true);
  await tap('[data-command="reset"]');await capture('landscape-arrows');
  await resize({width:430,height:932});await tap('#steering-switch');await capture('portrait-wheel');
  check('Portrait camera and render have correct aspect without black bands',await page.evaluate(()=>Math.abs(alpineGame.camera.aspect-innerWidth/innerHeight)<.001&&Math.abs(alpineGame.renderer.domElement.width/alpineGame.renderer.domElement.height-innerWidth/innerHeight)<.01));
  await page.evaluate(()=>{clearInterval(window.qaTimer);const g=alpineGame;g.command('flight');for(let i=0;i<70;i++)g.tick(1/60);g.hud();g.telemetry();});
  check('Ground-only finite thruster hop lifts the actual car',(await state()).flight_active&&await page.evaluate(()=>alpineGame.physics.car.translation().y>alpineGame.nearest.y+1));
  await tap('#interact');check('Airborne exit is safely blocked',(await state()).in_vehicle);
  const lift=await center('[data-hold="lift"]'),boost=await center('#boost-control'),flightGas=await center('#gas-pedal');
  await touch('touchStart',[{id:10,...lift},{id:11,...boost},{id:12,...flightGas}]);
  const thrust=await page.evaluate(()=>{const g=alpineGame,before=g.physics.flight.energy;for(let i=0;i<20;i++)g.tick(1/60);g.hud();g.telemetry();return g.input.sample(true,false).lift===1&&g.input.sample(true,false).boost&&g.physics.flight.energy<before;});
  await touch('touchEnd');check('Lift and boost consume shared finite gas with independent touch sources',thrust);
  // Stop the test timer again after each capture; finite flight is intentionally
  // not extended to accommodate slow software screenshots.
  await resize({width:932,height:430});await capture('hop-landscape');await page.evaluate(()=>clearInterval(window.qaTimer));
  await resize({width:430,height:932});await capture('hop-portrait');await page.evaluate(()=>clearInterval(window.qaTimer));
  await tap('#land-control');
  const landing=await page.evaluate(()=>{const g=alpineGame;for(let i=0;i<600;i++)g.tick(1/60);g.hud();g.telemetry();return {active:g.physics.flight.active,grounded:g.physics.carGrounded,gas:g.physics.flight.energy};});
  check('Limited hop automatically returns to ground driving without instant refill',!landing.active&&landing.grounded&&landing.gas<100);
  const finite=await page.evaluate(()=>{const g=alpineGame;g.recover();g.trial.countdown=0;g.command('flight');g.input.press('qa','lift');let maxTime=0,airRefill=false,last=100;for(let i=0;i<600;i++){g.tick(1/60);const f=g.physics.flight;if(f.active){maxTime=Math.max(maxTime,f.elapsed);if(!g.physics.carGrounded&&f.energy>last+.001)airRefill=true;last=f.energy;}}g.input.clear();g.hud();g.telemetry();return {active:g.physics.flight.active,grounded:g.physics.carGrounded,maxTime,airRefill,valid:g.trial.valid};});
  check('Holding lift cannot sustain flight, refill aloft or count as a clean race lap',!finite.active&&finite.grounded&&!finite.airRefill&&!finite.valid);
  await startSteps();
  await tap('#interact');await wait(()=>!alpineTelemetry.in_vehicle);check('Walking retains its own joystick and hides driving pedals',await page.locator('#joystick').isVisible()&&!await page.locator('#gas-pedal').isVisible());
  const joy=await center('#joystick'),walkStart=(await state()).player_position;await touch('touchStart',[{id:7,...joy}]);await touch('touchMove',[{id:7,x:joy.x,y:joy.y-30}]);await wait(p=>Math.hypot(alpineTelemetry.player_position.x-p.x,alpineTelemetry.player_position.z-p.z)>.3,walkStart);await touch('touchCancel');check('On-foot joystick still moves the real character',true);
  await tap('[data-command="pause"]');await wait(()=>alpineTelemetry.paused);await tap('#pause .primary');await wait(()=>alpineTelemetry.phase==='playing');check('Pause/resume preserves gameplay',true);
  await page.evaluate(()=>window.dispatchEvent(new Event('blur')));await wait(()=>alpineTelemetry.paused&&alpineTelemetry.input.throttle===0);check('Focus loss pauses and clears held controls',true);
  await page.evaluate(()=>alpineGame.command('menu'));await wait(()=>alpineTelemetry.phase==='menu');await tap('#launch-flight');await tap('#start');await wait(()=>alpineTelemetry.flight_active&&alpineTelemetry.in_vehicle);check('Lobby flight selection launches the playable training mode',true);await page.evaluate(()=>alpineGame.command('reset'));
  await page.evaluate(()=>clearInterval(window.qaTimer));
  const raceRun=await page.evaluate(async()=>{
   const {nearestRoute}=await import('/src/track.js'),g=alpineGame;g.launchMode='drive';g.command('menu');g.command('start');const sample=g.input.sample.bind(g.input);let ticks=0,maxDistance=0;
   g.input.sample=()=>{const p=g.physics.car.translation(),near=nearestRoute(g.world.data.route,p),target=g.world.data.route[(near.index+5)%640],desired=Math.atan2(-(target[0]-p.x),-(target[2]-p.z)),error=Math.atan2(Math.sin(desired-g.physics.yaw),Math.cos(desired-g.physics.yaw));maxDistance=Math.max(maxDistance,near.distance);return {x:Math.max(-1,Math.min(1,-error*2.8)),y:0,throttle:g.physics.speed<8?.3:0,brake:g.physics.speed>9,jump:false,run:false,lift:0,boost:false,flightBrake:false};};
   try{for(;ticks<18000&&g.laps<1;ticks++)g.tick(1/60);}finally{g.input.sample=sample;g.input.clear();}
   g.hud();g.telemetry();return {scope:'Actual runtime tick, terrain, contacts, checkpoint ordering, countdown and TimeTrial persistence, driven only by a test-input pursuit driver. No car transform/velocity assignment after reset. Not a human/tablet FPS test.',ticks,laps:g.laps,max_distance:maxDistance,result:g.trial.result,best:g.trial.best,saved:JSON.parse(localStorage.getItem('alpine-time-trial-v5')||'null')};
  });fs.writeFileSync(path.join(out,'runtime-time-trial.json'),JSON.stringify(raceRun,null,2)+'\n');check('Real full runtime lap awards a clean medal and persists a personal best',raceRun.laps===1&&raceRun.result.valid&&raceRun.best.time===raceRun.saved.time);
  check('Personal-best HUD is visible and readable in gameplay',await page.locator('#trial-best').isVisible()&&(await page.locator('#trial-best').textContent()).includes('s'));
  await resize({width:1200,height:630});await page.evaluate(()=>alpineGame.command('night'));await capture('circuit-day');await page.evaluate(()=>clearInterval(window.qaTimer));
  final=await state();check('No browser runtime errors',errors.length===0);
 }catch(e){failure=e.message;throw e;}finally{
  fs.writeFileSync(path.join(out,'browser-validation.json'),JSON.stringify({scope:'Real Chromium mobile emulation, actual WebGL2 software rendering and actual touch input/Rapier. Simulation stepped by test timer independently of expensive render readbacks. Performance graphics preset (about 0.52MP) explicitly selected. Not real-time/FPS/physical-phone evidence.',checks,errors,failure,completed:!!final,final},null,2)+'\n');await browser.close();
 }
})().catch(e=>{console.error(e);process.exitCode=1;});
