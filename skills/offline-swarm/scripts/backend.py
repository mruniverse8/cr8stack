#!/usr/bin/env python3
"""Set the Codex CLI backend before an offline-swarm worker starts."""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

BACKEND_NAME = "codex-cli"
BACKEND_FILE = "backend.json"
EFFORTS = ("low", "medium", "high", "xhigh", "max")
SANDBOXES = ("workspace-write", "read-only")
FLAG_GROUPS = {
    "model": ("-m", "--model"),
    "config": ("-c", "--config"),
    "sandbox": ("--sandbox",),
    "cd": ("-C", "--cd"),
    "output": ("-o", "--output-last-message"),
    "worktree": ("--worktree",),
    "ephemeral": ("--ephemeral",),
    "color": ("--color",),
    "approve": ("--approve-for-me",),
}


def fail(message):
    print(message, file=sys.stderr)
    raise SystemExit(1)


def codex_bin():
    found = shutil.which("codex")
    if not found:
        fail("codex-cli is not installed. Offline swarm stays stopped until `codex` is on PATH.")
    return found


def run(argv):
    return subprocess.run(argv, capture_output=True, text=True)


def help_text(binary):
    chunks = []
    for argv in ([binary, "exec", "--help"], [binary, "--help"]):
        result = run(argv)
        chunks.append(result.stdout)
        chunks.append(result.stderr)
    return "\n".join(chunks)


def choose_flag(blob, group):
    for flag in FLAG_GROUPS[group]:
        if flag in blob:
            return flag
    return None


def backend_path(run_dir):
    return Path(run_dir) / BACKEND_FILE


def load_backend(run_dir):
    path = backend_path(run_dir)
    if not path.is_file():
        fail(
            "set the backend first: "
            f"python3 {Path(__file__).resolve()} init --run {run_dir} "
            "--model <slug> --effort <level>"
        )
    data = json.loads(path.read_text())
    if data.get("backend") != BACKEND_NAME:
        fail(f"backend file says {data.get('backend')}. Offline swarm uses {BACKEND_NAME}.")
    return data


def command_init(args):
    if args.effort not in EFFORTS:
        fail(f"effort must be one of {', '.join(EFFORTS)}.")
    binary = codex_bin()
    blob = help_text(binary)
    flags = {name: choose_flag(blob, name) for name in FLAG_GROUPS}
    if not flags["model"]:
        fail("codex exec has no model flag. The backend is not set.")
    catalog = run([binary, "debug", "models"])
    catalog_text = catalog.stdout + "\n" + catalog.stderr
    if catalog.returncode != 0:
        fail("codex debug models failed. The backend is not set.")
    if args.model not in catalog_text:
        fail(f"{args.model} is not in the Codex model catalog.")
    version = run([binary, "--version"])
    data = {
        "backend": BACKEND_NAME,
        "bin": binary,
        "version": (version.stdout or version.stderr).strip(),
        "model": args.model,
        "reasoning_effort": args.effort,
        "sandbox": args.sandbox,
        "flags": flags,
        "catalog": catalog_text,
    }
    path = backend_path(args.run)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")
    print(
        f"backend {BACKEND_NAME} model {args.model} "
        f"effort {args.effort} sandbox {args.sandbox}"
    )


def selected(data, model, effort):
    chosen_model = model or data["model"]
    chosen_effort = effort or data["reasoning_effort"]
    if chosen_model not in data["catalog"]:
        fail(f"{chosen_model} is not in the catalog recorded with the backend.")
    if chosen_effort not in EFFORTS:
        fail(f"effort must be one of {', '.join(EFFORTS)}.")
    return chosen_model, chosen_effort


def command_exec(args):
    data = load_backend(args.run)
    model, effort = selected(data, args.model, args.effort)
    flags = data["flags"]
    argv = [data["bin"], "exec"]
    if flags.get("worktree"):
        argv.append(flags["worktree"])
    argv.extend([flags["model"], model])
    if flags.get("config"):
        argv.extend([flags["config"], f'model_reasoning_effort="{effort}"'])
    if flags.get("cd"):
        argv.extend([flags["cd"], args.cwd])
    sandbox = args.sandbox or data["sandbox"]
    if sandbox not in SANDBOXES:
        fail(f"sandbox must be one of {', '.join(SANDBOXES)}.")
    if flags.get("sandbox"):
        argv.extend([flags["sandbox"], sandbox])
    if sandbox != "read-only" and flags.get("approve"):
        argv.append(flags["approve"])
    if flags.get("ephemeral"):
        argv.append(flags["ephemeral"])
    if flags.get("color"):
        argv.extend([flags["color"], "never"])
    if flags.get("output"):
        argv.extend([flags["output"], args.output])
    prompt = sys.stdin.read()
    result = subprocess.run(argv, input=prompt, text=True)
    raise SystemExit(result.returncode)


def build_parser():
    parser = argparse.ArgumentParser(description="Set the Codex CLI backend, then launch one worker.")
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init")
    init.add_argument("--run", required=True)
    init.add_argument("--model", required=True)
    init.add_argument("--effort", required=True)
    init.add_argument("--sandbox", choices=SANDBOXES, default="workspace-write")
    init.set_defaults(func=command_init)

    execute = commands.add_parser("exec")
    execute.add_argument("--run", required=True)
    execute.add_argument("--cwd", required=True)
    execute.add_argument("--output", required=True)
    execute.add_argument("--model")
    execute.add_argument("--effort")
    execute.add_argument("--sandbox", choices=SANDBOXES)
    execute.set_defaults(func=command_exec)
    return parser


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
