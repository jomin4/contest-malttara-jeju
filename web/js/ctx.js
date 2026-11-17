// 서버에서 한 번 받는 데이터(설정·지도·통계)와 캐시
export const ctx = {
  health: null,
  config: null,
  map: null,
  stats: {},     // month(0=연평균) -> EmdStats
  monthly: null, // month=all 응답 {period, source_id, months: {"1": items, …}}
  trends: {},    // place_id -> Trend
  bootError: null,
};
