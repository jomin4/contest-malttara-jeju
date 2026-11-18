// 클릭 시나리오 검증 54항목: 서버(run.py) 켠 뒤 `node web/tools/e2e_scenarios.js 1366 800` (Playwright 필요)
const {chromium}=require('playwright');
const BASE=process.env.BASE||'http://127.0.0.1:8765/';
const results=[]; const ok=(name,cond,info='')=>{results.push([cond?'PASS':'FAIL',name,info]);};
const W=+process.argv[2]||1366,H=+process.argv[3]||800;
(async()=>{const b=await chromium.launch({args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const newPage=async(opts={})=>{const c=await b.newContext({viewport:{width:W,height:H},...opts});const p=await c.newPage();p.errs=[];p.reqs=[];
 p.on('pageerror',e=>p.errs.push(String(e)));p.on('console',m=>{if(m.type()==='error'&&!/Failed to load resource/.test(m.text()))p.errs.push(m.text().slice(0,160))});
 p.on('request',r=>{if(r.url().includes('/api/'))p.reqs.push(r.method()+' '+r.url().split('8765')[1]+(r.postData()?' '+r.postData().slice(0,3000):''))});return p;};
const shot=(p,n)=>p.screenshot({path:`./${W}-${n}.png`});
try{
// ── S1 정상 흐름 (키보드) ──
let p=await newPage(); await p.goto(BASE); await p.waitForTimeout(800); await p.click('.guide-offer button:has-text("괜찮아요")');
ok('01 첫 화면: 경로 만들기 비활성', await p.locator('button:has-text("경로 만들기")').last().isDisabled());
await p.click('textarea'); await p.keyboard.type('3박 4일 동안 오름이랑 숲을 천천히 걷고 카페도 가고 싶어요'); await p.keyboard.press('Enter'); await p.waitForTimeout(1200);
const chipsTxt=(await p.locator('.chips').first().innerText()).replace(/\s+/g,' ');
ok('01 Enter로 조건 해석(기간 3박 4일)', /3박\s*4일/.test(chipsTxt), chipsTxt);
ok('01 관심사 오름·숲·카페', /오름/.test(chipsTxt)&&/숲/.test(chipsTxt)&&/카페/.test(chipsTxt), chipsTxt);
// 숙소·범위
await p.locator('.plan-panel path.emd').nth(5).click(); await p.waitForTimeout(250);
const stayTxt=await p.locator('.plan-panel').innerText(); ok('01 숙소 동네 선택 표시', /숙소/.test(stayTxt), stayTxt.slice(0,60));
await p.click('.area-opt >> nth=1'); await p.waitForTimeout(200);
ok('01 다닐 범위 선택', await p.locator('.area-opt.on').count()===1);
// 다시 읽기 후 숙소 유지
await p.click('button:has-text("다시 읽기")'); await p.waitForTimeout(1000);
ok('01 다시 읽기 후 숙소·범위 유지', /숙소 [^—]*·/.test(await p.locator('.plan-panel').innerText()) && await p.locator('.area-opt.on:has-text("숙소 근처")').count()===1);
// 여유 칩 변경
await p.locator('.chip:has-text("여유")').first().click(); await p.waitForTimeout(200);
const optCnt=await p.locator('.pop .opt').count(); ok('01 칩 팝업 열림', optCnt>0, optCnt);
await p.locator('.pop .opt:has-text("빡빡하게")').first().click(); await p.waitForTimeout(300);
ok('01 여유 → 빡빡하게 반영', /빡빡하게/.test(await p.locator('.chips').first().innerText()));
await shot(p,'01');
// 경로 만들기 (더블클릭 → 배치 1번만)
await p.locator('button:has-text("경로 만들기")').last().dblclick(); 
await p.waitForSelector('text=경로가 준비됐어요',{timeout:30000}); await p.waitForTimeout(400);
const batchA=p.reqs.filter(r=>r.startsWith('POST /api/batch/a'));
ok('02 더블클릭해도 배치 1번', batchA.length===1, batchA.length);
ok('02 goal에 stay·area 포함', /"stay":\{/.test(batchA[0]||'') && /"area":"near"/.test(batchA[0]||''));
const days=await p.locator('.daylist .day').count(); ok('02 4일 일정', days===4, days);
const perDay=await p.locator('.daylist .day').evaluateAll(ds=>ds.map(d=>d.querySelectorAll('[data-place]').length));
ok('02 빡빡하게 = 하루 5곳', perDay.every(n=>n===5), perDay.join(','));
await p.locator('button:has-text("근거 보기")').first().click(); await p.waitForTimeout(200);
ok('02 근거 펼침', (await p.locator('ul.why li').count())>0);
await p.locator('.map-card .daytab:has-text("2일차")').click(); await p.waitForTimeout(200);
ok('02 지도 일차 탭 → 목록도 2일차만', (await p.locator('.daylist .day').count())===1);
await p.locator('.map-card .daytab:has-text("전체")').click();
await p.click('button:has-text("왜 이렇게 짰나요?")'); await p.waitForTimeout(900);
const whyTop=await p.locator('#why').evaluate(e=>e.getBoundingClientRect().top);
ok('02 왜 버튼 → 근거 섹션으로 스크롤', whyTop<200, Math.round(whyTop));
ok('02 근거 섹션 5단계 이상', (await p.locator('.why-step').count())>=5);
await shot(p,'02');
// ── 03 게임 ──
await p.click('button:has-text("미리 둘러보기")'); await p.waitForTimeout(2000);
ok('03 게임 화면', await p.locator('.page-game').count()===1);
let typed=0;
for(let i=0;i<3;i++){
  const name=(await p.locator('.target .name').innerText()).trim();
  await p.click('#typein'); await p.keyboard.type(name,{delay:5}); await p.waitForTimeout(600);
  const arrived=await p.locator('.typebar.arrived').count(); ok(`03 ${i+1}번째 '${name}' 입력 → 도착 패널`, arrived===1);
  const before=p.reqs.filter(r=>/feedback/.test(r)).length;
  await p.keyboard.press(String([2,3,1][i])); await p.waitForTimeout(450);
  ok(`03 숫자키 ${[2,3,1][i]} 반응 전송`, p.reqs.filter(r=>/feedback/.test(r)).length===before+1);
  await p.keyboard.press('Enter'); await p.waitForTimeout(500); typed++;
}
// 건너뛰기
const skipN=await p.locator('button:has-text("건너뛰기")').count();
if(skipN){ await p.click('button:has-text("건너뛰기")'); await p.waitForTimeout(400); }
ok('03 건너뛰기 동작', skipN>0);
const tally=await p.locator('.tally').first().innerText().catch(()=> ''); ok('03 반응 집계 표시', /1/.test(tally), tally.replace(/\s+/g,' '));
// 2D·목록
await p.click('.seg button:has-text("2D")'); await p.waitForTimeout(500);
ok('03 2D 전환', await p.locator('.stage .map-svg').count()>0);
await p.click('.seg button:has-text("목록")'); await p.waitForTimeout(500);
ok('03 목록 모드', await p.locator('.page-game').count()===0);
await shot(p,'03');
const evs=p.reqs.filter(r=>r.startsWith('POST /api/events'));
ok('03 반응·도착 이벤트 전송', evs.filter(e=>/feedback/.test(e)).length>=3 && evs.filter(e=>/virtual_arrival/.test(e)).length>=3, evs.length);
// ── 04 ──
await p.locator('button:has-text("다시 짜기")').last().click();
await p.waitForSelector('text=나만의 제주 여행 계획',{timeout:30000}); await p.waitForTimeout(800);
const chg=await p.locator('.changes li').allInnerTexts();
ok('04 반응 반영 변경 표시(꼭 갈래요 고정/별로예요 교체)', chg.some(t=>/고정/.test(t)) && chg.some(t=>/교체|제외/.test(t)), chg.join(' | ').slice(0,200));
await p.click('button:has-text("휴대폰으로 가져가기")'); await p.waitForTimeout(400);
ok('04 QR 모달', await p.locator('.qr-box svg, .qr-box img').count()>0);
const qrText=await p.locator('.qr-preview').innerText(); ok('04 QR 내용에 일차 포함', /1일차/.test(qrText)&&/4일차/.test(qrText));
await p.keyboard.press('Escape'); await p.waitForTimeout(200);
const escClosed=await p.locator('.qr-modal').count()===0; ok('04 Esc로 QR 닫힘', escClosed);
if(!escClosed) await p.click('.qr-top button');
const [pop]=await Promise.all([p.context().waitForEvent('page',{timeout:5000}).catch(()=>null), p.click('.actions button:has-text("인쇄")')]);
if(pop){await pop.waitForLoadState(); const t=await pop.innerText('body'); ok('04 인쇄 문서 열림', /1일차/.test(t), t.length); await pop.close();} else ok('04 인쇄 문서 열림',false);
ok('04 차트 표시', (await p.locator('.charts svg').count())>0);
// 직접 고르기 → 다시
await p.click('.view-switch button:has-text("직접 고르기")'); await p.waitForSelector('.pick-row');
await p.locator('.pick-row:not(:has(.badge)) .btn').first().click(); await p.waitForTimeout(150);
await p.click('text=담은 장소 넣어 다시 짜기'); await p.waitForSelector('text=나만의 제주 여행 계획',{timeout:30000}); await p.waitForTimeout(800);
const bReqs=p.reqs.filter(r=>r.startsWith('POST /api/batch/b'));
ok('04 직접 고르기 재실행(picks 전송)', bReqs.length===2 && /picks/.test(bReqs[1]), bReqs.length);
const ch2=await p.locator('.changes li').allInnerTexts(); ok('04 직접 고름 변경 표시', ch2.some(t=>/직접/.test(t)), ch2.join(' | ')+' // '+(bReqs[1]||'').slice(0,200));
await shot(p,'04');
// 헤더 단계 이동
await p.click('.step:has-text("02")'); await p.waitForTimeout(400);
ok('헤더: 02로 돌아가기(결과 유지)', /경로가 준비됐어요/.test(await p.innerText('h1')));
await p.click('.step:has-text("04")'); await p.waitForTimeout(400);
ok('헤더: 04로 다시(재실행 없이)', p.reqs.filter(r=>r.startsWith('POST /api/batch/b')).length===2);
// 처음부터
await p.click('button[title="처음부터"]'); await p.waitForTimeout(400);
ok('처음부터 → 01 초기화 + 다음 사람에게 가이드 제안', (await p.inputValue('textarea'))==='' && /한 줄로/.test(await p.innerText('h1')) && await p.locator('.guide-offer').count()===1);
ok('S1 콘솔 오류 없음', p.errs.length===0, p.errs.join(' / '));
await p.context().close();

// ── S2 기간 없음 / 범위 초과 / 빈 입력 ──
p=await newPage(); await p.goto(BASE); await p.waitForTimeout(600); await p.click('.guide-offer button:has-text("괜찮아요")');
await p.click('textarea'); await p.keyboard.press('Enter'); await p.waitForTimeout(500);
ok('빈 입력 Enter → 오류 없이 유지', p.errs.length===0 && await p.locator('button:has-text("경로 만들기")').last().isDisabled());
await p.fill('textarea','바다 보고 맛있는 거 먹고 싶어요'); await p.keyboard.press('Enter'); await p.waitForTimeout(1000);
ok('기간 없음 → 경로 만들기 비활성 + 안내', await p.locator('button:has-text("경로 만들기")').last().isDisabled() && /기간/.test(await p.innerText('.conds')), (await p.innerText('.conds')).slice(0,80));
await p.fill('textarea','9박 10일 제주 일주'); await p.keyboard.press('Enter'); await p.waitForTimeout(1000);
const t9=await p.innerText('.conds'); const dis9=await p.locator('button:has-text("경로 만들기")').last().isDisabled();
ok('9박 10일(최대 7일 초과) → 막거나 안내', dis9 || /7일|최대/.test(t9), t9.slice(0,120));
await p.fill('textarea','x'.repeat(3000)); await p.keyboard.press('Enter'); await p.waitForTimeout(1200);
ok('3000자 입력 → 오류 없이 처리', p.errs.length===0, p.errs.join('/'));
await p.fill('textarea','<img src=x onerror=alert(1)> 2박 3일'); await p.keyboard.press('Enter'); await p.waitForTimeout(1000);
ok('HTML 입력이 실행되지 않음(XSS)', await p.locator('img[src="x"]').count()===0);
await p.context().close();

// ── S3 시연 모드 오류 주입 ──
p=await newPage(); await p.goto(BASE); await p.waitForTimeout(600); await p.click('.guide-offer button:has-text("괜찮아요")');
await p.keyboard.press('Control+Shift+D'); await p.waitForTimeout(300);
await p.click('.example >> nth=0'); await p.waitForTimeout(900);
await p.locator('button:has-text("경로 만들기")').last().click(); await p.waitForTimeout(300);
const inj=await p.locator('label.switch:has-text("오류 주입") input').count();
if(inj){ await p.waitForSelector('text=경로가 준비됐어요',{timeout:30000}); await p.click('label.switch:has-text("오류 주입")'); await p.click('button:has-text("다시 만들기")'); await p.waitForSelector('text=경로가 준비됐어요',{timeout:30000}); await p.waitForTimeout(300);
  const lastA=p.reqs.filter(r=>r.startsWith('POST /api/batch/a')).pop();
  ok('시연: 오류 주입 요청', /"inject_error":true/.test(lastA||''));
  await p.click('.why-step >> nth=0').catch(()=>{});
  const log=await p.locator('.why-timeline').innerText().catch(()=> '');
  ok('시연: 검증 실패 → 수정 기록 표시', /고쳤|교체|위반|fail|수정/.test(log), log.slice(0,150));
} else ok('시연 모드 켜짐(Ctrl+Shift+D)',false);
ok('S3 콘솔 오류 없음', p.errs.length===0, p.errs.join(' / '));
await p.context().close();

// ── S4 자동 초기화(120초 무입력) ──
p=await newPage(); await p.clock.install(); await p.goto(BASE); await p.waitForTimeout(600); await p.click('.guide-offer button:has-text("괜찮아요")');
await p.click('.example >> nth=0'); await p.waitForTimeout(900);
await p.clock.fastForward(122000); await p.waitForTimeout(300);
const modal=await p.locator('.modal').count(); ok('120초 무입력 → 초기화 예고 모달(15초)', modal===1);
await p.clock.fastForward(16000); await p.waitForTimeout(300);
ok('135초 → 01 초기화', (await p.inputValue('textarea'))==='');
await p.context().close();

// ── S5 서버 끊김 ──
p=await newPage(); await p.goto(BASE); await p.waitForTimeout(600); await p.click('.guide-offer button:has-text("괜찮아요")');
await p.click('.example >> nth=0'); await p.waitForTimeout(900);
await p.route('**/api/batch/a', r=>r.abort()); 
await p.locator('button:has-text("경로 만들기")').last().click(); await p.waitForTimeout(1500);
const errTxt=await p.innerText('body'); ok('서버 끊김 → 한국어 안내 + 다시 시도', /서버에 연결할 수 없습니다/.test(errTxt) && await p.locator('button:has-text("다시")').count()>0);
await p.unroute('**/api/batch/a'); await p.locator('button:has-text("다시 시도")').first().click();
await p.waitForSelector('text=경로가 준비됐어요',{timeout:30000}).then(()=>ok('복구 후 다시 시도 성공',true)).catch(()=>ok('복구 후 다시 시도 성공',false));
await p.route('**/api/places**', r=>r.fulfill({status:500, contentType:'application/json', body:'{"error":"서버 오류가 났습니다 (Test)"}'}));
await p.click('.view-switch button:has-text("직접 고르기")'); await p.waitForTimeout(800);
ok('목록 API 오류 → 안내 + 다시 시도', /서버 오류/.test(await p.innerText('.picker')) && await p.locator('.picker button:has-text("다시 시도")').count()===1);
ok('S5 페이지 오류 없음', p.errs.filter(e=>!/서버/.test(e)).length===0, p.errs.join(' / '));
await p.context().close();
}catch(e){ok('스크립트 예외',false,String(e).slice(0,300));}
await b.close();
const f=results.filter(r=>r[0]==='FAIL');
for(const r of results) console.log(r[0], r[1], r[0]==='FAIL'||process.env.V? '— '+String(r[2]).slice(0,200):'');
console.log(`\n${results.length-f.length}/${results.length} PASS`);
})();
