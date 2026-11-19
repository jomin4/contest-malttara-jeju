"""기획서 PDF 만들기 (개발용 도구, 실행·제출 동작과 무관).

proposal.md → HTML(초안 v0.9 PDF와 같은 스타일) → Chrome 헤드리스 인쇄(A4) → submission/proposal/

    python docs/02_proposal/build_pdf.py            # 필요: pip install markdown, Chrome 설치

글꼴은 Noto Sans KR(없으면 Noto Sans CJK KR·맑은 고딕), 코드 글꼴은 DejaVu Sans Mono 계열.
"""
import os
import pathlib
import shutil
import subprocess
import sys

import markdown

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT_DIR = ROOT / "submission" / "proposal"

CSS = """
@page { size: A4; margin: 20mm 17.2mm 18mm 17.2mm; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { font-family: "Noto Sans KR", "Noto Sans CJK KR", "Malgun Gothic", sans-serif;
       font-size: 10pt; line-height: 1.55; color: #111; margin: 0; word-break: keep-all; overflow-wrap: break-word; }
h1 { font-size: 19pt; font-weight: 700; line-height: 1.35; margin: 0 0 10pt; }
h2 { font-size: 14pt; font-weight: 700; margin: 20pt 0 9pt; padding-bottom: 4pt; border-bottom: 2px solid #0f766e;
     break-after: avoid; }
h3 { font-size: 11.5pt; font-weight: 700; margin: 14pt 0 6pt; break-after: avoid; }
p { margin: 0 0 7pt; }
blockquote { margin: 0 0 9pt; padding: 0 0 0 9pt; border-left: 3px solid #ccc; color: #555; font-size: 9pt; }
blockquote p { margin: 0; }
hr { border: 0; border-top: 1px solid #ddd; margin: 12pt 0; }
ul, ol { margin: 0 0 7pt; padding-left: 20pt; }
li { margin: 0 0 2pt; }
code { font-family: "DejaVu Sans Mono", Consolas, "Noto Sans KR", monospace; font-size: 0.88em; }
pre { font-family: "DejaVu Sans Mono", Consolas, "Noto Sans KR", monospace; font-size: 8.8pt; line-height: 1.45; margin: 0 0 7pt;
      white-space: pre-wrap; break-inside: avoid; }
pre code { font-size: inherit; }
table { width: 100%; border-collapse: collapse; font-size: 8.8pt; line-height: 1.45; margin: 0 0 9pt;
        break-inside: avoid; }
th, td { border: 1px solid #bbb; padding: 3pt 5pt; vertical-align: top; text-align: left; }
th { background: #eef6f4; font-weight: 700; text-align: center; }
img { display: block; max-width: 100%; max-height: 425pt; margin: 4pt auto 3pt; break-inside: avoid; }
p:has(> img) { break-inside: avoid; break-after: avoid; margin-bottom: 2pt; }
p:has(> em:only-child) { font-size: 8.8pt; color: #555; }
"""


def find_chrome() -> str:
    for c in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              shutil.which("chrome"), shutil.which("google-chrome"), shutil.which("chromium")):
        if c and os.path.exists(c):
            return c
    sys.exit("Chrome/Edge를 찾지 못했습니다")


def build(src=HERE / "proposal.md", name="말따라제주_기획서") -> pathlib.Path:
    body = markdown.markdown(src.read_text(encoding="utf-8"), extensions=["tables", "fenced_code", "sane_lists"])
    html = (f"<!doctype html><html lang='ko'><head><meta charset='utf-8'><base href='{HERE.as_uri()}/'>"
            f"<title>{name}</title><style>{CSS}</style></head><body>{body}</body></html>")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    html_path, pdf_path = OUT_DIR / f"{name}.html", OUT_DIR / f"{name}.pdf"
    html_path.write_text(html, encoding="utf-8")
    prof = OUT_DIR / ".chrome-profile"
    subprocess.run([find_chrome(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--user-data-dir={prof}", f"--print-to-pdf={pdf_path}", html_path.as_uri()],
                   check=True, capture_output=True, timeout=120)
    shutil.rmtree(prof, ignore_errors=True)
    return pdf_path


if __name__ == "__main__":
    print(build())
