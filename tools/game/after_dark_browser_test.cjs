/* Real Chromium WebGL2 + CDP multi-touch. No mocked vehicle or renderer. */
const path=require('path'),fs=require('fs');
const root=path.resolve(__dirname,'../..');
const {chromium:playwright}=require(path.join(root,'.cache/browser/node_modules/playwright-core'));
(async()=>{
 const {default:chromium}=await import(path.join(root,'.cache/browser/node_modules/@sparticuz/chromium/build/index.js'));
 const executablePath=await chromium.executablePath();
 const libraries=[path.join(root,'.cache/browser-runtime/usr/lib/x86_64-linux-gnu'),path.join(root,'.cache/software-graphics/runtime/usr/lib/x86_64-linux-gnu'),'/tmp',process.env.LD_LIBRARY_PATH||''].join(':');
 const browser=await playwright.launch({executablePath,env:{...process.env,LD_LIBRARY_PATH:libraries},args:['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist'],headless:true});
 const context=await browser.newContext({viewport:{width:1200,height:630},deviceScaleFactor:1,isMobile:true,hasTouch:true});
 const page=await context.newPage(),cdp=await context.newCDPSession(page);
 const out=path.join(root,'docs/game/after-dark');fs.mkdirSync(out,{recursive:true});
 const errors=[],checks=[];page.on('pageerror',e=>{errors.push(e.message);console.log('ERROR',e.message);});page.on('console',m=>{if(m.type()==='error'){errors.push(m.text());console.log('CONSOLE ERROR',m.text());}});
 const check=(name,value)=>{checks.push({name,passed:!!value});console.log(value?'PASS':'FAIL',name);if(!value)throw Error(name);};
 const state=()=>page.evaluate(()=>window.alpineTelemetry);
 const wait=(fn,arg)=>page.waitForFunction(fn,arg,{timeout:240000});
 const center=async selector=>{const b=await page.locator(selector).boundingBox();if(!b)throw Error('Hidden control: '+selector);return {x:b.x+b.width/2,y:b.y+b.height/2};};
 const tap=async selector=>{const p=await center(selector);await page.touchscreen.tap(p.x,p.y);};
 const point=(id,p)=>({id,...p,radiusX:5,radiusY:5,force:1});
 const touch=(type,points=[])=>cdp.send('Input.dispatchTouchEvent',{type,touchPoints:points});
 async function freeze(){await page.evaluate(()=>{window.savedRAF=window.requestAnimationFrame;window.requestAnimationFrame=()=>0;});await page.waitForTimeout(1000);}
 async function resume(){await page.evaluate(()=>{window.requestAnimationFrame=window.savedRAF;const g=window.alpineGame;g.lastTime=performance.now();requestAnimationFrame(t=>g.frame(t));});}
 async function capture(name){await freeze();const png=await page.evaluate(()=>document.getElementById('canvas').toDataURL('image/png'));fs.writeFileSync(path.join(out,name+'-1080p.png'),Buffer.from(png.split(',')[1],'base64'));const shot=await cdp.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});fs.writeFileSync(path.join(out,name+'-ui.png'),Buffer.from(shot.data,'base64'));await resume();}
 let initial,driving,final,failure;
 try{
  const url=process.env.GAME_URL||'http://127.0.0.1:3001/';
  const response=await page.request.get(url);const raw=await response.text();
  check('Open Graph title/image and Twitter card exist in raw non-JavaScript HTML',raw.includes('property="og:title"')&&raw.includes('property="og:image"')&&raw.includes('summary_large_image'));
  await page.goto(url,{waitUntil:'domcontentloaded'});await wait(()=>window.alpineTelemetry?.reflection_frames>2);
  initial=await state();check('Actual native 1920x1080 render',initial.render_size.join('x')==='1920x1080');
  check('Dynamic 2200kg Roadster chassis and four suspension contacts',initial.car_dynamic&&initial.vehicle_mass_kg===2200&&initial.wheel_contacts===4);
  check('Photographic night sky is default and headlights are enabled',initial.night&&initial.headlights);
  check('Touch controls auto-detected',initial.touch_enabled);
  await capture('launcher');console.log('CAPTURED real launcher / preview source');
  if(process.env.CAPTURE_ONLY==='1')return;
  await tap('[data-command="garage"]');check('Garage opens a real specification panel',await page.locator('#garage-panel').isVisible());await tap('#garage-panel .drawer-close');
  await tap('[data-command="settings"]');check('Controls/settings panel opens',await page.locator('#settings-panel').isVisible());await tap('#settings-panel .drawer-close');
  await page.setViewportSize({width:932,height:430});await tap('#start');await wait(()=>window.alpineTelemetry?.phase==='playing'&&window.alpineTelemetry.in_vehicle);
  check('Launch button starts in the actual Roadster',true);
  const start=(await state()).car_position,j=await center('#joystick'),gas=await center('[data-hold="forward"]');
  await touch('touchStart',[point(1,gas),point(2,j)]);await touch('touchMove',[point(1,gas),point(2,{x:j.x+16,y:j.y})]);
  await wait(p=>Math.hypot(window.alpineTelemetry.car_position.x-p.x,window.alpineTelemetry.car_position.z-p.z)>1.3,start);driving=await state();
  await touch('touchEnd');check('Multi-touch throttle and steering move the dynamic body',driving.car_dynamic&&Math.abs(driving.speed)>1);
  const brake=await center('#jump');await touch('touchStart',[point(3,brake)]);await wait(()=>Math.abs(window.alpineTelemetry.speed)<.15);await touch('touchEnd');check('Physical brakes stop the car',true);
  await tap('#interact');await wait(()=>!window.alpineTelemetry.in_vehicle);check('Safe exit activates the character',true);
  const from=(await state()).player_position,look={x:645,y:200};
  await touch('touchStart',[point(4,j)]);await touch('touchMove',[point(4,{x:j.x,y:j.y-32})]);
  await touch('touchStart',[point(4,{x:j.x,y:j.y-32}),point(5,look)]);await touch('touchMove',[point(4,{x:j.x,y:j.y-32}),point(5,{x:look.x+35,y:look.y})]);
  await wait(p=>Math.hypot(window.alpineTelemetry.player_position.x-p.x,window.alpineTelemetry.player_position.z-p.z)>.5,from);await touch('touchEnd');check('On-foot movement and camera work with two independent fingers',true);
  await touch('touchStart',[point(6,j)]);await touch('touchMove',[point(6,{x:j.x,y:j.y-32})]);await touch('touchCancel');await wait(()=>Math.abs(window.alpineTelemetry.input.y)<.01);check('Touch cancellation releases movement',true);
  await tap('#sky-button');await wait(()=>window.alpineTelemetry.night===false);await tap('#sky-button');await wait(()=>window.alpineTelemetry.night===true);check('Day/night switching changes the live world and returns to night',true);
  await page.keyboard.press('h');await wait(()=>!window.alpineTelemetry.headlights);await page.keyboard.press('h');await wait(()=>window.alpineTelemetry.headlights);check('Headlight toggle operates independently',true);
  await tap('[data-command="pause"]');await wait(()=>window.alpineTelemetry.paused);await tap('#pause .primary');await wait(()=>window.alpineTelemetry.phase==='playing');check('Pause/resume UI preserves gameplay',true);
  await touch('touchStart',[point(7,j)]);await touch('touchMove',[point(7,{x:j.x,y:j.y-30})]);await wait(()=>window.alpineTelemetry.input.y<-.1);
  await page.evaluate(()=>window.dispatchEvent(new Event('blur')));await touch('touchEnd');await wait(()=>window.alpineTelemetry.paused&&Math.abs(window.alpineTelemetry.input.y)<.01);check('Focus loss pauses and clears held input',true);
  await page.setViewportSize({width:430,height:932});check('Portrait retains native canvas resolution',(await state()).render_size.join('x')==='1920x1080');await page.setViewportSize({width:932,height:430});
  await tap('#pause .primary');await tap('[data-command="reset"]');await wait(()=>window.alpineTelemetry.grounded);final=await state();
  check('Live reflection target updated during the expedition',final.reflection_frames>initial.reflection_frames+8);check('No browser runtime errors',errors.length===0);
  await capture('night-gameplay');
 }catch(error){failure=error.message;throw error;}finally{
  fs.writeFileSync(path.join(out,'browser-validation.json'),JSON.stringify({checks,errors,failure,completed:!!final,initial,driving,final,physical_phone_tested:false,target_60fps_verified:false,scope:'Actual Chromium mobile emulation / WebGL2 SwiftShader / dynamic Rapier WASM. Screenshot is real game UI, not generated concept art. CPU software rendering is not a phone or hardware FPS benchmark.'},null,2)+'\n');
  await browser.close();
 }
})().catch(e=>{console.error(e);process.exitCode=1;});
