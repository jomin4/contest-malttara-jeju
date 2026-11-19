// 적응형 점검: 서버(run.py) 켠 뒤 `node web/tools/check_responsive.js 360,768,1366,1920 [shot]` — 가로 넘침·눌린 글자 탐지 (Playwright 필요)
const {chromium}=require('playwright');
const widths=(process.argv[2]||'375,768,940,1024,1280,1440,1920').split(',').map(Number);
const SHOT=process.argv[3]==='shot';
(async()=>{const b=await chromium.launch({args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
for(const W of widths){const H=W<800?800:(W<1100?760:900);
const ctx=await b.newContext({viewport:{width:W,height:H}});const p=await ctx.newPage();
const errs=[];p.on('pageerror',e=>errs.push(String(e)));
const check=async(tag)=>{const r=await p.evaluate(()=>{const vw=document.documentElement.clientWidth;const out={overflow:document.documentElement.scrollWidth-vw,bad:[]};
for(const el of document.querySelectorAll('h1,h2,h3,p,button,.card,.badge,.transport-note,.chip,label,a,li,section,.pagehead,.actions')){const s=getComputedStyle(el);if(s.display==='none'||s.visibility==='hidden')continue;
const rc=el.getBoundingClientRect();if(!rc.width)continue;const txt=(el.innerText||'').trim();
if(rc.right>vw+1&&!el.closest('.no-clip'))out.bad.push('OUT '+el.tagName+'.'+el.className.toString().slice(0,30)+' r='+Math.round(rc.right)+' "'+txt.slice(0,20)+'"');
const lh=parseFloat(s.lineHeight)||parseFloat(s.fontSize)*1.4;if(txt.length>8&&rc.width<170&&rc.height>lh*3.2&&/^(H1|H2|H3|P|BUTTON|LI|DIV)$/.test(el.tagName))out.bad.push('SQUASH '+el.tagName+'.'+el.className.toString().slice(0,30)+' w='+Math.round(rc.width)+' "'+txt.slice(0,20)+'"');}
out.bad=[...new Set(out.bad)].slice(0,12);return out;});
console.log(W,tag,'overflow',r.overflow,r.bad.length?'\n   '+r.bad.join('\n   '):'');
if(SHOT)await p.screenshot({path:`./${W}-${tag}.png`,fullPage:true});};
try{
await p.goto('http://127.0.0.1:8765/');await p.waitForTimeout(700);await check('01');await p.keyboard.press('Escape');await p.waitForTimeout(200);
await p.click('.example >> nth=0');await p.waitForTimeout(900);await check('01b');
await p.click('text=경로 만들기 >> nth=-1');await p.waitForSelector('text=경로가 준비됐어요',{timeout:25000});await p.waitForTimeout(400);await check('02');
await p.click('text=미리 둘러보기');await p.waitForTimeout(1500);await check('03');
await p.click('text=다시 짜기 >> nth=-1');await p.waitForSelector('text=나만의 제주 여행 계획',{timeout:25000});await p.waitForTimeout(800);await check('04');
}catch(e){console.log(W,'FAIL',String(e).slice(0,200));if(SHOT)await p.screenshot({path:`./${W}-fail.png`});}
if(errs.length)console.log(W,'errors',errs);await ctx.close();}
await b.close();})();
