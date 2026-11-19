"""OpenAI 호환 LLM 클라이언트(urllib). 실패하면 None을 돌려주고 호출부가 규칙으로 넘어간다.

- 배포: Upstage Solar Pro 4 (json_mode="schema", response_format=json_schema)
- 개발: K-EXAONE 2.5 (json_mode="prompt": response_format 없이 프롬프트로 JSON 지시, 본문에서 JSON 추출)
키는 로그에 남기지 않는다.
"""
import json
import threading
import time
import urllib.error
import urllib.request
from collections import deque

from malttara.agent.guard import SECURITY, SYSTEM_GUARD, clean_text, detect_injection, wrap_user
from malttara.agent.schema_lite import check_schema


def _default_transport(url: str, headers: dict, body: bytes, timeout: float) -> bytes:
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _skeleton(schema: dict):
    """스키마에서 '채워 넣을 모양' 예시를 만든다(모델이 스키마 자체를 다시 출력하는 것을 막는다)."""
    t = schema.get("type")
    t = t[0] if isinstance(t, list) else t
    if "enum" in schema:
        return schema["enum"][0]
    if t == "object":
        return {k: _skeleton(v) for k, v in schema.get("properties", {}).items()}
    if t == "array":
        return [_skeleton(schema["items"])] if schema.get("items") else []
    return {"string": "…", "integer": 0, "number": 0, "boolean": False, "null": None}.get(t, "…")


def _extract_json(text: str):
    if not isinstance(text, str):
        return None
    s, e = text.find("{"), text.rfind("}")
    if s < 0 or e <= s:
        return None
    try:
        return json.loads(text[s:e + 1])
    except ValueError:
        return None


class LLMClient:
    def __init__(self, api_key, base_url, model, timeout_s: float, transport=None,
                 json_mode: str = "schema", extra_body=None, max_calls_per_min=None):
        self.api_key = api_key
        self.base_url = (base_url or "").rstrip("/")
        self.model = model
        self.timeout_s = timeout_s
        self.transport = transport or _default_transport
        self.json_mode = json_mode if json_mode in ("schema", "prompt") else "schema"
        self.extra_body = dict(extra_body or {})
        self.max_calls_per_min = max_calls_per_min
        self._calls = deque()                # 최근 60초 안의 실제 HTTP 호출 시각
        self._lock = threading.Lock()
        self._local = threading.local()      # 배치마다 스레드가 달라 상태를 섞지 않는다

    @property
    def available(self) -> bool:
        return bool(self.api_key and self.base_url and self.model)

    @property
    def last_status(self) -> str:
        """ok · invalid · error · unavailable · injection_suspected · rate_limited"""
        return getattr(self._local, "status", "ok")

    def _set(self, status: str):
        self._local.status = status

    def _take_slot(self) -> bool:
        if not self.max_calls_per_min:
            return True
        now = time.monotonic()
        with self._lock:
            while self._calls and now - self._calls[0] >= 60:
                self._calls.popleft()
            if len(self._calls) >= self.max_calls_per_min:
                return False
            self._calls.append(now)
            return True

    def _post(self, messages: list, schema: dict, mode: str):
        body = {"model": self.model, "messages": messages, "temperature": 0}
        if mode == "schema":
            body["response_format"] = {"type": "json_schema",
                                       "json_schema": {"name": "out", "schema": schema, "strict": True}}
        body.update(self.extra_body)
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        raw = self.transport(f"{self.base_url}/chat/completions", headers,
                             json.dumps(body, ensure_ascii=False).encode("utf-8"), self.timeout_s)
        data = json.loads(raw)
        return data["choices"][0]["message"].get("content")

    def chat_json(self, system: str, user: str, schema: dict):
        if not self.available:
            self._set("unavailable")
            return None
        user = clean_text(user)
        if detect_injection(user):           # 의심 입력은 외부로 보내지 않고 규칙으로 넘긴다
            self._set("injection_suspected")
            return None
        system = system + SYSTEM_GUARD
        user = wrap_user(user)
        modes = [self.json_mode] if self.json_mode == "prompt" else ["schema", "prompt"]
        for mode in modes:
            if not self._take_slot():
                self._set("rate_limited")
                return None
            sys_msg = system
            if mode == "prompt":
                sys_msg = (system + "\n\n출력 규칙: 아래 '모양'과 같은 키를 가진 JSON 객체 하나만 출력하라. "
                           "값을 실제 내용으로 채우고, 스키마나 설명·코드블록은 출력하지 않는다.\n모양: "
                           + json.dumps(_skeleton(schema), ensure_ascii=False)
                           + "\n허용 값 규칙: " + json.dumps(schema, ensure_ascii=False))
            try:
                content = self._post([{"role": "system", "content": sys_msg},
                                      {"role": "user", "content": user}], schema, mode)
            except urllib.error.HTTPError as e:
                if mode == "schema" and e.code == 400:
                    continue                    # response_format 미지원 → 프롬프트 방식으로 한 번 더
                self._set("error")
                return None
            except Exception:
                self._set("error")
                return None
            out = _extract_json(content)
            ok = out is not None and check_schema(out, schema)
            self._set("ok" if ok else "invalid")
            return out if ok else None
        self._set("error")
        return None


def client_from_env(env: dict, settings: dict) -> LLMClient:
    try:
        extra = json.loads(env.get("LLM_EXTRA_BODY") or "{}")
    except ValueError:
        extra = {}
    try:                                         # 개발용 느린 모델 확인 때만 .env에서 늘린다
        timeout = float(env.get("LLM_TIMEOUT_S") or settings["llm"]["timeout_s"])
    except ValueError:
        timeout = settings["llm"]["timeout_s"]
    return LLMClient(env.get("LLM_API_KEY") or None, env.get("LLM_BASE_URL") or None,
                     env.get("LLM_MODEL") or None, timeout,
                     json_mode=env.get("LLM_JSON_MODE") or "schema",
                     extra_body=extra if isinstance(extra, dict) else {},
                     max_calls_per_min=SECURITY.get("llm_max_calls_per_min"))
