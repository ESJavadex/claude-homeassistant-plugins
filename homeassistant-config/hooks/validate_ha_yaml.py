#!/usr/bin/env python3
"""
PostToolUse hook: validate YAML right after Claude writes or edits it.

Claude Code sends the hook event as JSON on stdin (there is no
$CLAUDE_TOOL_INPUT variable). We read `tool_input.file_path`, then validate the
WHOLE file on disk, which works the same for Write, Edit and MultiEdit (an Edit
only carries a fragment, which is not valid YAML on its own).

- Only a broken file blocks (YAML syntax error, tabs, duplicate keys): that is
  certain whatever Home Assistant version runs. `decision: block` makes Claude
  fix it in the same turn.
- Home Assistant rules (removed or deprecated syntax) are compared with the
  installed release (`.HA_VERSION`) and passed as additionalContext: advice,
  never a forced edit. `ha core check` and Settings > Repairs have the last word.
- No PyYAML: re-run with a system Python that has it (a persistent venv without
  --system-site-packages hides the image's py3-yaml); if none has it, say the
  check was skipped instead of passing in silence.
- Anything unexpected (unreadable file, bad JSON, a bug here) -> exit 0
  silently. A validator must never block work because of its own bugs.

Home Assistant rules only run when the file looks like HA config (an ancestor
holds configuration.yaml, the path is under /config or /homeassistant, or it is
a blueprint). Other YAML (CI workflows, docker-compose...) only gets the
syntax and tab checks.
"""

import json
import os
import sys
from pathlib import Path

MAX_MESSAGES = 12


def is_dashboard(path: Path, keys) -> bool:
    """A YAML dashboard: has `views:`, or lives where dashboards usually live."""
    name = path.name.lower()
    if keys and "views" in keys:
        return True
    return name.startswith(("ui-lovelace", "lovelace")) or any(
        part.lower() in ("dashboards", "lovelace") for part in path.parent.parts[-2:]
    )


def emit_context(text: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": text}}))


def main() -> int:
    plugin_root = Path(os.environ.get("CLAUDE_PLUGIN_ROOT") or Path(__file__).resolve().parent.parent)
    sys.path.insert(0, str(plugin_root / "skills" / "homeassistant-config" / "scripts"))
    try:
        from ha_yaml import ensure_yaml, require_yaml  # noqa: E402
    except Exception:
        return 0
    ensure_yaml()  # may re-exec with another Python; stdin is still unread here

    try:
        event = json.load(sys.stdin)
    except Exception:
        return 0

    tool_input = event.get("tool_input") or {}
    file_path = tool_input.get("file_path") or tool_input.get("path") or ""
    if not file_path or not file_path.lower().endswith((".yaml", ".yml")):
        return 0

    path = Path(file_path)
    if not path.is_absolute():
        path = Path(event.get("cwd") or os.getcwd()) / path
    if not path.is_file():
        return 0

    missing = require_yaml()
    if missing:
        emit_context(f"homeassistant-config: the YAML check for {path.name} was skipped. {missing}")
        return 0
    try:
        from validate_yaml import HAYamlValidator  # noqa: E402
    except Exception:
        return 0

    try:
        result = HAYamlValidator(ha_rules=None).validate_file(str(path))
    except Exception:
        return 0

    broken = []  # the file itself is broken: certain, so it blocks
    if result.get("error"):
        broken.append(f"{result['error']}: {result.get('details', '')}".strip(": "))
    findings = result.get("findings") or []
    fmt = format_finding
    broken += [fmt(f) for f in findings if f.get("kind") == "yaml" and f["level"] == "error"]
    errors = [fmt(f) for f in findings if f.get("kind") != "yaml" and f["level"] == "error" and not f.get("upcoming")]
    warnings = [fmt(f) for f in findings if f["level"] == "warning" and not f.get("upcoming")]
    upcoming = [fmt(f) for f in findings if f.get("upcoming") and f["level"] != "info"]

    # Dashboards get the dashboard rules too (syntax is already covered above).
    if not result.get("error") and (result.get("dashboard") or is_dashboard(path, result.get("keys"))):
        try:
            from lovelace_validator import LovelaceValidator  # noqa: E402
            dash = LovelaceValidator().validate_file(str(path))
            errors += [e for e in dash.get("errors") or [] if e not in errors]
            warnings += [w for w in dash.get("warnings") or [] if w not in warnings]
        except Exception:
            pass

    if broken:
        lines = [f"{path} is not valid YAML, so Home Assistant cannot load it:"]
        lines += [f"  - {e}" for e in broken[:MAX_MESSAGES]]
        lines.append("Fix the file before continuing.")
        # PostToolUse cannot undo the write; `decision: block` feeds the reason
        # back to Claude so it repairs the file in the same turn.
        print(json.dumps({
            "decision": "block",
            "reason": "\n".join(lines),
            "hookSpecificOutput": {"hookEventName": "PostToolUse"},
        }))
        return 0

    if not (errors or warnings or upcoming):
        return 0
    version = result.get("ha_version")
    running = f"Home Assistant {version}" if version else "current Home Assistant (installed version unknown)"
    lines = [f"homeassistant-config checked {path.name} against {running}:"]
    budget = MAX_MESSAGES
    for title, items in (
        ("Will not work (fix before relying on it):", errors),
        ("Deprecated or ignored:", warnings),
        ("Fine for now, changes in a newer release:", upcoming),
    ):
        if items and budget > 0:
            lines.append(title)
            lines += [f"- {i}" for i in items[:budget]]
            if len(items) > budget:
                lines.append(f"- ... and {len(items) - budget} more")
            budget -= len(items)
    if result.get("note"):
        lines.append(result["note"])
    lines.append("Fix what applies unless the user asked to keep it. If `ha core check` or "
                 "Settings > Repairs disagree with this check, they are right.")
    emit_context("\n".join(lines))
    return 0


def format_finding(f: dict) -> str:
    where = f"Line {f['line']}: " if f.get("line") else ""
    at = f"{f['path']}: " if f.get("path") else ""
    since = f" [HA {f['since']}]" if f.get("since") else ""
    return f"{where}{at}{f['message']}{since}"


if __name__ == "__main__":
    sys.exit(main())
