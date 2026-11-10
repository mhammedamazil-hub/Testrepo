/* Offline actual Three.js -> lossless PNG sequence -> genuine 1080p60 H.264.
 * No frame interpolation, video-generation model or claim of real-time speed.
 * Requires the existing optional Playwright/Chromium QA dependencies and ffmpeg.
 */
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),{spawnSync}=require('node:child_process');
const root=path.resolve(__dirname,'../..'),cache=path.join(root,'.cache/offline-cinematic'),output=path.join(root,'output');
const seconds=Number(process.env.FILM_SECONDS||3),benchmark=process.argv.includes('--benchmark'),resume=process.argv.includes('--resume');
if(!Number.isFinite(seconds)||seconds<=0||seconds>60)throw Error('FILM_SECONDS must be >0 and <=60');
fs.mkdirSync(cache,{recursive:true});fs.mkdirSync(output,{recursive:true});const frames=path.join(cache,'frames');fs.mkdirSync(frames,{recursive:true});
(async()=>{
 const {chromium:pw}=require(path.join(root,'.cache/browser/node_modules/playwright-core'));
 const {default:chromium}=await import(path.join(root,'.cache/browser/node_modules/@sparticuz/chromium/build/index.js'));
 const libs=[path.join(root,'.cache/browser-runtime/usr/lib/x86_64-linux-gnu'),path.join(root,'.cache/software-graphics/runtime/usr/lib/x86_64-linux-gnu'),'/tmp'].join(':');
 const browser=await pw.launch({executablePath:await chromium.executablePath(),env:{...process.env,LD_LIBRARY_PATH:libs},args:['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist'],headless:true});
 const context=await browser.newContext({viewport:{width:1920,height:1080},deviceScaleFactor:1}),page=await context.newPage(),cdp=await context.newCDPSession(page),errors=[];
 page.on('pageerror',e=>{errors.push(e.message);console.error('BROWSER_ERROR',e.message);});page.on('console',m=>{if(m.type()==='error'){errors.push(m.text());console.error(m.text());}});
 await page.addInitScript(()=>{window.requestAnimationFrame=()=>0;localStorage.setItem('alpine-graphics','full');});
 let settings,last;const start=Date.now();
 try{
  await page.goto(process.env.GAME_URL||'http://127.0.0.1:3001/',{waitUntil:'domcontentloaded'});await page.waitForFunction(()=>window.alpineReady,undefined,{timeout:300000,polling:100});
  settings=await page.evaluate(async seconds=>{const {prepareCinematic}=await import('/src/offline-cinematic.js');window.film=await prepareCinematic(alpineGame,{seconds,msaa:0});return film.settings;},seconds);
  console.log('SETTINGS',JSON.stringify(settings));
  if(!benchmark){const signature=crypto.createHash('sha256').update(fs.readFileSync(path.join(root,'engine/src/offline-cinematic.js'))).update(JSON.stringify(settings)).digest('hex'),manifest=path.join(cache,'render-config.json');if(resume){if(!fs.existsSync(manifest)||JSON.parse(fs.readFileSync(manifest)).signature!==signature)throw Error('Cannot resume: film source/settings differ or manifest is missing. Run without --resume for a new export.');}else fs.writeFileSync(manifest,JSON.stringify({signature,settings},null,2)+'\n');}

  const count=benchmark?3:settings.frames;
  for(let i=0;i<count;i++){
   const file=path.join(frames,String(i).padStart(6,'0')+'.png');if(resume&&!benchmark&&fs.existsSync(file)){const data=fs.readFileSync(file);if(data.length>45&&data.toString('ascii',1,4)==='PNG'&&data.readUInt32BE(16)===1920&&data.readUInt32BE(20)===1080&&data.toString('ascii',data.length-8,data.length-4)==='IEND')continue;}
   const before=Date.now();last=await page.evaluate(i=>film.draw(i),benchmark?i*60:i);
   const shot=await cdp.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false,fromSurface:true});fs.writeFileSync(benchmark?path.join(cache,'preview-'+i+'.png'):file,Buffer.from(shot.data,'base64'));
   if(benchmark||i%15===0||i===count-1)console.log('FRAME',i+1,'/',count,'MS',Date.now()-before,'ELAPSED_S',((Date.now()-start)/1000).toFixed(1));
  }
  if(errors.length)throw Error('Browser errors: '+errors.join('; '));
 }finally{await browser.close();}
 if(benchmark){fs.writeFileSync(path.join(cache,'benchmark.json'),JSON.stringify({settings,elapsed_seconds:(Date.now()-start)/1000,last,errors},null,2)+'\n');return;}
 const ffmpeg=process.env.FFMPEG||spawnSync(path.join(root,'.venv/bin/python'),['-c','import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())'],{encoding:'utf8'}).stdout.trim();
 const video=path.join(output,'alpine-roadster-1080p60.mp4'),credits=fs.readFileSync(path.join(root,'game/CREDITS.md'),'utf8')+'\n\nOffline film modifications: red physical clearcoat paint, authored parked-car camera orbit, larger shadows/reflections, soft artistic contact decal, FXAA and title/credit overlay. Not path tracing or a real-time FPS benchmark.\n';fs.writeFileSync(path.join(output,'alpine-roadster-credits.txt'),credits);
 const result=spawnSync(ffmpeg,['-y','-framerate','60','-start_number','0','-i',path.join(frames,'%06d.png'),'-frames:v',String(settings.frames),'-c:v','libx264','-preset','slow','-crf','17','-pix_fmt','yuv420p','-r','60','-movflags','+faststart','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-metadata','title=Alpine - Roadster 20 / Offline Cinematic','-metadata','comment='+credits,'-an',video],{stdio:'inherit'});if(result.status!==0)throw Error('FFmpeg failed');
 const probe=spawnSync(ffmpeg,['-i',video,'-map','0:v:0','-f','null','-'],{encoding:'utf8'});if(probe.status!==0)throw Error('Full video decode failed');const decoded=[...probe.stderr.matchAll(/frame=\s*(\d+)/g)].at(-1);if(!decoded||Number(decoded[1])!==settings.frames||!probe.stderr.includes('1920x1080')||!probe.stderr.includes('60 fps'))throw Error('Decoded frame count, size or frame rate does not match the requested export');
 const report={settings,video:path.relative(root,video),bytes:fs.statSync(video).size,render_elapsed_seconds:(Date.now()-start)/1000,source_frames:settings.frames,decoded_frames:Number(decoded[1]),video_sha256:crypto.createHash('sha256').update(fs.readFileSync(video)).digest('hex'),interpolated_frames:0,errors,last,decode_validation:probe.stderr};
 fs.writeFileSync(path.join(output,'alpine-roadster-1080p60.json'),JSON.stringify(report,null,2)+'\n');console.log('OFFLINE_1080P60_COMPLETE',video);
})().catch(e=>{console.error(e);process.exitCode=1;});
