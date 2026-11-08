/* Actual Chromium touch events, mobile viewport, real Godot Web runtime.
   Emulation is NOT a physical-phone or 60 FPS certification. */
const path=require('path'),fs=require('fs');
const root=path.resolve(__dirname,'../..');
const {chromium:playwright}=require(path.join(root,'.cache/browser/node_modules/playwright-core'));
(async()=>{
 const {default:chromium}=await import(path.join(root,'.cache/browser/node_modules/@sparticuz/chromium/build/index.js'));
 const executablePath=await chromium.executablePath();
 const libraries=[path.join(root,'.cache/browser-runtime/usr/lib/x86_64-linux-gnu'),path.join(root,'.cache/software-graphics/runtime/usr/lib/x86_64-linux-gnu'),'/tmp',process.env.LD_LIBRARY_PATH||''].join(':');
 const browser=await playwright.launch({executablePath,env:{...process.env,LD_LIBRARY_PATH:libraries},args:['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist'],headless:true});
 const context=await browser.newContext({viewport:{width:932,height:430},deviceScaleFactor:1,isMobile:true,hasTouch:true,userAgent:'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Mobile Safari/537.36'});
 const page=await context.newPage(),cdp=await context.newCDPSession(page);

 const out=path.join(root,'docs/game'),errors=[],checks=[];fs.mkdirSync(out,{recursive:true});
 page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
 const check=(name,value)=>{checks.push({name,passed:!!value});console.log(value?'PASS':'FAIL',name);if(!value)throw Error(name);};
 const state=()=>page.evaluate(()=>window.alpineTelemetry);
 const wait=(fn,arg)=>page.waitForFunction(fn,arg,{timeout:180000});
 const center=async selector=>{const b=await page.locator(selector).boundingBox();return {x:b.x+b.width/2,y:b.y+b.height/2};};
 const tap=async selector=>{const p=await center(selector);await page.touchscreen.tap(p.x,p.y);};
 const point=(id,p)=>({id,...p,radiusX:5,radiusY:5,force:1});
 const touch=(type,points=[])=>cdp.send('Input.dispatchTouchEvent',{type,touchPoints:points});
 try{
 await page.goto(process.env.GAME_URL||'http://127.0.0.1:3001',{waitUntil:'domcontentloaded'});
 await wait(()=>window.alpineTelemetry?.reflection_frames>1);
 check('Actual native 1920x1080 WebGL2 renderer',(await state()).render_size.join('x')==='1920x1080');
 check('Mobile controls auto-detected',(await state()).touch_enabled);
 check('Live mirrored-camera water and occluded shafts enabled',(await state()).rays_enabled&&(await state()).reflection_frames>1);
 await tap('#start');await wait(()=>window.alpineTelemetry?.phase==='playing');
 await wait(()=>window.alpineTelemetry?.grounded);check('Actual scene terrain supports Rapier character',true);
 let start=(await state()).player_position;
 const j=await center('#joystick'),look={x:650,y:200};
 await touch('touchStart',[point(1,j)]);await touch('touchMove',[point(1,{x:j.x,y:j.y-35})]);
 await touch('touchStart',[point(1,{x:j.x,y:j.y-35}),point(2,look)]);
 await touch('touchMove',[point(1,{x:j.x,y:j.y-35}),point(2,{x:look.x+45,y:look.y})]);
 await wait(p=>Math.hypot(window.alpineTelemetry.player_position.x-p.x,window.alpineTelemetry.player_position.z-p.z)>.7,start);
 await touch('touchEnd');check('Two real touch fingers walk and orbit',true);
 await wait(()=>Math.abs(window.alpineTelemetry.input.x)<.01&&Math.abs(window.alpineTelemetry.input.y)<.01);
 await tap('[data-command="reset"]');await tap('#interact');await wait(()=>window.alpineTelemetry?.in_vehicle);check('Touch ENTER activates real vehicle',true);
 start=(await state()).car_position;const gas=await center('[data-hold="forward"]');
 await touch('touchStart',[point(3,gas),point(4,j)]);await touch('touchMove',[point(3,gas),point(4,{x:j.x+20,y:j.y})]);
 await wait(p=>Math.hypot(window.alpineTelemetry.car_position.x-p.x,window.alpineTelemetry.car_position.z-p.z)>1.5,start);
 const driven=await state();await touch('touchEnd');check('Multi-touch pedals and steering move collision vehicle',true);
 const brake=await center('#jump');await touch('touchStart',[point(5,brake)]);await wait(()=>Math.abs(window.alpineTelemetry.speed)<.1);await touch('touchEnd');check('Touch BRAKE stops vehicle',true);
 await tap('#interact');await wait(()=>!window.alpineTelemetry.in_vehicle);check('Safe touch EXIT restores character',true);
 await touch('touchStart',[point(6,j)]);await touch('touchMove',[point(6,{x:j.x,y:j.y-35})]);await touch('touchCancel');
 await wait(()=>Math.abs(window.alpineTelemetry.input.y)<.01);check('Touch cancellation releases joystick',true);
 await tap('[data-command="pause"]');await wait(()=>window.alpineTelemetry.paused);await tap('#pause .primary');await wait(()=>window.alpineTelemetry.phase==='playing');check('Pause and resume via touch',true);
 await touch('touchStart',[point(7,gas)]);await page.evaluate(()=>window.dispatchEvent(new Event('blur')));await touch('touchEnd');
 await wait(()=>window.alpineTelemetry.paused&&window.alpineTelemetry.input.throttle===0);check('Focus loss pauses and releases all input',true);
 await page.setViewportSize({width:430,height:932});check('Portrait remains native 1080p',(await state()).render_size.join('x')==='1920x1080');await page.setViewportSize({width:932,height:430});
 await tap('#pause .primary');await tap('[data-command="reset"]');await wait(()=>window.alpineTelemetry.grounded);
 // Camera-only QA framing: no fabricated image or mocked renderer/physics.
 await page.evaluate(()=>{const g=window.alpineGame;g.cameraYaw=.45;g.cameraPitch=-.12;g.orbitUntil=performance.now()+100000;});
 const before=(await state()).reflection_frames;await wait(n=>window.alpineTelemetry.reflection_frames>n+2,before);
 const final=await state();check('Reflection target updates across rendered frames',final.reflection_frames>before+2);check('No browser runtime errors',errors.length===0);
 // Stop scheduling frames before synchronous readback on CPU SwiftShader.
 await page.evaluate(()=>{window.requestAnimationFrame=()=>0;});await page.waitForTimeout(1000);
 const png=await page.evaluate(()=>document.getElementById('canvas').toDataURL('image/png'));
 fs.writeFileSync(path.join(out,'alpine-library-water-shafts-1080p.png'),Buffer.from(png.split(',')[1],'base64'));
 const screenshot=await cdp.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});fs.writeFileSync(path.join(out,'alpine-mobile-browser.png'),Buffer.from(screenshot.data,'base64'));
 fs.writeFileSync(path.join(out,'alpine-browser-validation.json'),JSON.stringify({checks,errors,final,driving:driven,physical_phone_tested:false,target_60fps_verified:false,scope:'Actual Chromium mobile emulation + WebGL2/SwiftShader + Rapier WASM; not physical-phone or hardware frame-rate certification.'},null,2)+'\n');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
