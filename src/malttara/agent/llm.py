"""LLM 클라이언트(표준 라이브러리 urllib만). 실패하면 None을 돌려주고 호출부가 규칙으로 넘어간다.

- provider="anthropic" (제출·평가): Claude Haiku 5.5, Anthropic Messages API `POST /v1/messages`.
  SDK는 설치하지 않는다(D17: 실행 중 표준 라이브러리만). 비용·지연을 줄이려고 생각(thinking)은 끄고
  effort low, max_tokens 상한을 둔다. 응답 형식은 output_config.format(json_schema)로 강제하되,
  지원하지 않는 스키마 규칙(최소·최대, 자유 키)은 빼거나 프롬프트 방식으로 보내고 코드가 다시 검사한다.
- provider="openai" (개발 때 쓴 OpenAI 호환 API, 예: K-EXAONE): response_format 또는 프롬프트로 JSON 지시.
키는 로그에 남기지 않는다. 응답의 토큰 사용량은 last_usage로 남겨 비용 기록(usage.py)에 쓴다.
"""
import json
import threading
import time
import urllib.error
import urllib.request
from collections import deque

from malttara.agent.guard import SECURITY, SYSTEM_GUARD, clean_text, detect_injection, wrap_user
from malttara.agent.schema_lite import check_schema

ANTHROPIC_BASE_URL = "https://api.anthropic.com"
_UNSUPPORTED = ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf",
                "minLength", "maxLength", "minItems", "maxItems", "uniqueItems")


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


def _anthropic_schema(schema):
    """Anthropic 응답 형식 강제용 스키마. 숫자·길이 제약은 빼고(코드가 검사), 객체는 additionalProperties=false.
    자유 키(additionalProperties가 스키마)처럼 표현할 수 없으면 None → 프롬프트 방식."""
    if isinstance(schema, list):
        out = [_anthropic_schema(s) for s in schema]
        return None if any(o is None for o in out) else out
    if not isinstance(schema, dict):
        return schema
    t = schema.get("type")
    is_obj = t == "object" or (isinstance(t, list) and "object" in t) or "properties" in schema
    if is_obj and schema.get("additionalProperties", False) is not False:
        return None
    out = {}
    for k, v in schema.items():
        if k in _UNSUPPORTED:
            continue
        if k in ("properties",):
            sub = {pk: _anthropic_schema(pv) for pk, pv in v.items()}
            if any(sv is None for sv in sub.values()):
                return None
            out[k] = sub
        elif k in ("items", "anyOf", "allOf"):
            sub = _anthropic_schema(v)
            if sub is None:
                return None
            out[k] = sub
        else:
            out[k] = v
    if is_obj:
        out["additionalProperties"] = False
    return out


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


def _merge(base: dict, extra: dict) -> dict:
    out = dict(base)
    for k, v in extra.items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


class LLMClient:
    def __init__(self, api_key, base_url, model, timeout_s: float, transport=None,
                 json_mode: str = "schema", extra_body=None, max_calls_per_min=None,
                 provider: str = "openai", max_tokens: int = 1024,
                 anthropic_version: str = "2026-10-21"):
        self.provider = provider if provider in ("openai", "anthropic") else "openai"
        if self.provider == "anthropic" and not base_url:
            base_url = ANTHROPIC_BASE_URL
        self.api_key = api_key
        self.base_url = (base_url or "").rstrip("/")
        self.model = model
        self.timeout_s = timeout_s
        self.transport = transport or _default_transport
        self.json_mode = json_mode if json_mode in ("schema", "prompt") else "schema"
        self.extra_body = dict(extra_body or {})
        self.max_calls_per_min = max_calls_per_min
        self.max_tokens = max_tokens
        self.anthropic_version = anthropic_version
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

    @property
    def last_usage(self):
        """이 스레드의 마지막 chat_json에서 실제로 쓴 토큰 합계 {model, input_tokens, output_tokens}, 호출이 없었으면 None."""
        return getattr(self._local, "usage", None)

    def take_usage(self):
        """last_usage를 돌려주고 비운다(같은 사용량을 두 번 기록하지 않게)."""
        u = self.last_usage
        self._local.usage = None
        return u

    def _set(self, status: str):
        self._local.status = status

    def _add_usage(self, inp, out):
        u = self._local.usage or {"model": self.model, "input_tokens": 0, "output_tokens": 0}
        u["input_tokens"] += int(inp or 0)
        u["output_tokens"] += int(out or 0)
        self._local.usage = u

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

    def _post_openai(self, system: str, user: str, schema: dict, mode: str):
        body = {"model": self.model, "temperature": 0,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        if mode == "schema":
            body["response_format"] = {"type": "json_schema",
                                       "json_schema": {"name": "out", "schema": schema, "strict": True}}
        body.update(self.extra_body)
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        raw = self.transport(f"{self.base_url}/chat/completions", headers,
                             json.dumps(body, ensure_ascii=False).encode("utf-8"), self.timeout_s)
        data = json.loads(raw)
        u = data.get("usage") or {}
        self._add_usage(u.get("prompt_tokens"), u.get("completion_tokens"))
        return data["choices"][0]["message"].get("content")

    def _post_anthropic(self, system: str, user: str, schema: dict, mode: str):
        # temperature 등 샘플링 값은 Haiku 5.5에서 400이라 보내지 않는다. 생각을 끄고 effort low로 토큰을 줄인다.
        body = {"model": self.model, "max_tokens": self.max_tokens, "system": system,
                "messages": [{"role": "user", "content": user}],
                "thinking": {"type": "disabled"}, "output_config": {"effort": "low"}}
        if mode == "schema":
            body["output_config"]["format"] = {"type": "json_schema", "schema": _anthropic_schema(schema)}
        body = _merge(body, self.extra_body)
        url = self.base_url + ("/messages" if self.base_url.endswith("/v1") else "/v1/messages")
        headers = {"x-api-key": self.api_key, "anthropic-version": self.anthropic_version,
                   "content-type": "application/json"}
        raw = self.transport(url, headers, json.dumps(body, ensure_ascii=False).encode("utf-8"), self.timeout_s)
        data = json.loads(raw)
        u = data.get("usage") or {}
        self._add_usage(u.get("input_tokens"), u.get("output_tokens"))
        if data.get("stop_reason") == "refusal":
            return None
        return "".join(b.get("text", "") for b in data.get("content") or [] if b.get("type") == "text")

    def _modes(self, schema: dict) -> list:
        if self.json_mode == "prompt":
            return ["prompt"]
        if self.provider == "anthropic" and _anthropic_schema(schema) is None:
            return ["prompt"]
        return ["schema", "prompt"]

    def chat_json(self, system: str, user: str, schema: dict):
        self._local.usage = None
        if not self.available:
            self._set("unavailable")
            return None
        user = clean_text(user)
        if detect_injection(user):           # 의심 입력은 외부로 보내지 않고 규칙으로 넘긴다
            self._set("injection_suspected")
            return None
        system = system + SYSTEM_GUARD
        user = wrap_user(user)
        post = self._post_anthropic if self.provider == "anthropic" else self._post_openai
        for mode in self._modes(schema):
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
                content = post(sys_msg, user, schema, mode)
            except urllib.error.HTTPError as e:
                if mode == "schema" and e.code == 400:
                    continue                    # 형식 강제 미지원 → 프롬프트 방식으로 한 번 더
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
    llm_cfg = settings["llm"]
    try:                                         # 느린 개발용 모델 확인 때만 .env에서 늘린다
        timeout = float(env.get("LLM_TIMEOUT_S") or llm_cfg["timeout_s"])
    except ValueError:
        timeout = llm_cfg["timeout_s"]
    base = env.get("LLM_BASE_URL") or None
    provider = env.get("LLM_PROVIDER") or ("anthropic" if base and "anthropic.com" in base else "openai")
    return LLMClient(env.get("LLM_API_KEY") or None, base, env.get("LLM_MODEL") or None, timeout,
                     json_mode=env.get("LLM_JSON_MODE") or "schema",
                     extra_body=extra if isinstance(extra, dict) else {},
                     max_calls_per_min=SECURITY.get("llm_max_calls_per_min"),
                     provider=provider, max_tokens=llm_cfg.get("max_tokens", 1024),
                     anthropic_version=llm_cfg.get("anthropic_version", "2026-10-21"))
