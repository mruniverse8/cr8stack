import json
import os
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills" / "offline-swarm" / "scripts" / "backend.py"
FAKE = textwrap.dedent(
    """\
    #!/bin/sh
    printf '%s\\n' "$@" >> "$CODEX_ARGV_LOG"
    if [ "$1" = "exec" ] && [ "$2" = "--help" ]; then
      echo "codex exec --worktree -m --model -c --sandbox -C --cd -o --ephemeral --color --approve-for-me"
      exit 0
    fi
    if [ "$1" = "--help" ]; then
      echo "codex exec"
      exit 0
    fi
    if [ "$1" = "--version" ]; then
      echo "codex-cli test"
      exit 0
    fi
    if [ "$1" = "debug" ]; then
      echo "gpt-6-sol visibility list"
      echo "gpt-6.1-terra visibility list"
      exit 0
    fi
    if [ "$1" = "exec" ]; then
      cat > "$CODEX_PROMPT_LOG"
      exit 0
    fi
    exit 1
    """
)


class Backend(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        bindir = root / "bin"
        bindir.mkdir()
        codex = bindir / "codex"
        codex.write_text(FAKE)
        codex.chmod(codex.stat().st_mode | stat.S_IEXEC)
        self.env = os.environ.copy()
        self.env["PATH"] = str(bindir) + os.pathsep + self.env.get("PATH", "")
        self.env["CODEX_ARGV_LOG"] = str(root / "argv.log")
        self.env["CODEX_PROMPT_LOG"] = str(root / "prompt.txt")
        self.run_dir = root / "run"
        self.repo = root / "repo"
        self.repo.mkdir()

    def command(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=self.repo,
            env=self.env,
            text=True,
            capture_output=True,
        )

    def test_exec_requires_the_backend(self):
        result = self.command("exec", "--run", str(self.run_dir), "--cwd", str(self.repo), "--output", "out.md")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("set the backend first", result.stderr)

    def test_init_records_the_codex_cli_backend(self):
        result = self.command(
            "init", "--run", str(self.run_dir), "--model", "gpt-6-sol", "--effort", "xhigh"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads((self.run_dir / "backend.json").read_text())
        self.assertEqual(data["backend"], "codex-cli")
        self.assertEqual(data["model"], "gpt-6-sol")
        self.assertEqual(data["reasoning_effort"], "xhigh")
        self.assertTrue(data["bin"].endswith("codex"))

    def test_init_rejects_a_model_outside_the_catalog(self):
        result = self.command(
            "init", "--run", str(self.run_dir), "--model", "missing-model", "--effort", "high"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.run_dir / "backend.json").exists())

    def test_exec_uses_the_recorded_backend(self):
        init = self.command(
            "init", "--run", str(self.run_dir), "--model", "gpt-6-sol", "--effort", "xhigh"
        )
        self.assertEqual(init.returncode, 0, init.stderr)
        result = self.command(
            "exec",
            "--run", str(self.run_dir),
            "--cwd", str(self.repo),
            "--output", str(self.run_dir / "worker.md"),
            "--model", "gpt-6.1-terra",
            "--effort", "high",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        argv = Path(self.env["CODEX_ARGV_LOG"]).read_text()
        self.assertIn("exec", argv)
        self.assertIn("gpt-6.1-terra", argv)
        self.assertIn('model_reasoning_effort="high"', argv)
        self.assertNotIn("gpt-6-sol", argv.split("exec\n", 1)[-1])

    def test_poteto_swarm_has_no_codex_adapter(self):
        swarm = (ROOT / "skills" / "swarm" / "SKILL.md").read_text()
        poteto = (ROOT / "skills" / "poteto-mode" / "SKILL.md").read_text()
        self.assertNotIn("Codex", swarm)
        self.assertNotIn("Codex", poteto)
        self.assertFalse((ROOT / "skills" / "swarm-cloud").exists())
        self.assertFalse((ROOT / "skills" / "pstack-set-codex").exists())
        self.assertFalse((ROOT / "skills" / "pstack-set-mode").exists())


if __name__ == "__main__":
    unittest.main()
