# 01 기획 다듬기

기획 초안(v0)을 실제 데이터와 UI에 맞춰 다듬는 단계의 작업 폴더.
최종 산출물은 superpowers brainstorming이 만드는 설계 문서 `docs/superpowers/specs/YYYY-MM-DD-malttara-jeju-design.md`이고, 이 폴더의 문서는 그 근거와 작업 기록이다.

| 파일 | 용도 | 수정 |
|---|---|---|
| `기획문서_v0.md` | 다른 세션에서 만든 기획 초안 원본 (366줄, 대회 기획서 양식 순서) | **수정 금지**. 바뀐 내용은 decisions.md와 설계 문서에 |
| `decisions.md` | D1~D8 결정과 변경 이력 | 결정할 때마다 추가 |
| `open-questions.md` | 미결 사항·리스크·기획 빈틈 | 해결하면 체크하고 결과 위치를 적음 |
| `data-selection.md` | D3(필수 데이터)·D4(공간 범위) 작업장. 후보 데이터의 카드 ID와 확인 항목 | 원본 확인 결과를 채움 |
| `review-checklist.md` | 대회 기획서 필수 항목·배점 기준으로 빈틈 점검 | 설계 문서 승인 전 한 번, 제출 전 한 번 |

## 권장 순서 (11/16 밤까지)

1. **D3·D4 결정** — `data-selection.md` 후보 중 원본을 받아 확인(좌표, 기간, 공간 단위, 장소명 매칭 가능성) → 결정 → decisions.md
2. **기획-UI 불일치 해소** — `design/ui-prototype/README.md`의 "기획과 어긋나는 부분"을 하나씩 결정(UI를 고칠지, 기획을 바꿀지)
3. **기획 빈틈 메우기** — `open-questions.md`의 "기획 빈틈" 항목
4. **review-checklist.md 점검** 후 설계 문서 작성 → 사용자 승인 → writing-plans

## brainstorming에 줄 맥락

- 기획문서_v0의 결정 D1·D2·D5~D8은 확정. 다시 열지 말고, 데이터나 UI 때문에 바꿔야 할 때만 이유와 함께 제안한다.
- 질문은 한 번에 하나. 선택지는 2~3개로 주고 추천안을 표시한다.
- 데이터 이야기는 카드 ID(`data/cards/{ID:04d}_*.md`)로 근거를 단다.
