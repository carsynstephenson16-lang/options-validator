import unittest
from pathlib import Path

from options_researcher import foundation
from scripts import new_research_note


ROOT = Path(__file__).resolve().parents[1]


class FoundationLayoutTests(unittest.TestCase):
    def test_required_foundation_paths_exist(self):
        self.assertEqual(foundation.missing_required_paths(ROOT), [])

    def test_obsidian_templates_are_unignored_but_vault_config_stays_ignored(self):
        gitignore = (ROOT / ".gitignore").read_text()
        self.assertIn(".obsidian/*", gitignore)
        self.assertIn("!.obsidian/templates/", gitignore)
        self.assertIn("!.obsidian/templates/**", gitignore)

    def test_forbidden_capabilities_are_explicit(self):
        self.assertEqual(
            set(foundation.FORBIDDEN_CAPABILITIES),
            {
                "paid_api_integration",
                "live_trading",
                "broker_order_placement",
                "hardcoded_secrets",
            },
        )

    def test_note_slug_is_stable_and_filesystem_safe(self):
        self.assertEqual(
            new_research_note.slugify("SPY $2-Wide Put Spread: Phase 0"),
            "spy-2-wide-put-spread-phase-0",
        )

    def test_note_template_render_replaces_local_placeholders(self):
        rendered = new_research_note.render_template(
            "# {{title}}\n{{date}}\n",
            title="My Test",
            today=__import__("datetime").date(2026, 7, 2),
        )
        self.assertEqual(rendered, "# My Test\n2026-07-02\n")


if __name__ == "__main__":
    unittest.main()
