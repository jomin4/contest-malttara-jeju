// 실제 앱 화면 자동 녹화(서버 run.py가 127.0.0.1:8765에서 실행 중이어야 함).
// 화면 조작은 실제 사용자와 같고, 자막·'실제 실행 화면' 표시만 덧씌운다(앱 동작은 바꾸지 않음).
const path = require('path');
const {chromium} = require('playwright');
const {record, sleep, W, H} = require('./lib/recorder');

const BASE = process.env.BASE || 'http://127.0.0.1:8765/';
const OUT = path.resolve(__dirname, '../../submission/demo/segments');
const SENTENCE = '2박 3일 동안 바다를 보며 여유롭게 쉬고, 현지 음식도 먹고 싶어요';

async function overlay(page) {
  await page.evaluate(() => {
    if (document.getElementById('__live')) return;
    const live = document.createElement('div');
    live.id = '__live';
    live.innerHTML = '<span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:#e11d48;margin-right:8px;vertical-align:1px"></span>실제 실행 화면';
    Object.assign(live.style, {position: 'fixed', left: '14px', bottom: '14px', zIndex: 2147483647, pointerEvents: 'none',
      background: 'rgba(255,255,255,.94)', color: '#111', font: '600 11px "Noto Sans KR",sans-serif',
      padding: '4px 10px', borderRadius: '999px', border: '1px solid #e5e7eb', boxShadow: '0 1px 3px rgba(0,0,0,.08)'});
    document.body.appendChild(live);
    const cap = document.createElement('div');
    cap.id = '__cap';
    Object.assign(cap.style, {position: 'fixed', left: '50%', bottom: '30px', transform: 'translateX(-50%)',
      zIndex: 2147483647, pointerEvents: 'none', background: 'rgba(15,23,42,.88)', color: '#fff',
      font: '600 19px/1.45 "Noto Sans KR",sans-serif', padding: '10px 24px', borderRadius: '12px',
      maxWidth: '86%', textAlign: 'center', opacity: '0', transition: 'opacity .35s', letterSpacing: '-.2px',
      whiteSpace: 'nowrap'});
    document.body.appendChild(cap);
  });
}

async function caption(page, html, holdMs = 0, pos = 'bottom') {
  await overlay(page);
  await page.evaluate(([h, pos]) => {
    const c = document.getElementById('__cap');
    if (!h) { c.style.opacity = '0'; return; }
    c.style.top = pos === 'top' ? '100px' : 'auto';
    c.style.bottom = pos === 'top' ? 'auto' : '30px';
    c.innerHTML = h; c.style.opacity = '1';
  }, [html, pos]);
  if (holdMs) await sleep(holdMs);
}

async function smoothScroll(page, dy, ms = 1200) {
  await page.evaluate(([dy, ms]) => new Promise(res => {
    const el = document.scrollingElement, s = el.scrollTop, t0 = performance.now();
    const step = t => { const k = Math.min(1, (t - t0) / ms); el.scrollTop = s + dy * (0.5 - Math.cos(Math.PI * k) / 2);
      k < 1 ? requestAnimationFrame(step) : res(); };
    requestAnimationFrame(step);
  }), [dy, ms]);
}

(async () => {
  const browser = await chromium.launch({channel: 'chrome', headless: true, args: ['--ignore-gpu-blocklist']});
  // 키오스크 기준 화면(1366×768)을 1.4배로 찍어 1920×1080 영상에서 글자를 키운다.
  const ctx = await browser.newContext({viewport: {width: 1366, height: 768}, deviceScaleFactor: W / 1366});
  const page = await ctx.newPage();
  await page.goto(BASE);
  await sleep(1200);
  await page.click('.guide-offer button:has-text("괜찮아요")').catch(() => {});
  await overlay(page);
  await sleep(300);

  // ── 01 여행 설명 ───────────────────────────────────────────
  await record(page, path.join(OUT, '10_app_01.mp4'), async () => {
    await caption(page, '① 여행을 <b>한 줄</b>로 말합니다', 1600);
    await page.click('textarea');
    await page.keyboard.type(SENTENCE, {delay: 55});
    await sleep(500);
    await page.keyboard.press('Enter');
    await page.waitForSelector('.chips', {timeout: 60000});
    await sleep(800);
    await caption(page, 'AI가 조건을 읽어 칩으로 보여 주고, 말하지 않은 조건은 <b>미반영</b>으로 둡니다', 4200);
    await caption(page, '동네별 붐비는 정도 — 제주데이터허브 563 읍면동 방문/거주 비율', 3200);
  });

  // ── 02 경로 만들기 ─────────────────────────────────────────
  await record(page, path.join(OUT, '11_app_02.mp4'), async () => {
    await caption(page, '② AI Agent가 작업을 계획하고 도구를 차례로 실행 — 판단 주체(AI/규칙)가 로그에 남습니다');
    await page.locator('button:has-text("경로 만들기")').last().click();
    await page.waitForSelector('text=경로가 준비됐어요', {timeout: 90000});
    await sleep(1500);
    await caption(page, '③ 날짜별 일정과 지도 — 거리는 <b>직선 km</b>이며 이동시간이 아닙니다', 3800);
    await page.locator('button:has-text("근거 보기")').first().click();
    await sleep(600);
    await caption(page, '장소마다 근거: 관심사 일치, 읍면동 지표(563), 반경 1km 렌터카 체류(1208)', 4200);
    await page.click('button:has-text("왜 이렇게 짰나요?")');
    await sleep(1200);
    await caption(page, '④ 왜 이렇게 짰나요? — 계획·점수·검증 단계를 데이터 출처·기간과 함께 설명', 4500);
  });

  // ── 시연: 오류 주입 → 스스로 검증·수정 ─────────────────────
  await record(page, path.join(OUT, '12_app_inject.mp4'), async () => {
    await smoothScroll(page, -6000, 900);
    await page.keyboard.press('Control+Shift+D');
    await sleep(500);
    await caption(page, '⑤ 시연: 일부러 다른 권역 장소를 넣어 오류를 만듭니다', 1800);
    await page.click('label.switch:has-text("오류 주입")');
    await sleep(400);
    await page.click('button:has-text("다시 만들기")');
    await caption(page, 'Agent가 검증에서 위반을 찾아 스스로 고치고 다시 검증합니다 (최대 2회)', 0, 'top');
    await page.waitForSelector('text=경로가 준비됐어요', {timeout: 90000});
    await sleep(1200);
    await page.click('button:has-text("왜 이렇게 짰나요?")');
    await sleep(1500);
    await caption(page, '위반 → 수정 → 재검증 통과 과정이 그대로 기록됩니다', 4200, 'top');
    await smoothScroll(page, -6000, 900);
  });

  // ── 03 미리보기 ────────────────────────────────────────────
  await record(page, path.join(OUT, '13_app_03.mp4'), async () => {
    await caption(page, '⑥ 말을 타고 미리 둘러보기 — 지명을 치는 만큼 말이 달립니다 (게임은 선택, 목록도 가능)', 0, 'top');
    await page.click('button:has-text("미리 둘러보기")');
    await sleep(3000);
    const keys = ['2', '3', '1'];
    const labels = ['꼭 갈래요', '별로예요', '좋아요'];
    for (let i = 0; i < 3; i++) {
      const name = (await page.locator('.target .name').innerText()).trim();
      await page.click('#typein');
      await page.keyboard.type(name, {delay: 140});
      await sleep(900);
      await caption(page, `가상 도착 → 반응 <b>${labels[i]}</b> (가상 탐험은 실제 방문 기록과 따로 저장)`, 0, 'top');
      await sleep(900);
      await page.keyboard.press(keys[i]);
      await sleep(900);
      await page.keyboard.press('Enter');
      await sleep(700);
    }
    await sleep(600);
  });

  // ── 04 다시 짜기 ───────────────────────────────────────────
  await record(page, path.join(OUT, '14_app_04.mp4'), async () => {
    await caption(page, '⑦ 반응을 반영해 다시 짭니다 — 꼭 갈래요는 고정, 별로예요는 교체 (코드가 강제)');
    await page.locator('button:has-text("다시 짜기")').last().click();
    await page.waitForSelector('text=나만의 제주 여행 계획', {timeout: 90000});
    await sleep(1800);
    const ch = page.locator('.changes').first();
    if (await ch.count()) { await ch.scrollIntoViewIfNeeded(); await sleep(400); }
    await caption(page, '무엇이 왜 바뀌었는지 전후를 비교해 보여 줍니다 — 최종 선택은 사용자', 4200);
    await smoothScroll(page, -6000, 800);
    await page.click('.actions button:has-text("휴대폰")').catch(async () => {
      await page.click('button:has-text("QR")').catch(() => {});
    });
    await sleep(800);
    await caption(page, '⑧ QR로 휴대폰에 담기 — 인터넷 없이 일정 글이 그대로 담깁니다', 3800);
    await page.keyboard.press('Escape');
    await sleep(600);
  });

  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
