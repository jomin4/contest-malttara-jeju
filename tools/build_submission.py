"""최종 결과물 ZIP 만들기 (개발용 도구, 표준 라이브러리만).

    python tools/build_submission.py            # 평가용 .env(LLM 키만) 포함
    python tools/build_submission.py --no-key   # 키 칸을 비운 .env

하는 일
 1. web/build.py로 화면 빌드 → 필요한 파일만 골라 submission/stage/말따라제주/ 에 모은다
 2. DB는 사본에서 실행 기록 표(batches·agent_decisions·user_interactions·llm_usage)를 비운다
 3. .env는 로컬 .env의 LLM_* 줄만 옮긴다(데이터 API 키는 넣지 않음)
 4. 데이터 API 키 값·Anthropic 키가 들어가면 안 되는 곳에 섞였는지 모든 파일을 바이트 단위로 검사한다
 5. ZIP으로 묶고, 공백·한글이 있는 임시 폴더에 풀어 표준 라이브러리만으로 서버 실행·API·테스트를 확인한다
사전 준비: submission/proposal/의 기획서·결과설명자료 PDF(docs/02_proposal/build_pdf.py), submission/demo/의 시연 영상.
"""
import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUB = ROOT / "submission"
NAME = "말따라제주"
STAGE = SUB / "stage" / NAME
ZIP = SUB / f"{NAME}_결과물.zip"

FILES = ["run.bat", "run.py", ".env.example", "requirements.txt", "requirements-etl.txt"]
TREES = ["src", "config", "tests", "web/dist", "data/mapping", "docs/05_submission/img"]
DOCS = ["manual_run.md", "manual_user.md", "data_spec.md", "README.md", "security.md", "cost.md",
        "pc_check.md", "principles_check.md", "result_overview.md"]
EXTRA = {  # 결과 설명 md가 참조하는 이미지
    "docs/assets": [f"0{i}_{n}.jpg" for i, n in enumerate(
        ["input", "route", "evidence", "selfcheck", "preview3d", "redesign", "qr", "picks", "guard"], start=1)],
    "docs/02_proposal/img": ["fig_architecture.svg", "fig_security_gate.svg", "fig_security_layers.svg"],
}
OUTPUTS = {  # 빌드 산출물 → ZIP 안 위치
    SUB / "proposal" / f"{NAME}_기획서.pdf": "기획서/말따라제주_기획서.pdf",
    SUB / "proposal" / f"{NAME}_결과설명자료.pdf": "결과설명자료/말따라제주_결과설명자료.pdf",
    SUB / "demo" / f"{NAME}_데모영상.mp4": "결과설명자료/말따라제주_데모영상.mp4",
}
SKIP = {"__pycache__", ".pytest_cache"}
RUNTIME_TABLES = ["batches", "agent_decisions", "user_interactions", "llm_usage"]


def read_env(path: Path) -> dict:
    out = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            s = line.strip()
            if s and not s.startswith("#") and "=" in s:
                k, v = s.split("=", 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def copy_tree(rel: str):
    src, dst = ROOT / rel, STAGE / rel
    for p in src.rglob("*"):
        if p.is_dir() or any(part in SKIP for part in p.parts) or p.suffix == ".pyc":
            continue
        t = dst / p.relative_to(src)
        t.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, t)


def stage(with_key: bool) -> dict:
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)
    subprocess.run([sys.executable, str(ROOT / "web" / "build.py")], check=True, cwd=ROOT, capture_output=True)
    for f in FILES:
        shutil.copy2(ROOT / f, STAGE / f)
    for t in TREES:
        copy_tree(t)
    (STAGE / "docs/05_submission").mkdir(parents=True, exist_ok=True)
    for d in DOCS:
        shutil.copy2(ROOT / "docs/05_submission" / d, STAGE / "docs/05_submission" / d)
    for folder, names in EXTRA.items():
        (STAGE / folder).mkdir(parents=True, exist_ok=True)
        for n in names:
            shutil.copy2(ROOT / folder / n, STAGE / folder / n)
    shutil.copy2(ROOT / "docs/05_submission/zip_README.md", STAGE / "README.md")
    missing = [str(s) for s in OUTPUTS if not s.exists()]
    if missing:
        sys.exit("빠진 산출물: " + ", ".join(missing))
    for s, rel in OUTPUTS.items():
        (STAGE / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(s, STAGE / rel)

    # DB: 실행 기록을 비운 사본
    db = STAGE / "data/db/malttara.sqlite"
    db.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "data/db/malttara.sqlite", db)
    shutil.copy2(ROOT / "data/db/map.json", STAGE / "data/db/map.json")
    con = sqlite3.connect(db)
    for t in RUNTIME_TABLES:
        if con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone():
            con.execute(f"DELETE FROM {t}")
    con.commit()
    con.execute("VACUUM")
    info = {"data_version": con.execute("SELECT value FROM meta WHERE key='data_version'").fetchone()[0],
            "places_in_scope": con.execute("SELECT COUNT(*) FROM places WHERE in_scope=1").fetchone()[0]}
    con.close()

    # .env: LLM 줄만
    env = read_env(ROOT / ".env")
    lines = ["# 말따라 제주 평가용 환경변수",
             "# 평가용 외부 AI API 키(Claude, 사용 한도 설정·평가 종료 후 폐기). 비우면 규칙 모드로 동작합니다.",
             "# 제주데이터허브·공공데이터포털 등 데이터 API 키는 넣지 않았습니다(실행에 불필요)."]
    for k in ("LLM_API_KEY", "LLM_PROVIDER", "LLM_BASE_URL", "LLM_MODEL"):
        v = env.get(k, "")
        if k == "LLM_API_KEY" and not with_key:
            v = ""
        lines.append(f"{k}={v}")
    (STAGE / ".env").write_text("\n".join(lines) + "\n", encoding="utf-8")
    info["llm_key_included"] = bool(with_key and env.get("LLM_API_KEY"))
    return info


def scan(env: dict):
    """데이터 API 키 값은 어디에도, Anthropic 키는 .env 밖에 있으면 안 된다."""
    forbidden = {k: v for k, v in env.items() if not k.startswith("LLM_") and len(v) >= 8}
    llm_key = env.get("LLM_API_KEY", "")
    problems = []
    for p in STAGE.rglob("*"):
        if p.is_dir():
            continue
        data = p.read_bytes()
        for k, v in forbidden.items():
            if v.encode() in data:
                problems.append(f"{p.relative_to(STAGE)}: {k} 값 포함")
        if p.name != ".env":   # 테스트의 가짜 키(sk-ant-x)는 허용, 실제 길이의 키 형태·실제 키 값은 금지
            if re.search(rb"sk-ant-[A-Za-z0-9_\-]{20,}", data) or (len(llm_key) >= 8 and llm_key.encode() in data):
                problems.append(f"{p.relative_to(STAGE)}: Anthropic 키 형태 포함")
    for name in (".git", "node_modules", "raw"):
        if any(name in q.parts for q in STAGE.rglob("*")):
            problems.append(f"제외 대상 폴더 포함: {name}")
    if problems:
        sys.exit("키 검사 실패:\n  " + "\n  ".join(problems))


def make_zip() -> int:
    ZIP.unlink(missing_ok=True)
    n = 0
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(STAGE.rglob("*")):
            if p.is_file():
                comp = zipfile.ZIP_STORED if p.suffix in (".mp4", ".jpg", ".png", ".woff2", ".pdf") else zipfile.ZIP_DEFLATED
                z.write(p, Path(NAME) / p.relative_to(STAGE), compress_type=comp)
                n += 1
    return n


def smoke() -> list:
    """공백·한글 경로에 풀어 '표준 라이브러리만'(-S -I)으로 실행 확인."""
    tmp = Path(tempfile.mkdtemp(prefix="malttara 제출 확인 "))
    with zipfile.ZipFile(ZIP) as z:
        z.extractall(tmp)
    app = tmp / NAME
    port = 8799
    log = []
    proc = subprocess.Popen([sys.executable, "-S", "-I", "run.py", "--no-browser", "--port", str(port)],
                            cwd=app, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        base = f"http://127.0.0.1:{port}"
        for _ in range(60):
            try:
                h = json.loads(urllib.request.urlopen(base + "/api/health", timeout=2).read())
                break
            except Exception:
                time.sleep(0.5)
        else:
            raise RuntimeError("서버가 뜨지 않았습니다")
        log.append(f"health: {h}")
        page = urllib.request.urlopen(base + "/", timeout=5).read()
        log.append(f"index.html: {len(page)} bytes")
        req = urllib.request.Request(base + "/api/goal/parse", method="POST",
                                     data=json.dumps({"text": "2박 3일 바다 여유롭게"}).encode(),
                                     headers={"Content-Type": "application/json"})
        g = json.loads(urllib.request.urlopen(req, timeout=60).read())
        log.append(f"parse: days={g['goal']['days']} actor={g['actor']}")
    finally:
        proc.terminate()
        proc.wait(timeout=10)
    t = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=app,
                       env={**os.environ, "PYTHONPATH": "src", "PYTHONIOENCODING": "utf-8"},
                       capture_output=True, text=True, encoding="utf-8", timeout=300)
    tail = (t.stderr or t.stdout).strip().splitlines()[-3:]
    log.append("tests: " + " | ".join(tail))
    shutil.rmtree(tmp, ignore_errors=True)
    if t.returncode != 0:
        raise RuntimeError("압축 푼 폴더에서 테스트 실패: " + " | ".join(tail))
    return log


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-key", action="store_true", help=".env의 LLM_API_KEY를 비운다")
    ap.add_argument("--no-smoke", action="store_true")
    a = ap.parse_args()
    info = stage(with_key=not a.no_key)
    scan(read_env(ROOT / ".env"))
    n = make_zip()
    print(f"ZIP: {ZIP}  ({ZIP.stat().st_size / 1048576:.1f} MB, 파일 {n}개)")
    print(f"DB data_version={info['data_version']} 추천 대상 {info['places_in_scope']}곳 · 평가용 키 포함={info['llm_key_included']}")
    print("키 검사: 통과 (데이터 API 키 없음, Anthropic 키는 .env에만)")
    if not a.no_smoke:
        for line in smoke():
            print("확인 " + line)


if __name__ == "__main__":
    main()
