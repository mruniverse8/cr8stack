import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[3]


def text(path):
    return (ROOT / path).read_text()


class ModeGates(unittest.TestCase):
    def test_modes_follow_the_process(self):
        modes = text("skills/pstack-set-mode/references/modes.md")
        self.assertIn("The process wins.", modes)
        self.assertIn("Do not run `command -v codex` to decide.", modes)
        self.assertIn("`$swarm-cloud` means this path.", modes)
        self.assertLess(modes.index("## cursor"), modes.index("## codex"))

    def test_cursor_rule_names_cursor_cloud(self):
        rule = text(".cursor/rules/pstack-mode.mdc")
        self.assertIn("mode: cursor", rule)
        self.assertIn("https://cursor.com/agents", rule)
        self.assertIn("Do not run `codex cloud exec`.", rule)

    def test_swarm_cloud_stops_cursor_before_codex(self):
        skill = text("skills/swarm-cloud/SKILL.md")
        cursor = skill.index("## Cursor cloud")
        codex = skill.index("## Codex cloud")
        self.assertLess(cursor, codex)
        self.assertIn("including a Cursor cloud agent, stop after this section", skill)
        self.assertIn("Do not look for the `codex` binary", skill)

    def test_swarm_routes_cursor_cloud_to_start(self):
        skill = text("skills/swarm/SKILL.md")
        self.assertIn("`$swarm-cloud` is Start with `environment: \"cloud\"`", skill)
        self.assertLess(skill.index("**Cursor:**"), skill.index("## Codex execution routing"))

    def test_cursor_workflows_keep_cursor_models(self):
        arena = text("skills/arena/SKILL.md")
        why = text("skills/why/SKILL.md")
        cursor_arena = arena.split("## Cursor workflow", 1)[1]
        cursor_why = why.split("## Cursor workflow", 1)[1]
        self.assertIn("claude-opus-5-5-xhigh", cursor_arena)
        self.assertIn("grok-4.7-xhigh-fast", cursor_arena)
        self.assertNotIn("gpt-6-sol", cursor_arena)
        self.assertNotIn("gpt-6-astra", cursor_arena)
        self.assertIn("default `grok-4.7-xhigh-fast`", cursor_why)
        self.assertIn("default `claude-opus-5-5-xhigh`", cursor_why)
        self.assertNotIn("gpt-6", cursor_why)

    def test_codex_model_setup_does_not_install_a_cursor_rule(self):
        skill = text("skills/pstack-set-codex/SKILL.md")
        self.assertIn("Do not write `~/.cursor/rules/pstack-codex.mdc`.", skill)
        self.assertNotIn("alwaysApply: true", skill)


if __name__ == "__main__":
    unittest.main()
