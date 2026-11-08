/* Render the real Web export in Chromium/SwiftShader. Not a GPU-speed claim.
   npm install --prefix .cache/browser playwright-core @sparticuz/chromium */
const path=require('path'),fs=require('fs');
const root=path.resolve(__dirname,'../..');
const {chromium:playwright}=require(path.join(root,'.cache/browser/node_modules/playwright-core'));
(async()=>{
 const {default:chromium}=await import(path.join(root,'.cache/browser/node_modules/@sparticuz/chromium/build/index.js'));
 const executablePath=await chromium.executablePath();
 const libraryPath=[path.join(root,'.cache/browser-runtime/usr/lib/x86_64-linux-gnu'),path.join(root,'.cache/software-graphics/runtime/usr/lib/x86_64-linux-gnu'),'/tmp',process.env.LD_LIBRARY_PATH||''].join(':');
 const browser=await playwright.launch({executablePath,env:{...process.env,LD_LIBRARY_PATH:libraryPath},args:['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist'],headless:true});
 const page=await browser.newPage({viewport:{width:1920,height:1080},deviceScaleFactor:1});
 const errors=[],messages=[];
 page.on('console',msg=>{messages.push(msg.text());if(msg.type()==='error')errors.push(msg.text());console.log(msg.type(),msg.text());});
 page.on('pageerror',err=>{errors.push(err.message);console.error('PAGE ERROR',err.message);});
 await page.goto(process.env.GAME_URL||'http://127.0.0.1:3000',{waitUntil:'domcontentloaded',timeout:60000});
 await page.waitForFunction(()=>window.alpineTelemetry,null,{timeout:180000});
 console.log('MAIN READY',await page.evaluate(()=>window.alpineTelemetry));
 const out=path.join(root,'docs/game');fs.mkdirSync(out,{recursive:true});
 async function capture(name){
  const png=await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>resolve(document.getElementById('canvas').toDataURL('image/png')))));
  fs.writeFileSync(path.join(out,name),Buffer.from(png.split(',')[1],'base64'));
 }
 await capture('menu-1080p.png');
 await page.mouse.click(300,790);
 await page.waitForFunction(()=>window.alpineTelemetry?.playing,null,{timeout:90000});
 await page.waitForTimeout(2000);
 const initial=await page.evaluate(()=>window.alpineTelemetry);
 await capture('walking-1080p.png');
 await page.keyboard.press('e');
 await page.waitForFunction(()=>window.alpineTelemetry?.driving,null,{timeout:90000});
 const before=await page.evaluate(()=>window.alpineTelemetry);
 await page.keyboard.down('w');
 await page.waitForFunction(before=>{const t=window.alpineTelemetry;return t&&Math.hypot(t.car[0]-before[0],t.car[2]-before[2])>3;},before.car,{timeout:180000});
 await page.keyboard.up('w');
 console.log('ACTUAL DRIVING MOTION VERIFIED');
 const driving=await page.evaluate(()=>window.alpineTelemetry);
 await capture('driving-1080p.png');
 await page.keyboard.down('Space');
 await page.waitForFunction(()=>Math.abs(window.alpineTelemetry?.speed_mps??10)<0.1,null,{timeout:90000});
 await page.keyboard.up('Space');
 await page.keyboard.press('e');
 await page.waitForFunction(()=>window.alpineTelemetry?.driving===false,null,{timeout:90000});
 const after=await page.evaluate(()=>window.alpineTelemetry);
 await page.keyboard.press('F8');
 await page.waitForTimeout(18000);
 const final=await page.evaluate(()=>window.alpineTelemetry);
 const gpu=await page.evaluate(()=>{const c=document.getElementById('canvas'),g=c.getContext('webgl2');if(!g)return null;const x=g.getExtension('WEBGL_debug_renderer_info');return {canvas:[c.width,c.height],renderer:x?g.getParameter(x.UNMASKED_RENDERER_WEBGL):g.getParameter(g.RENDERER),vendor:x?g.getParameter(x.UNMASKED_VENDOR_WEBGL):g.getParameter(g.VENDOR)};});
 const distance=Math.hypot(driving.car[0]-before.car[0],driving.car[2]-before.car[2]);
 const report={status:distance>1&&after.driving===false?'BROWSER_GAMEPLAY_PASS':'BROWSER_GAMEPLAY_FAIL',engine:'Actual Godot 4.4.1 Web release',gpu,initial,before,driving,after,final,distance_driven_meters:distance,console_errors:errors,messages,
  performance_scope:'Sandbox headless Chromium software graphics; not representative of hardware GPU speed',
  target_1080p_verified:final.render_size[0]===1920&&final.render_size[1]===1080&&gpu.canvas[0]===1920&&gpu.canvas[1]===1080,
  target_60fps_verified:final.fps>=60&&final.p95_frame_ms>0&&final.p95_frame_ms<=16.67};
 fs.writeFileSync(path.join(out,'browser-validation.json'),JSON.stringify(report,null,2)+'\n');
 console.log('BROWSER RESULT',JSON.stringify(report,null,2));
 await browser.close();
 if(report.status!=='BROWSER_GAMEPLAY_PASS'||errors.some(x=>x.includes('SCRIPT ERROR')))process.exitCode=1;
})().catch(err=>{console.error(err);process.exit(1);});
