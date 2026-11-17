// 표시용 문구. 수치는 서버 값을 반올림만 한다.
export const distanceLabel = (km) => `직선 ${Number(km).toFixed(1)} km`;
export const DIST_NOTE = "도로거리·이동시간 아님";

export function periodLabel(goal) {
  if (!goal || goal.days == null) return null;
  if (goal.days === 1) return "당일치기";
  return `${goal.nights ?? goal.days - 1}박 ${goal.days}일`;
}

export const ACTOR = { llm: "AI", rule: "규칙", code: "코드" };
export const STATUS_SYM = { ok: "✓", fail: "✗", fix: "↻", add: "+", skip: "−" };
export const CHANGE = { keep: "유지", pin: "고정", replace: "교체", add: "추가", remove: "제외" };
export const REACT = { interest: "좋아요", must: "꼭 갈래요", dislike: "별로예요" };
// 버튼 아래 작은 설명 (무엇이 바뀌는지)
export const REACT_HINT = { interest: "비슷한 곳 더", must: "일정에 고정", dislike: "다른 곳으로" };

export function violationText(v, places) {
  const nm = (id) => (places && places[id] ? places[id].name : id);
  switch (v.type) {
    case "distance": return `${v.day}일차 직선 합계 ${v.value} km가 기준 ${v.limit} km를 넘습니다`;
    case "regions": return `${v.day}일차에 권역 ${v.value}곳 방문(기준 ${v.limit})`;
    case "count": return `${v.day}일차 장소 ${v.value}곳(목표 ${v.limit}곳) — 조건에 맞는 장소가 부족합니다`;
    case "origin": return `${v.day}일차 첫 장소가 출발지에서 직선 ${v.value} km(기준 ${v.limit} km)`;
    case "duplicate": return `${v.day}일차 ${nm(v.place_id)}이(가) 중복됩니다`;
    case "out_of_scope": return `${v.day}일차 ${nm(v.place_id)}은(는) 범위 밖 장소입니다`;
    default: return `${v.day}일차 ${v.type}`;
  }
}

// 타이핑 비교: 공백 제거 + NFC
export const normalizeTyping = (t) => (t || "").normalize("NFC").replace(/\s+/g, "");

export const pct100 = (p) => (p == null ? null : Math.round(p * 100));

// 실행 로그의 Tool 이름 → 방문객용 한국어
export const TOOL_KO = {
  plan_tasks: "작업 계획", search_places: "장소 찾기", get_region_data: "지역 지표 비교", analyze_tourism: "입장객 추이 확인",
  check_data_quality: "데이터 품질 점검", create_itinerary: "일정 만들기", calculate_route: "거리 계산", validate_itinerary: "일정 검증",
  revise_itinerary: "일정 고치기", inject_error: "오류 주입(시연)", explain_decisions: "설명 정리", save_agent_state: "기록 저장",
  analyze_feedback: "반응 분석", decide_keep_replace: "유지·교체 판단", compare_itineraries: "전후 비교", parse_travel_goal: "조건 읽기",
};
// 진행 단계 (로그 tool → 단계 번호)
export const STAGES_A = ["계획", "장소 찾기", "일정 짜기", "검증·수정", "완료"];
export const STAGES_B = ["반응 분석", "유지·교체", "다시 짜기", "검증", "완료"];
const STAGE_OF = {
  plan_tasks: 0, search_places: 1, get_region_data: 1, analyze_tourism: 1, check_data_quality: 1,
  create_itinerary: 2, calculate_route: 2, inject_error: 3, validate_itinerary: 3, revise_itinerary: 3, explain_decisions: 4, save_agent_state: 4,
  analyze_feedback: 0, decide_keep_replace: 1, compare_itineraries: 3,
};
export function stageOf(kind, events, done) {
  if (done) return 4;
  if (!events?.length) return 0;
  const t = events[events.length - 1].tool;
  if (kind === "B" && (t === "search_places" || t === "calculate_route")) return 2;
  if (kind === "B" && t === "validate_itinerary") return 3;
  return Math.min(3, STAGE_OF[t] ?? 0);
}
