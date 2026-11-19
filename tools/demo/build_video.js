// segments/*.mp4를 파일 이름 순서로 이어 최종 데모 영상을 만든다.
const fs = require('fs');
const path = require('path');
const {spawnSync} = require('child_process');
const ffmpeg = require('ffmpeg-static');

const DIR = path.resolve(__dirname, '../../submission/demo');
const SEG = path.join(DIR, 'segments');
const OUT = path.join(DIR, '말따라제주_데모영상.mp4');

const files = fs.readdirSync(SEG).filter(f => /^\d\d_.*\.mp4$/.test(f)).sort();
if (!files.length) { console.error('segments가 비어 있습니다. npm run scenes / npm run app 먼저'); process.exit(1); }
// 구간마다 시간 기준이 달라 단순 복사로 이으면 틈이 생긴다 → concat 필터로 한 번에 다시 인코딩(무음 영상).
const inputs = files.flatMap(f => ['-i', path.join(SEG, f)]);
const filter = files.map((_, i) => `[${i}:v]setpts=PTS-STARTPTS,fps=30,setsar=1,format=yuv420p[v${i}]`).join(';') + ';' +
  files.map((_, i) => `[v${i}]`).join('') + `concat=n=${files.length}:v=1:a=0[out]`;
const r = spawnSync(ffmpeg, ['-y', '-hide_banner', '-loglevel', 'error', ...inputs, '-filter_complex', filter,
  '-map', '[out]', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-r', '30', '-movflags', '+faststart', OUT],
  {stdio: 'inherit'});
if (r.status !== 0) process.exit(r.status);
const probe = spawnSync(ffmpeg, ['-hide_banner', '-i', OUT], {encoding: 'utf8'});
const dur = (probe.stderr.match(/Duration: ([\d:.]+)/) || [])[1];
console.log(`완성: ${OUT}\n구간 ${files.length}개 · 길이 ${dur} · ${(fs.statSync(OUT).size / 1048576).toFixed(1)} MB`);
console.log(files.join('\n'));
