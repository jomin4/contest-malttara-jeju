"""말따라 제주 실행: 서버를 켜고 브라우저를 연다. 표준 라이브러리만 쓴다.

사용:
  python run.py            실제 데이터(data/db/malttara.sqlite)
  python run.py --mock     모의 데이터(원본·DB 없이 화면 개발·시연)
  python run.py --port 9000 --no-browser
"""
import argparse
import os
import sys
import tempfile
import webbrowser

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from malttara.config import load_config, load_env  # noqa: E402
from malttara.server.app import make_server  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="말따라 제주 서버")
    ap.add_argument("--mock", action="store_true", help="모의 데이터로 실행")
    ap.add_argument("--port", type=int, default=None)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args(argv)

    settings = load_config("settings")
    host = settings["server"]["host"]
    port = args.port or settings["server"]["port"]
    env = load_env(os.path.join(ROOT, ".env"))

    if args.mock:
        from malttara.etl.mock_data import build_mock_db, build_mock_map
        d = tempfile.mkdtemp(prefix="malttara-mock-")
        db_path, map_path = os.path.join(d, "mock.sqlite"), os.path.join(d, "map.json")
        build_mock_db(db_path)
        build_mock_map(map_path)
        print("[모의 데이터] 장소·지도·통계는 실제가 아닌 개발용 값입니다.")
    else:
        db_path = os.path.join(ROOT, "data", "db", "malttara.sqlite")
        map_path = os.path.join(ROOT, "data", "db", "map.json")
        if not os.path.exists(db_path):
            print("데이터 파일이 없습니다: data/db/malttara.sqlite")
            print("제출본에는 함께 들어 있습니다. 개발 중이라면 'python run.py --mock'으로 실행하거나 build_db를 실행하세요.")
            return 1

    try:
        srv = make_server(db_path, map_path, os.path.join(ROOT, "web", "dist"), host, port, env)
    except OSError:
        print(f"포트 {port}를 쓸 수 없습니다(이미 실행 중일 수 있습니다). 'python run.py --port 9000'처럼 다른 포트로 실행해 보세요.")
        return 1
    url = f"http://{host}:{port}/"
    llm = "AI 연결됨" if srv.ctx.llm.available else "AI 키 없음 → 규칙 기반으로 동작"
    print(f"말따라 제주 실행 중: {url}  ({llm})")
    print("끝내려면 이 창에서 Ctrl+C를 누르세요.")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
