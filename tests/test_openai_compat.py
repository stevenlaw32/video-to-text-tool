import unittest
from types import SimpleNamespace

from openai_compat import (
    build_request,
    complete_text,
    extract_response_text,
    resolve_reasoning_effort,
)


class _CreateRecorder:
    def __init__(self, response):
        self.response = response
        self.params = None

    def create(self, **kwargs):
        self.params = kwargs
        return self.response


class OpenAICompatTests(unittest.TestCase):
    def test_gpt62_auto_uses_responses_and_sanitizes_parameters(self):
        mode, params = build_request(
            model="gpt-6.2-sol",
            user_message="整理这段文字",
            developer_prompt="长期复用的规则",
            temperature=0.7,
            max_tokens=1200,
            reasoning_effort="auto",
            api_mode="auto",
            prompt_cache_ttl="auto",
            service_tier="standard",
        )

        self.assertEqual(mode, "responses")
        self.assertNotIn("temperature", params)
        self.assertNotIn("max_tokens", params)
        self.assertEqual(params["max_output_tokens"], 1200)
        self.assertEqual(params["reasoning"], {"effort": "medium"})
        self.assertEqual(params["prompt_cache_options"], {"ttl": "30m"})
        self.assertEqual(params["input"][0]["role"], "developer")
        self.assertEqual(params["input"][0]["content"], "长期复用的规则")
        self.assertEqual(params["input"][-1]["role"], "user")

    def test_legacy_none_and_minimal_migrate_to_low(self):
        self.assertEqual(resolve_reasoning_effort("gpt-6.2-astra", "none"), "low")
        self.assertEqual(resolve_reasoning_effort("gpt-6.2-sol", "minimal"), "low")
        self.assertEqual(resolve_reasoning_effort("openai/gpt-6.2-sol", "auto"), "medium")

    def test_non_gpt62_auto_keeps_chat_compatibility(self):
        mode, params = build_request(
            model="gpt-4o",
            user_message="hello",
            developer_prompt="system",
            temperature=0.4,
            api_mode="auto",
        )

        self.assertEqual(mode, "chat")
        self.assertEqual(params["temperature"], 0.4)
        self.assertNotIn("reasoning_effort", params)
        self.assertEqual(params["messages"][0]["role"], "system")

    def test_gpt62_tools_reject_chat_completions(self):
        with self.assertRaisesRegex(ValueError, "工具调用必须使用 Responses"):
            build_request(
                model="gpt-6.2-astra",
                user_message="hello",
                api_mode="chat",
                tools=[{"type": "function", "name": "lookup"}],
            )

    def test_gpt62_rejects_flex_service_tier(self):
        with self.assertRaisesRegex(ValueError, "不支持 service_tier=flex"):
            build_request(
                model="gpt-6.2-sol",
                user_message="hello",
                service_tier="flex",
            )

    def test_complete_text_calls_responses_client(self):
        recorder = _CreateRecorder(SimpleNamespace(output_text="完成"))
        client = SimpleNamespace(responses=recorder)

        result = complete_text(
            client,
            model="gpt-6.2-sol",
            user_message="hello",
        )

        self.assertEqual(result, "完成")
        self.assertEqual(recorder.params["input"][-1]["content"], "hello")

    def test_extract_response_text_falls_back_to_output_items(self):
        response = {
            "output": [
                {"content": [{"type": "output_text", "text": "第一段"}]},
                {"content": [{"type": "output_text", "text": "第二段"}]},
            ]
        }
        self.assertEqual(extract_response_text(response), "第一段第二段")


if __name__ == "__main__":
    unittest.main()
