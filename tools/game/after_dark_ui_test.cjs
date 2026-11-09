/* DOM-only contrast regression. Gameplay/WebGL evidence is the separate browser test. */
const path=require('path'),fs=require('fs'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..');
const {chromium:playwright}=require(path.join(root,'.cache/browser/node_modules/playwright-core'));
(async()=>{
 const {default:chromium}=await import(path.join(root,'.cache/browser/node_modules/@sparticuz/chromium/build/index.js'));
 const libraries=[path.join(root,'.cache/browser-runtime/usr/lib/x86_64-linux-gnu'),path.join(root,'.cache/software-graphics/runtime/usr/lib/x86_64-linux-gnu'),'/tmp',process.env.LD_LIBRARY_PATH||''].join(':');
 const browser=await playwright.launch({executablePath:await chromium.executablePath(),env:{...process.env,LD_LIBRARY_PATH:libraries},args:['--no-sandbox','--disable-dev-shm-usage'],headless:true});
 try{
  const html=fs.readFileSync(path.join(root,'engine/index.html'),'utf8').replace(/<script[^>]*>[\s\S]*?<\/script>/g,'');
  const css=fs.readFileSync(path.join(root,'engine/src/style.css'),'utf8');
  const results=[];
  for(const mobile of [true,false]){
   const context=await browser.newContext({viewport:{width:932,height:430},hasTouch:mobile,isMobile:mobile}),page=await context.newPage();
   await page.setContent(html);await page.addStyleTag({content:css});await page.evaluate(()=>{document.body.dataset.phase='playing';document.body.classList.add('touch');document.getElementById('loading').hidden=true;});
   for(const selector of ['[data-command="reset"]','#sky-button']){
    if(mobile)await page.locator(selector).tap();else await page.locator(selector).hover();
    await page.waitForTimeout(250);
    const style=await page.locator(selector).evaluate(el=>{const s=getComputedStyle(el);return {color:s.color,background:s.backgroundColor};});
    assert.equal(style.color,mobile?'rgb(233, 240, 247)':'rgb(9, 24, 41)');
    if(!mobile)assert.equal(style.background,'rgb(188, 231, 241)');
    results.push({mobile,selector,...style});
   }
   await context.close();
  }
  fs.writeFileSync(path.join(root,'docs/game/after-dark/ui-contrast-validation.json'),JSON.stringify({scope:'DOM-only actual HTML/CSS regression after correcting touch sticky-hover contrast; no renderer/gameplay is mocked or claimed by this check.',checks:results,passed:true},null,2)+'\n');
  console.log('TOUCH_AND_DESKTOP_BUTTON_CONTRAST_PASS');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
