// CDP screencast(고화질 JPEG) → ffmpeg-static(H.264) 녹화기. Playwright 기본 녹화(VP8 1Mbps)보다 글자가 선명하다.
const fs = require('fs');
const os = require('os');
const path = require('path');
const {spawnSync} = require('child_process');
const ffmpeg = require('ffmpeg-static');

const W = 1920, H = 1080, FPS = 30;

async function record(page, outFile, fn, {fadeIn = 0.4, fadeOut = 0.4} = {}) {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'malttara-rec-'));
  const cdp = await page.context().newCDPSession(page);
  const frames = [];
  let n = 0;
  cdp.on('Page.screencastFrame', ({data, metadata, sessionId}) => {
    const f = path.join(tmp, `${String(n++).padStart(6, '0')}.jpg`);
    fs.writeFileSync(f, Buffer.from(data, 'base64'));
    frames.push({f, t: metadata.timestamp});
    cdp.send('Page.screencastFrameAck', {sessionId}).catch(() => {});
  });
  const t0 = Date.now() / 1000;
  await cdp.send('Page.startScreencast', {format: 'jpeg', quality: 92, maxWidth: W, maxHeight: H, everyNthFrame: 1});
  await fn();
  const tEnd = Date.now() / 1000;
  await cdp.send('Page.stopScreencast');
  await new Promise(r => setTimeout(r, 150));
  if (!frames.length) throw new Error('녹화된 프레임이 없습니다: ' + outFile);

  // 프레임마다 다음 프레임까지의 시간을 길이로 쓴다(화면이 안 바뀌면 프레임이 오지 않으므로).
  const lines = [];
  frames[0].t = Math.min(frames[0].t, t0);
  for (let i = 0; i < frames.length; i++) {
    const next = i + 1 < frames.length ? frames[i + 1].t : tEnd;
    const d = Math.max(0.001, next - frames[i].t);    // 실제 간격 그대로(30fps보다 빠른 프레임은 fps 필터가 솎는다)
    lines.push(`file '${frames[i].f.replace(/\\/g, '/')}'`, `duration ${d.toFixed(4)}`);
  }
  lines.push(`file '${frames[frames.length - 1].f.replace(/\\/g, '/')}'`);
  const list = path.join(tmp, 'list.txt');
  fs.writeFileSync(list, lines.join('\n'));
  const total = tEnd - frames[0].t;
  const vf = [`fps=${FPS}`, `scale=${W}:${H}:flags=lanczos`, 'setsar=1', 'format=yuv420p'];
  if (fadeIn) vf.push(`fade=t=in:st=0:d=${fadeIn}:color=white`);
  if (fadeOut) vf.push(`fade=t=out:st=${Math.max(0, total - fadeOut).toFixed(2)}:d=${fadeOut}:color=white`);
  fs.mkdirSync(path.dirname(outFile), {recursive: true});
  const r = spawnSync(ffmpeg, ['-y', '-hide_banner', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', list,
    '-vf', vf.join(','), '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-r', String(FPS),
    '-movflags', '+faststart', outFile], {stdio: 'inherit'});
  fs.rmSync(tmp, {recursive: true, force: true});
  if (r.status !== 0) throw new Error('ffmpeg 실패: ' + outFile);
  console.log(`  저장 ${path.basename(outFile)} (${total.toFixed(1)}초, 프레임 ${frames.length})`);
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

module.exports = {record, sleep, W, H, FPS};
