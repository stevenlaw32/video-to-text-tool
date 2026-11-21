import unittest
from pathlib import Path


class ModelSettingsTemplateTests(unittest.TestCase):
    def test_generation_controls_are_model_version_agnostic(self):
        template = (
            Path(__file__).resolve().parents[1] / "templates" / "models_settings.html"
        ).read_text(encoding="utf-8")

        self.assertNotIn("GPT-6.2", template)
        self.assertNotIn("Astra/Sol", template)
        self.assertIn("优先 Responses，不支持时回退 Chat", template)
        self.assertIn("自动（由模型决定）", template)


if __name__ == "__main__":
    unittest.main()
