// 모션 그래픽 장면(scenes/scenes.html#장면) 녹화 → submission/demo/segments/*.mp4
const path = require('path');
const {pathToFileURL} = require('url');
const {chromium} = require('playwright');
const {record, sleep, W, H} = require('./lib/recorder');

const OUT = path.resolve(__dirname, '../../submission/demo/segments');
const PAGE = pathToFileURL(path.join(__dirname, 'scenes', 'scenes.html')).href;
// 파일 이름 순서 = 영상 순서 (앱 녹화는 10~14)
// 시연 영상 위주: 타이틀·아웃트로만 넣는다. (problem·arch·gate·layers·cost 장면은 scenes.html에 남겨 둠)
const SCENES = [['00_title', 'title'], ['90_outro', 'outro']];

(async () => {
  const only = process.argv.slice(2);
  const browser = await chromium.launch({channel: 'chrome', headless: true});
  for (const [file, scene] of SCENES) {
    if (only.length && !only.includes(scene)) continue;
    const ctx = await browser.newContext({viewport: {width: W, height: H}, deviceScaleFactor: 1});
    const page = await ctx.newPage();
    await page.goto('about:blank');
    await record(page, path.join(OUT, file + '.mp4'), async () => {
      await page.goto(`${PAGE}#${scene}`);
      await page.waitForLoadState('load');
      await page.evaluate(() => document.fonts.ready);
      const ms = await page.evaluate(() => window.DURATION);
      await sleep(ms);
    }, {fadeIn: 0, fadeOut: 0.5});
    await ctx.close();
  }
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
