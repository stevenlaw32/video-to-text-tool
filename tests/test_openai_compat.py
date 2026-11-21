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


class _UnavailableResponses:
    def create(self, **kwargs):
        error = RuntimeError("unknown endpoint")
        error.status_code = 404
        raise error


class OpenAICompatTests(unittest.TestCase):
    def test_auto_prefers_responses_without_model_specific_defaults(self):
        mode, params = build_request(
            model="future-model",
            user_message="整理这段文字",
            developer_prompt="长期复用的规则",
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
        self.assertNotIn("reasoning", params)
        self.assertNotIn("prompt_cache_options", params)
        self.assertEqual(params["input"][0]["role"], "developer")
        self.assertEqual(params["input"][0]["content"], "长期复用的规则")
        self.assertEqual(params["input"][-1]["role"], "user")

    def test_reasoning_effort_is_explicit_and_version_agnostic(self):
        self.assertIsNone(resolve_reasoning_effort("auto"))
        self.assertEqual(resolve_reasoning_effort("none"), "none")
        self.assertEqual(resolve_reasoning_effort("minimal"), "minimal")
        self.assertEqual(resolve_reasoning_effort("medium"), "medium")

    def test_explicit_chat_keeps_chat_compatibility(self):
        mode, params = build_request(
            model="compatible-model",
            user_message="hello",
            developer_prompt="system",
            temperature=0.4,
            api_mode="chat",
        )

        self.assertEqual(mode, "chat")
        self.assertEqual(params["temperature"], 0.4)
        self.assertNotIn("reasoning_effort", params)
        self.assertEqual(params["messages"][0]["role"], "system")

    def test_explicit_temperature_is_passed_through(self):
        _, params = build_request(
            model="reasoning-model",
            user_message="hello",
            temperature=0.7,
            reasoning_effort="high",
        )
        self.assertEqual(params["reasoning"], {"effort": "high"})
        self.assertEqual(params["temperature"], 0.7)

    def test_explicit_cache_and_service_tier_are_passed_through(self):
        _, params = build_request(
            model="any-model",
            user_message="hello",
            prompt_cache_ttl="12h",
            service_tier="flex",
        )
        self.assertEqual(params["prompt_cache_options"], {"ttl": "12h"})
        self.assertEqual(params["service_tier"], "flex")

    def test_request_policy_does_not_branch_on_model_name(self):
        _, first = build_request(
            model="model-version-a",
            user_message="hello",
            reasoning_effort="low",
            prompt_cache_ttl="30m",
        )
        _, second = build_request(
            model="model-version-b",
            user_message="hello",
            reasoning_effort="low",
            prompt_cache_ttl="30m",
        )
        first.pop("model")
        second.pop("model")
        self.assertEqual(first, second)

    def test_complete_text_calls_responses_client(self):
        recorder = _CreateRecorder(SimpleNamespace(output_text="完成"))
        client = SimpleNamespace(responses=recorder)

        result = complete_text(
            client,
            model="future-model",
            user_message="hello",
        )

        self.assertEqual(result, "完成")
        self.assertEqual(recorder.params["input"][-1]["content"], "hello")

    def test_auto_falls_back_to_chat_when_responses_endpoint_is_missing(self):
        chat_recorder = _CreateRecorder(
            SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="回退成功"))]
            )
        )
        client = SimpleNamespace(
            responses=_UnavailableResponses(),
            chat=SimpleNamespace(completions=chat_recorder),
        )

        result = complete_text(
            client,
            model="provider-model",
            user_message="hello",
            api_mode="auto",
        )

        self.assertEqual(result, "回退成功")
        self.assertEqual(chat_recorder.params["messages"][-1]["content"], "hello")

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
