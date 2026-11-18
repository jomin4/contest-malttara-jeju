// 사용 가이드 전체 따라가기(01→04): 서버 켠 뒤 `node web/tools/tour_walkthrough.js 1366 800`
const {chromium}=require('playwright');
(async()=>{const W=+process.argv[2]||1366,H=+process.argv[3]||800;
const b=await chromium.launch({args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const p=await (await b.newContext({viewport:{width:W,height:H}})).newPage();
const errs=[];p.on('pageerror',e=>errs.push(String(e)));p.on('console',m=>{if(m.type()==='error')errs.push(m.text())});
await p.goto('http://127.0.0.1:8765/');await p.waitForTimeout(900);
console.log('offer', await p.locator('.guide-offer').count());
await p.screenshot({path:`./${W}-00.png`});
await p.click('text=가이드 시작'); 
let n=0, last='';
for(let k=0;k<40;k++){
  await p.waitForTimeout(700);
  if(!await p.locator('.tour').count()){console.log('tour ended'); break;}
  const st=await p.locator('.tour').getAttribute('data-state');
  const t=(await p.locator('.tour-title').innerText().catch(()=> '')).trim();
  const c=(await p.locator('.tour-count').innerText().catch(()=> '')).trim();
  const sc=(await p.locator('.tour-screen').innerText().catch(()=> '')).trim();
  if(st!=='on'){ console.log('  wait:',sc,t); await p.waitForTimeout(1200); continue; }
  const sig=sc+c; if(sig!==last){ n++; last=sig; console.log(sc,c,t, 'side='+await p.locator('.tour-tip').getAttribute('data-side'));
    await p.screenshot({path:`./${W}-${String(n).padStart(2,'0')}.png`}); }
  // use keyboard on some, click on others
  if(n%2) await p.keyboard.press('ArrowRight'); else await p.click('.tour-actions .btn-primary');
}
console.log('final step', await p.evaluate(()=>document.querySelector('.step.active')?.textContent), 'errors', errs);
await b.close();})();
