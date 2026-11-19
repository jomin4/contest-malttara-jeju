import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from helpers import S, mock_conn
from malttara.agent.decide import decide, polish_text
from malttara.agent.llm import LLMClient, client_from_env
from malttara.agent.schema_lite import check_schema
from malttara.tools.revise import ALLOWED_ACTIONS

SCHEMA = {"type": "object", "properties": {"type": {"enum": ["replace", "reorder", "remove"]}},
          "required": ["type"], "additionalProperties": False}


def fake(body):
    return lambda url, h, b, t: json.dumps({"choices": [{"message": {"content": json.dumps(body)}}]}).encode()


class SchemaTest(unittest.TestCase):
    def test_check_schema(self):
        s = {"type": "object", "required": ["a"], "properties": {
            "a": {"type": "integer", "minimum": 1, "maximum": 3},
            "b": {"type": "array", "items": {"type": "string"}},
            "c": {"type": ["string", "null"]}}, "additionalProperties": False}
        self.assertTrue(check_schema({"a": 2, "b": ["x"], "c": None}, s))
        self.assertFalse(check_schema({"a": 5}, s))
        self.assertFalse(check_schema({"b": []}, s))
        self.assertFalse(check_schema({"a": 1, "z": 1}, s))
        self.assertFalse(check_schema({"a": True}, s))     # bool은 integer가 아님
        self.assertFalse(check_schema({"a": 1, "b": [1]}, s))


class LLMTest(unittest.TestCase):
    def setUp(self):
        self.conn, _ = mock_conn()

    def tearDown(self):
        self.conn.close()

    def test_no_key_uses_rule_without_network(self):
        called = []
        llm = LLMClient(None, None, None, 5, transport=lambda *a: called.append(1))
        self.assertFalse(llm.available)
        out, actor = decide(self.conn, "A-x", "revise", llm, "s", "u", SCHEMA, lambda o: True, lambda: {"type": "reorder"})
        self.assertEqual((out, actor, called), ({"type": "reorder"}, "rule", []))

    def test_valid_llm_answer_is_used(self):
        llm = LLMClient("k", "http://x", "m", 5, transport=fake({"type": "remove"}))
        out, actor = decide(self.conn, "A-x", "revise", llm, "s", "u", SCHEMA, lambda o: True, lambda: {"type": "reorder"})
        self.assertEqual((out, actor), ({"type": "remove"}, "llm"))

    def test_invalid_json_or_schema_falls_back(self):
        llm = LLMClient("k", "http://x", "m", 5, transport=fake({"type": 3}))
        self.assertEqual(decide(self.conn, "A-x", "revise", llm, "s", "u", SCHEMA, lambda o: True, lambda: {"type": "reorder"})[1], "rule")
        broken = LLMClient("k", "http://x", "m", 5, transport=lambda *a: b"not json")
        self.assertIsNone(broken.chat_json("s", "u", SCHEMA))

    def test_transport_exception_falls_back(self):
        def boom(*a):
            raise OSError("offline")
        llm = LLMClient("k", "http://x", "m", 5, transport=boom)
        self.assertIsNone(llm.chat_json("s", "u", SCHEMA))

    def test_rejected_by_accept_falls_back_and_is_recorded(self):
        llm = LLMClient("k", "http://x", "m", 5, transport=fake({"type": "remove"}))
        decide(self.conn, "A-x", "revise", llm, "s", "u", SCHEMA, lambda o: o["type"] == "replace", lambda: {"type": "reorder"})
        row = self.conn.execute("select actor, reason, point from agent_decisions").fetchone()
        self.assertEqual((row["actor"], row["reason"], row["point"]), ("rule", "llm_invalid", "revise"))

    def test_request_shape_schema_mode(self):
        seen = {}

        def tr(url, headers, body, timeout):
            seen.update(url=url, headers=headers, body=json.loads(body))
            return json.dumps({"choices": [{"message": {"content": "{\"type\": \"reorder\"}"}}]}).encode()
        llm = LLMClient("secret", "http://x/v1", "m", 5, transport=tr, extra_body={"reasoning_effort": "low"})
        llm.chat_json("s", "u", SCHEMA)
        self.assertEqual(seen["url"], "http://x/v1/chat/completions")
        self.assertEqual(seen["headers"]["Authorization"], "Bearer secret")
        self.assertEqual(seen["body"]["response_format"]["type"], "json_schema")
        self.assertEqual(seen["body"]["reasoning_effort"], "low")
        self.assertEqual(seen["body"]["temperature"], 0)

    def test_prompt_json_mode_parses_json_inside_text(self):
        body = {"choices": [{"message": {"content": "결과입니다:\n{\"type\": \"reorder\"}\n끝", "reasoning_content": "..."}}]}
        seen = {}

        def tr(u, h, b, t):
            seen["body"] = json.loads(b)
            return json.dumps(body).encode()
        llm = LLMClient("k", "http://x", "m", 5, json_mode="prompt", transport=tr)
        self.assertEqual(llm.chat_json("s", "u", SCHEMA), {"type": "reorder"})
        self.assertNotIn("response_format", seen["body"])
        self.assertIn("JSON", seen["body"]["messages"][0]["content"])

    def test_schema_mode_400_retries_prompt_mode(self):
        import urllib.error
        calls = []

        def tr(u, h, b, t):
            body = json.loads(b)
            calls.append("response_format" in body)
            if "response_format" in body:
                raise urllib.error.HTTPError(u, 400, "bad", {}, None)
            return json.dumps({"choices": [{"message": {"content": "{\"type\": \"remove\"}"}}]}).encode()
        llm = LLMClient("k", "http://x", "m", 5, transport=tr)
        self.assertEqual(llm.chat_json("s", "u", SCHEMA), {"type": "remove"})
        self.assertEqual(calls, [True, False])

    def test_client_from_env(self):
        env = {"LLM_API_KEY": "k", "LLM_BASE_URL": "https://api.exaone.ai/v1", "LLM_MODEL": "k-exaone_v2.5",
               "LLM_JSON_MODE": "prompt", "LLM_EXTRA_BODY": "{\"reasoning_effort\": \"low\"}"}
        c = client_from_env(env, S)
        self.assertTrue(c.available)
        self.assertEqual((c.json_mode, c.extra_body), ("prompt", {"reasoning_effort": "low"}))
        self.assertFalse(client_from_env({}, S).available)

    def test_polish_rejects_new_numbers(self):
        llm = LLMClient("k", "http://x", "m", 5, transport=fake({"text": "만족도 99%입니다"}))
        self.assertEqual(polish_text(llm, "직선 12.1 km"), ("직선 12.1 km", "rule"))
        ok = LLMClient("k", "http://x", "m", 5, transport=fake({"text": "하루 직선 12.1 km를 이동합니다"}))
        self.assertEqual(polish_text(ok, "직선 12.1 km"), ("하루 직선 12.1 km를 이동합니다", "llm"))

    def test_allowed_actions_used_in_accept(self):
        self.assertIn("replace", ALLOWED_ACTIONS)


if __name__ == "__main__":
    unittest.main()


class PromptModeTest(unittest.TestCase):
    def test_skeleton_and_timeout_override(self):
        from malttara.agent.llm import _skeleton
        sch = {"type": "object", "properties": {"days": {"type": ["integer", "null"]}, "pace": {"enum": ["여유롭게", "보통"]},
                                                 "interests": {"type": "array", "items": {"enum": ["바다"]}}}}
        self.assertEqual(_skeleton(sch), {"days": 0, "pace": "여유롭게", "interests": ["바다"]})
        c = client_from_env({"LLM_API_KEY": "k", "LLM_BASE_URL": "u", "LLM_MODEL": "m", "LLM_TIMEOUT_S": "60"}, S)
        self.assertEqual(c.timeout_s, 60.0)

