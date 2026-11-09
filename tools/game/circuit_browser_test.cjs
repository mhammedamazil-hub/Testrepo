/* Actual WebGL + real touch + real physics. CPU QA steps simulation separately
 * from expensive render readbacks. It is NOT real-time/phone/FPS evidence. */
const fs=require('fs'),path=require('path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),out=path.join(root,'docs/game/circuit-v3');
const {chromium:pw}=require(path.join(root,'.cache/browser/node_modules/playwright-core'));
(async()=>{
 const {default:chromium}=await import(path.join(root,'.cache/browser/node_modules/@sparticuz/chromium/build/index.js'));
 const libs=[path.join(root,'.cache/browser-runtime/usr/lib/x86_64-linux-gnu'),path.join(root,'.cache/software-graphics/runtime/usr/lib/x86_64-linux-gnu'),'/tmp'].join(':');
 const browser=await pw.launch({executablePath:await chromium.executablePath(),env:{...process.env,LD_LIBRARY_PATH:libs},args:['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist'],headless:true});
 const context=await browser.newContext({viewport:{width:1200,height:630},hasTouch:true,isMobile:true}),page=await context.newPage(),cdp=await context.newCDPSession(page),errors=[],checks=[];
 page.on('pageerror',e=>{errors.push(e.message);console.log('ERROR',e.message);});page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
 await page.addInitScript(()=>{localStorage.setItem('alpine-graphics','performance');localStorage.setItem('alpine-steering','wheel');window.requestAnimationFrame=()=>0;});
 const check=(name,value)=>{assert.ok(value,name);checks.push({name,passed:true});console.log('PASS',name);};
 const state=()=>page.evaluate(()=>window.alpineTelemetry),wait=(fn,arg)=>page.waitForFunction(fn,arg,{timeout:60000,polling:100});
 const center=async s=>{const b=await page.locator(s).boundingBox();assert.ok(b,'Visible '+s);return {x:b.x+b.width/2,y:b.y+b.height/2};},tap=async s=>{const p=await center(s);await page.touchscreen.tap(p.x,p.y);};
 const touch=(type,points=[])=>cdp.send('Input.dispatchTouchEvent',{type,touchPoints:points.map(p=>({...p,radiusX:4,radiusY:4,force:1}))});
 const startSteps=()=>page.evaluate(()=>{clearInterval(window.qaTimer);window.qaTimer=setInterval(()=>{const g=window.alpineGame;if(g.phase==='playing')g.tick(1/60);g.hud();g.telemetry();},16);});
 const resize=async viewport=>{await page.setViewportSize(viewport);await wait(()=>Math.abs(alpineGame.camera.aspect-innerWidth/innerHeight)<.001);};
 const render=()=>page.evaluate(()=>{const g=window.alpineGame;g.updateCamera(1/60);g.world.update(g.camera,1/60);g.world.person.visible=g.phase!=='menu'&&!g.physics.inVehicle;for(const [i,marker] of g.world.markers.entries())marker.visible=g.phase!=='menu'&&i===g.checkpoint;g.composer.render(1/60);g.hud();g.telemetry();});
 async function capture(name){await page.evaluate(()=>clearInterval(window.qaTimer));await render();const shot=await cdp.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});fs.writeFileSync(path.join(out,name+'.png'),Buffer.from(shot.data,'base64'));console.log('CAPTURED',name);await startSteps();}
 let failure,final;
 try{
  await page.goto(process.env.GAME_URL||'http://127.0.0.1:3001/',{waitUntil:'domcontentloaded'});await wait(()=>window.alpineReady);
  await startSteps();await capture('launcher-ui');
  check('Game initializes with actual graded terrain, four contacts and dynamic car',(await state()).wheel_contacts===4&&(await state()).car_dynamic);
  await tap('#start');await wait(()=>window.alpineTelemetry.in_vehicle);await resize({width:932,height:430});
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
  await tap('#interact');await wait(()=>!alpineTelemetry.in_vehicle);check('Walking retains its own joystick and hides driving pedals',await page.locator('#joystick').isVisible()&&!await page.locator('#gas-pedal').isVisible());
  const joy=await center('#joystick'),walkStart=(await state()).player_position;await touch('touchStart',[{id:7,...joy}]);await touch('touchMove',[{id:7,x:joy.x,y:joy.y-30}]);await wait(p=>Math.hypot(alpineTelemetry.player_position.x-p.x,alpineTelemetry.player_position.z-p.z)>.3,walkStart);await touch('touchCancel');check('On-foot joystick still moves the real character',true);
  await tap('[data-command="pause"]');await wait(()=>alpineTelemetry.paused);await tap('#pause .primary');await wait(()=>alpineTelemetry.phase==='playing');check('Pause/resume preserves gameplay',true);
  await page.evaluate(()=>window.dispatchEvent(new Event('blur')));await wait(()=>alpineTelemetry.paused&&alpineTelemetry.input.throttle===0);check('Focus loss pauses and clears held controls',true);
  final=await state();check('No browser runtime errors',errors.length===0);
 }catch(e){failure=e.message;throw e;}finally{
  fs.writeFileSync(path.join(out,'browser-validation.json'),JSON.stringify({scope:'Real Chromium mobile emulation, actual WebGL2 software rendering and actual touch input/Rapier. Simulation stepped by test timer independently of expensive render readbacks. Performance graphics preset (about 0.52MP) explicitly selected. Not real-time/FPS/physical-phone evidence.',checks,errors,failure,completed:!!final,final},null,2)+'\n');await browser.close();
 }
})().catch(e=>{console.error(e);process.exitCode=1;});
