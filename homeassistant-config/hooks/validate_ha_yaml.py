#!/usr/bin/env python3
"""
PostToolUse hook: validate YAML right after Claude writes or edits it.

Claude Code sends the hook event as JSON on stdin (there is no
$CLAUDE_TOOL_INPUT variable). We read `tool_input.file_path`, then validate the
WHOLE file on disk, which works the same for Write, Edit and MultiEdit (an Edit
only carries a fragment, which is not valid YAML on its own).

- Errors (syntax, tabs, duplicate keys, removed syntax) -> `decision: block`, so
  Claude sees the problem and fixes it in the same turn.
- Warnings (deprecated-but-working syntax) -> exit 0 + additionalContext, so
  Claude is told without interrupting anything.
- Anything unexpected (no PyYAML, unreadable file, bad JSON) -> exit 0 silently.
  A validator must never block work because of its own bugs.

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


def main() -> int:
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

    plugin_root = Path(os.environ.get("CLAUDE_PLUGIN_ROOT") or Path(__file__).resolve().parent.parent)
    sys.path.insert(0, str(plugin_root / "skills" / "homeassistant-config" / "scripts"))
    try:
        from validate_yaml import HAYamlValidator  # noqa: E402
        from ha_yaml import require_yaml  # noqa: E402
    except Exception:
        return 0
    if require_yaml():
        return 0

    try:
        result = HAYamlValidator(ha_rules=None).validate_file(str(path))
    except Exception:
        return 0

    errors = result.get("errors") or []
    if result.get("error"):
        errors = [f"{result['error']}: {result.get('details', '')}".strip(": ")] + errors
    warnings = result.get("warnings") or []

    # Dashboards get the dashboard rules too (syntax is already covered above).
    if not result.get("error") and is_dashboard(path, result.get("keys")):
        try:
            from lovelace_validator import LovelaceValidator  # noqa: E402
            dash = LovelaceValidator().validate_file(str(path))
            errors += [e for e in dash.get("errors") or [] if e not in errors]
            warnings += [w for w in dash.get("warnings") or [] if w not in warnings]
        except Exception:
            pass

    if errors:
        lines = [f"Home Assistant YAML check failed for {path}:"]
        lines += [f"  - {e}" for e in errors[:MAX_MESSAGES]]
        if warnings:
            lines.append("Also worth fixing:")
            lines += [f"  - {w}" for w in warnings[: max(0, MAX_MESSAGES - len(errors))]]
        lines.append("Fix the file before continuing (run validate_yaml.py from the homeassistant-config skill for the full report).")
        # PostToolUse cannot undo the write; `decision: block` feeds the reason
        # back to Claude so it repairs the file in the same turn.
        print(json.dumps({
            "decision": "block",
            "reason": "\n".join(lines),
            "hookSpecificOutput": {"hookEventName": "PostToolUse"},
        }))
        return 0

    if warnings:
        shown = warnings[:MAX_MESSAGES]
        more = len(warnings) - len(shown)
        context = (
            f"homeassistant-config: {path.name} is valid YAML, but uses outdated Home Assistant syntax:\n"
            + "\n".join(f"- {w}" for w in shown)
            + (f"\n- ... and {more} more" if more > 0 else "")
            + "\nUpdate it to the current syntax unless the user asked to keep it."
        )
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": context,
            }
        }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
