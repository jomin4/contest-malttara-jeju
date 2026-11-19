# 데모 영상 제작 도구 (공모 제출용)

개발용 도구다. 실행·제출 동작과 무관하며 결과 영상만 `submission/demo/`에 만든다(git 제외).

## 구성
| 파일 | 하는 일 |
|---|---|
| `lib/recorder.js` | Chrome 화면 스트림(CDP screencast, 고화질 JPEG) → ffmpeg-static으로 H.264 MP4. Playwright 기본 녹화(VP8 1Mbps)보다 글자가 선명하다 |
| `scenes/scenes.html` | 모션 그래픽 장면 7개(타이틀·문제·아키텍처·보안 관문·방어의 세 겹·비용·아웃트로). 기획서 도식 SVG를 그대로 쓴다 |
| `render_scenes.js` | 장면 녹화 → `segments/00~02, 20~23` |
| `record_app.js` | **실제 앱**을 자동 조작해 녹화 → `segments/10~14`. 자막과 '실제 실행 화면' 표시만 덧씌우고 앱 동작은 바꾸지 않는다 |
| `build_video.js` | 구간을 파일 이름 순서로 이어 `말따라제주_데모영상.mp4` |

## 만들기
```
cd tools/demo
npm install                       # playwright, ffmpeg-static (설치된 Chrome 사용, 브라우저 다운로드 없음)
# Playwright 녹화용 ffmpeg가 없으면: node_modules/ffmpeg-static/ffmpeg.exe 를
#   %LOCALAPPDATA%/ms-playwright/ffmpeg-1011/ffmpeg-win64.exe 로 복사(현재 녹화기는 쓰지 않음)
python ../../run.py --no-browser   # 다른 터미널에서 서버(127.0.0.1:8765), .env에 Claude 키
npm run scenes                     # 모션 그래픽 (약 1분 30초)
npm run app                        # 실제 앱 녹화 (약 2분, Claude API 호출 수 회 · 1원 미만)
npm run build                      # 합치기
```
장면 하나만 다시: `node render_scenes.js gate`

## 주의
- 영상의 화면 수치는 그때 DB 기준이다. **최종 DB(Release)를 넣은 뒤 `npm run app`과 `npm run build`를 다시 돌린다.**
- 화면에 키·`.env`·터미널이 나오지 않는다(브라우저 페이지만 녹화).
- 무음 영상이며 설명은 화면 자막으로 넣었다.
