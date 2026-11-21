import json
import tempfile
import unittest
from pathlib import Path

from models_config import ModelsConfig


class ModelsConfigRuntimeOptionsTests(unittest.TestCase):
    def test_runtime_options_round_trip_without_model_family_assumptions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "models.json"
            config = ModelsConfig(str(config_path))

            saved = config.add_model(
                alias="provider-example-model",
                provider_alias="official",
                api_key="test-key",
                base_url="https://api.openai.com/v1",
                model_provider="openai",
                model_name="example-model",
                api_mode="responses",
                reasoning_effort="medium",
                prompt_cache_ttl="30m",
                service_tier="standard",
            )

            self.assertTrue(saved)
            stored = json.loads(config_path.read_text(encoding="utf-8"))
            model = stored["models"][0]
            self.assertEqual(model["api_mode"], "responses")
            self.assertEqual(model["reasoning_effort"], "medium")
            self.assertEqual(model["prompt_cache_ttl"], "30m")
            self.assertEqual(model["service_tier"], "standard")


if __name__ == "__main__":
    unittest.main()
