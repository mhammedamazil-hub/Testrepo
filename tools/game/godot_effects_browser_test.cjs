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
 const errors=[];page.on('pageerror',e=>{errors.push(e.message);console.log('PAGEERROR',e.message);});page.on('console',m=>console.log(m.type(),m.text()));
 await page.goto('http://127.0.0.1:3000',{waitUntil:'domcontentloaded',timeout:60000});
 await page.waitForFunction(()=>window.alpineReady && window.alpineTelemetry?.live_reflection_frames>3,null,{timeout:180000});
 const b=await page.locator('#canvas').boundingBox();await page.touchscreen.tap(b.x+300/1920*b.width,b.y+790/1080*b.height);
 await page.waitForFunction(()=>window.alpineTelemetry?.playing,null,{timeout:180000});
 const state=await page.evaluate(()=>window.alpineTelemetry);console.log('STATE',state);
 fs.writeFileSync(root+'/docs/game/godot-library-browser-validation.json',JSON.stringify({telemetry:state,errors,physical_phone_tested:false,target_60fps_verified:false,scope:'Actual Godot WebGL2 render/start touch; physics/input suite separately run in native Godot.'},null,2)+'\n');
 await page.evaluate(()=>{window.requestAnimationFrame=()=>0;});
 await page.waitForTimeout(2000);
 const png=await page.evaluate(()=>document.querySelector('canvas').toDataURL());fs.writeFileSync(root+'/docs/game/godot-library-water-shafts-1080p.png',Buffer.from(png.split(',')[1],'base64'));
 fs.writeFileSync(root+'/.cache/godot-library-browser-errors.json',JSON.stringify(errors));await browser.close();if(errors.length)process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1;});
