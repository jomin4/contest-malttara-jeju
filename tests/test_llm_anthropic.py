"""Anthropic Messages API 연결(표준 라이브러리 urllib)과 토큰 사용량·비용 기록."""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from helpers import S, mock_conn
from malttara.agent.decide import decide
from malttara.agent.llm import LLMClient, client_from_env
from malttara.agent.usage import record_usage, usage_summary

SCHEMA = {"type": "object", "properties": {"type": {"enum": ["replace", "reorder", "remove"]},
                                           "day": {"type": "integer", "minimum": 1, "maximum": 7}},
          "required": ["type"], "additionalProperties": False}
FREE_KEYS = {"type": "object", "required": ["evidence"], "properties": {
    "evidence": {"type": "object", "additionalProperties": {"type": "string"}}}}


def anth(seen, out, usage=(120, 30), stop="end_turn"):
    def tr(url, headers, body, timeout):
        seen.append({"url": url, "headers": headers, "body": json.loads(body)})
        return json.dumps({"type": "message", "model": "claude-haiku-5-5", "stop_reason": stop,
                           "content": [{"type": "text", "text": json.dumps(out)}],
                           "usage": {"input_tokens": usage[0], "output_tokens": usage[1]}}).encode()
    return tr


def client(seen, out, **kw):
    return LLMClient("sk-ant-x", "https://api.anthropic.com", "claude-haiku-5-5", 5,
                     transport=anth(seen, out, **kw), provider="anthropic", max_tokens=1024)


class AnthropicTest(unittest.TestCase):
    def test_request_shape(self):
        seen = []
        self.assertEqual(client(seen, {"type": "remove"}).chat_json("s", "2박 3일 바다", SCHEMA), {"type": "remove"})
        r = seen[0]
        self.assertEqual(r["url"], "https://api.anthropic.com/v1/messages")
        self.assertEqual((r["headers"]["x-api-key"], r["headers"]["anthropic-version"]), ("sk-ant-x", "2026-10-21"))
        self.assertNotIn("Authorization", r["headers"])
        b = r["body"]
        self.assertEqual((b["model"], b["max_tokens"]), ("claude-haiku-5-5", 1024))
        self.assertNotIn("temperature", b)
        self.assertEqual(b["thinking"], {"type": "disabled"})
        self.assertEqual(b["output_config"]["effort"], "low")
        fmt = b["output_config"]["format"]
        self.assertEqual(fmt["type"], "json_schema")
        self.assertNotIn("minimum", json.dumps(fmt["schema"]))      # 미지원 제약은 빼고 코드가 검사
        self.assertIn("보안 규칙", b["system"])
        self.assertEqual(b["messages"], [{"role": "user", "content": "<사용자_입력>\n2박 3일 바다\n</사용자_입력>"}])

    def test_code_still_checks_removed_constraints(self):
        self.assertIsNone(client([], {"type": "remove", "day": 9}).chat_json("s", "u", SCHEMA))

    def test_free_key_schema_uses_prompt_mode(self):
        seen = []
        out = client(seen, {"evidence": {"days": "2박 3일"}}).chat_json("s", "u", FREE_KEYS)
        self.assertEqual(out, {"evidence": {"days": "2박 3일"}})
        self.assertNotIn("format", seen[0]["body"]["output_config"])
        self.assertIn("모양", seen[0]["body"]["system"])

    def test_usage_and_refusal(self):
        llm = client([], {"type": "remove"})
        llm.chat_json("s", "u", SCHEMA)
        self.assertEqual(llm.last_usage, {"model": "claude-haiku-5-5", "input_tokens": 120, "output_tokens": 30})
        refused = client([], {"type": "remove"}, stop="refusal")
        self.assertIsNone(refused.chat_json("s", "u", SCHEMA))
        self.assertEqual(refused.last_status, "invalid")

    def test_extra_body_merges_output_config(self):
        seen = []
        llm = LLMClient("k", "https://api.anthropic.com", "claude-haiku-5-5", 5, transport=anth(seen, {"type": "remove"}),
                        provider="anthropic", extra_body={"output_config": {"effort": "medium"}})
        llm.chat_json("s", "u", SCHEMA)
        oc = seen[0]["body"]["output_config"]
        self.assertEqual((oc["effort"], oc["format"]["type"]), ("medium", "json_schema"))

    def test_client_from_env(self):
        env = {"LLM_API_KEY": "sk-ant-x", "LLM_BASE_URL": "https://api.anthropic.com", "LLM_MODEL": "claude-haiku-5-5"}
        c = client_from_env(env, S)
        self.assertEqual((c.provider, c.max_tokens, c.available), ("anthropic", S["llm"]["max_tokens"], True))
        self.assertEqual(client_from_env({**env, "LLM_BASE_URL": "https://x/v1"}, S).provider, "openai")
        self.assertEqual(client_from_env({**env, "LLM_PROVIDER": "anthropic", "LLM_BASE_URL": ""}, S).base_url,
                         "https://api.anthropic.com")


class UsageTest(unittest.TestCase):
    def setUp(self):
        self.conn, _ = mock_conn()

    def tearDown(self):
        self.conn.close()

    def test_decide_records_usage_and_summary_prices_it(self):
        llm = client([], {"type": "remove"}, usage=(1_000_000, 200_000))
        decide(self.conn, "A-1", "revise", llm, "s", "u", SCHEMA, lambda o: True, lambda: {"type": "reorder"})
        s = usage_summary(self.conn, S)
        self.assertEqual((s["calls"], s["input_tokens"], s["output_tokens"]), (1, 1_000_000, 200_000))
        self.assertAlmostEqual(s["usd"], 0.10 + 0.10)            # 입력 $0.10/M + 출력 $0.50/M × 0.2M
        self.assertEqual(s["by_batch"]["A-1"]["calls"], 1)

    def test_no_usage_without_network_call(self):
        llm = LLMClient(None, None, None, 5)
        record_usage(self.conn, "A-2", "plan_tasks", llm)
        self.assertEqual(usage_summary(self.conn, S)["calls"], 0)

    def test_unknown_model_has_no_price(self):
        llm = LLMClient("k", "https://api.anthropic.com", "other-model", 5, provider="anthropic",
                        transport=anth([], {"type": "remove"}))
        llm.chat_json("s", "u", SCHEMA)
        record_usage(self.conn, "A-3", "revise", llm)
        self.assertIsNone(usage_summary(self.conn, S)["usd"])


if __name__ == "__main__":
    unittest.main()
