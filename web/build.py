"""프론트 '빌드': 실행에 필요한 파일만 web/dist 로 복사한다 (Python 표준 라이브러리, Node 불필요).

서버(run.py)는 계약대로 web/dist 를 서빙한다. 목업(mock/)·개발 도구(tools/)·문서는 넣지 않는다.

사용:  python web/build.py
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(HERE, "dist")
INCLUDE = ["index.html", "css", "js", "fonts"]


def build() -> int:
    if os.path.isdir(DIST):
        try:
            shutil.rmtree(DIST)
        except OSError as e:  # 지울 권한이 없으면 덮어쓰기로 진행
            print(f"web/dist 를 비우지 못해 덮어씁니다 ({e.__class__.__name__})")
    os.makedirs(DIST, exist_ok=True)
    n = 0
    for name in INCLUDE:
        src = os.path.join(HERE, name)
        dst = os.path.join(DIST, name)
        if os.path.isdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)
            n += sum(len(f) for _, _, f in os.walk(dst))
        else:
            shutil.copy2(src, dst)
            n += 1
    # 외부 주소가 섞이지 않았는지 점검 (SVG 네임스페이스 제외)
    bad = []
    for root, _, files in os.walk(DIST):
        for f in files:
            if f.endswith((".html", ".css", ".js")):
                text = open(os.path.join(root, f), encoding="utf-8").read()
                for token in ("http://", "https://"):
                    i = text.find(token)
                    while i != -1:
                        if not text.startswith("http://www.w3.org/2000/svg", i):
                            bad.append(f"{f}: {text[i:i + 60]}")
                        i = text.find(token, i + 1)
    print(f"web/dist 생성: 파일 {n}개")
    if bad:
        print("외부 주소가 있습니다(오프라인에서 깨질 수 있음):")
        for b in bad:
            print("  ", b)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(build())
