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

    def test_prompt_editor_uses_full_width_responsive_section(self):
        template = (
            Path(__file__).resolve().parents[1] / "templates" / "models_settings.html"
        ).read_text(encoding="utf-8")

        grid_end = template.index('id="promptEditorSection"')
        form_end = template.index("</form>")
        self.assertGreater(grid_end, form_end)
        self.assertIn('class="grid grid-cols-1 lg:grid-cols-2 gap-8"', template)
        self.assertIn('class="prompt-editor w-full', template)
        self.assertIn("min-height: clamp(24rem, 52vh, 48rem)", template)
        self.assertIn('rows="18"', template)


if __name__ == "__main__":
    unittest.main()
