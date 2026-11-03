#!/usr/bin/env python3
"""
Home Assistant YAML validator (rules up to Home Assistant 2026.11).

Usage:
  python3 validate_yaml.py <file-or-directory> [more paths...] [--strict] [--all] [--quiet]
                           [--include-unloaded] [--ha-version=2026.10]

  --strict            warnings also make the run fail
  --all               apply Home Assistant rules even if the file does not look like HA config
  --quiet             print only files that have findings (directory mode)
  --include-unloaded  also check files that configuration.yaml never loads
                      (archive or draft folders are skipped by default)
  --ha-version=X      check against this release instead of the installed one

Version: rules are compared with the Home Assistant release that runs the
config (`.HA_VERSION` in the config folder, or the HA_VERSION variable). A rule
from a newer release is reported under "upcoming" (it will matter when you
update), not as an error.

What it checks
  * YAML syntax with Home Assistant tags (!include, !secret, !input, !env_var...)
  * tabs and duplicate keys (the last duplicate silently wins in HA)
  * syntax that HA removed (error), deprecated (warning) or replaced but still
    accepted (info), with the release where it changed.

Levels
  error     will not work on the installed Home Assistant
  warning   deprecated or ignored; will break or already does nothing
  info      old style that still works; modernise when you touch it
  upcoming  fine on the installed release, changes in a newer one

Output: JSON. Exit code 0 when valid, 1 otherwise.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, List, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ha_yaml import (  # noqa: E402
    RULES_CURRENT_TO,
    HATag,
    ensure_yaml,
    find_config_root,
    installed_version,
    is_unloaded,
    iter_yaml_files,
    line_of,
    load_text,
    loaded_files,
    parse_version,
    require_yaml,
)

try:
    import yaml  # noqa: F401
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore

LEGACY_TEMPLATE_DOMAINS = {
    "sensor", "binary_sensor", "switch", "cover", "fan", "light", "lock",
    "vacuum", "weather", "alarm_control_panel",
}
TEMPLATE_PLATFORMS = {
    "alarm_control_panel", "binary_sensor", "button", "climate", "cover",
    "device_tracker", "event", "fan", "image", "light", "lock", "number",
    "select", "sensor", "switch", "update", "vacuum", "weather",
}
LEGACY_TEMPLATE_KEYS = {
    "value_template": "state",
    "friendly_name": "name",
    "friendly_name_template": "name",
    "icon_template": "icon",
    "entity_picture_template": "picture",
    "availability_template": "availability",
    "attribute_templates": "attributes",
}
TRIGGER_LIST_KEYS = {"triggers", "trigger", "wait_for_trigger"}

# Purpose-specific triggers/conditions renamed or removed (2026.5 - 2026.7).
REMOVED_TRIGGERS = {
    "battery.low": ("battery.became_low", "2026.7"),
    "battery.not_low": ("battery.no_longer_low", "2026.7"),
    "lawn_mower.docked": ("lawn_mower.returned_to_dock", "2026.7"),
    "vacuum.docked": ("vacuum.returned_to_dock", "2026.7"),
    "schedule.turned_on": ("schedule.block_started", "2026.7"),
    "schedule.turned_off": ("schedule.block_ended", "2026.7"),
    "timer.time_remaining": ("timer.remaining_time_reached", "2026.7"),
    "update.update_became_available": ("update.became_available", "2026.7"),
    "person.entered_home": ("zone.entered (target zone.home)", "2026.5"),
    "person.left_home": ("zone.left (target zone.home)", "2026.5"),
    "device_tracker.entered_home": ("zone.entered (target zone.home)", "2026.5"),
    "device_tracker.left_home": ("zone.left (target zone.home)", "2026.5"),
}
REMOVED_CONDITIONS = {
    "climate.target_temperature": ("climate.is_target_temperature", "2026.7"),
    "climate.target_humidity": ("climate.is_target_humidity", "2026.7"),
    "person.is_home": ("zone.in_zone (target zone.home)", "2026.5"),
    "person.is_not_home": ("not + zone.in_zone (target zone.home)", "2026.5"),
    "device_tracker.is_home": ("zone.in_zone (target zone.home)", "2026.5"),
    "device_tracker.is_not_home": ("not + zone.in_zone (target zone.home)", "2026.5"),
}
ZONE_BEHAVIOR_RENAMES = {"any": "each", "last": "all"}
# A state condition may read its target state from one of these entities.
ENTITY_STATE_DOMAINS = {"input_select", "input_text", "input_number", "input_datetime", "select", "sensor", "text"}

BOOL_LINE = re.compile(
    r"^\s*(?:-\s+)?(to|from|not_to|not_from|state|option|payload|payload_on|payload_off)\s*:\s*(on|off|yes|no)\s*(?:#.*)?$",
    re.IGNORECASE,
)
ENTITY_ID = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+$")
# The UI editor writes entity registry IDs (32 hex chars) in device triggers/actions.
REGISTRY_ID = re.compile(r"^[0-9a-f]{32}$")
ACTION_ID = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+$")
HA_TOP_KEYS = {
    "homeassistant", "automation", "script", "scene", "template", "sensor",
    "binary_sensor", "input_boolean", "input_number", "input_select",
    "input_text", "input_datetime", "input_button", "counter", "timer",
    "group", "recorder", "logger", "lovelace", "frontend", "default_config",
    "mqtt", "notify", "http", "zone", "person", "blueprint", "shell_command",
    "rest_command", "command_line", "utility_meter", "history_stats",
    "conversation", "intent_script", "light", "switch", "cover", "fan",
}


def _is_template(value: Any) -> bool:
    return isinstance(value, str) and ("{{" in value or "{%" in value)


class HAYamlValidator:
    """Validate one Home Assistant YAML file."""

    def __init__(self, strict: bool = False, ha_rules: Optional[bool] = None,
                 ha_version: Optional[str] = "auto"):
        self.strict = strict
        self.ha_rules = ha_rules  # None = auto-detect
        self.ha_version = ha_version  # "auto" = read .HA_VERSION next to the config, None = unknown
        self.findings: List[dict] = []

    # ------------------------------------------------------------------ api
    def validate_file(self, file_path: str) -> dict:
        path = Path(file_path)
        if not path.exists():
            return {"valid": False, "file": str(path), "error": f"File not found: {file_path}"}
        try:
            content = path.read_text(encoding="utf-8")
        except Exception as exc:  # pragma: no cover
            return {"valid": False, "file": str(path), "error": f"Cannot read file: {exc}"}
        return self.validate_text(content, path)

    def validate_text(self, content: str, path: Path = Path("<stdin>")) -> dict:
        self.findings = []
        for i, line in enumerate(content.splitlines(), 1):
            if "\t" in line[: len(line) - len(line.lstrip(" \t"))]:
                self._add("error", i, "", "Tab used for indentation (Home Assistant needs spaces)", kind="yaml")

        try:
            data, duplicates = load_text(content)
        except Exception as exc:
            msg = str(exc)
            m = re.search(r"line (\d+)", msg)
            return self._result(path, None, syntax_error=msg, line=int(m.group(1)) if m else None)

        for key, line in duplicates:
            self._add("error", line, key, f"Duplicate key '{key}': only the last one is used", kind="yaml")

        apply = self.ha_rules if self.ha_rules is not None else looks_like_ha(path, data)
        if apply:
            self._check_bool_lines(content)
            self._visit(data, "", ())
            if isinstance(data, dict):
                self._check_root(data, path)
            self._check_template_text(content)
        return self._result(path, data, ha_rules=apply)

    # -------------------------------------------------------------- helpers
    def _add(self, level: str, line: int, path: str, message: str, since: Optional[str] = None,
             kind: str = "ha"):
        """kind: "yaml" = the file itself is broken (certain); "ha" = a Home Assistant rule."""
        self.findings.append({
            "level": level,
            "line": line or None,
            "path": path,
            "message": message,
            "since": since,
            "kind": kind,
        })

    def _result(self, path: Path, data: Any, syntax_error: Optional[str] = None,
                line: Optional[int] = None, ha_rules: bool = False) -> dict:
        def fmt(f):
            where = f"Line {f['line']}: " if f["line"] else ""
            at = f"{f['path']}: " if f["path"] else ""
            since = f" [HA {f['since']}]" if f.get("since") else ""
            return f"{where}{at}{f['message']}{since}"

        version = installed_version(path) if self.ha_version == "auto" else self.ha_version
        running = parse_version(version)
        for f in self.findings:
            since = parse_version(f.get("since"))
            f["upcoming"] = bool(running and since and since > running)

        self.findings.sort(key=lambda f: (f["line"] or 0))
        current = [f for f in self.findings if not f["upcoming"]]
        errors = [fmt(f) for f in current if f["level"] == "error"]
        warnings = [fmt(f) for f in current if f["level"] == "warning"]
        info = [fmt(f) for f in current if f["level"] == "info"]
        upcoming = [fmt(f) for f in self.findings if f["upcoming"] and f["level"] != "info"]
        result = {
            "file": str(path),
            "ha_rules": ha_rules,
            "ha_version": version,
            "errors": errors,
            "warnings": warnings,
            "info": info,
            "upcoming": upcoming,
            "findings": self.findings,
        }
        note = rules_note(version)
        if note:
            result["note"] = note
        if syntax_error:
            result.update({"valid": False, "error": "YAML syntax error", "details": syntax_error, "line": line})
            return result
        valid = not errors and not (self.strict and warnings)
        result["valid"] = valid
        if isinstance(data, dict):
            result["keys"] = [str(k) for k in data.keys()]
        result["dashboard"] = is_dashboard_data(data)
        return result

    def _check_bool_lines(self, content: str):
        for i, line in enumerate(content.splitlines(), 1):
            m = BOOL_LINE.match(line)
            if m:
                key, value = m.group(1), m.group(2)
                self._add("warning", i, key,
                          f"Unquoted {value} is read as a boolean, not the string \"{value}\". Quote it: \"{value.lower()}\"")

    def _check_template_text(self, content: str):
        for i, line in enumerate(content.splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            if "relative_time" in line:
                self._add("info", i, "", "relative_time is deprecated; use time_since()", None)
            if re.search(r"state_attr\([^)]*['\"]friendly_name['\"]", line) or re.search(r"\.attributes\.friendly_name", line):
                self._add("info", i, "", "friendly_name in templates is planned for deprecation; use entity_name(), device_name() or area_name()", "2026.11")

    # ---------------------------------------------------------------- walk
    def _visit(self, node: Any, path: str, ancestors: Sequence[str]):
        if isinstance(node, dict):
            self._check_dict(node, path, ancestors)
            for key, value in node.items():
                child = f"{path}.{key}" if path else str(key)
                self._visit(value, child, tuple(ancestors) + (str(key),))
        elif isinstance(node, list):
            for i, item in enumerate(node):
                self._visit(item, f"{path}[{i}]", ancestors)

    def _check_dict(self, d: dict, path: str, ancestors: Sequence[str]):
        parent = ancestors[-1] if ancestors else None
        line = line_of(d)

        # --- automation-like blocks: mixed and singular keys
        has_trigger_list = isinstance(d.get("trigger"), list) or isinstance(d.get("triggers"), list)
        if has_trigger_list and parent not in TRIGGER_LIST_KEYS:
            for old, new in (("trigger", "triggers"), ("condition", "conditions"), ("action", "actions")):
                if old in d and new in d:
                    self._add("error", line, path, f"Both '{old}' and '{new}' in the same block; keep only '{new}'", "2024.10")
                elif old in d and (old != "action" or isinstance(d[old], list)) and (old != "condition" or isinstance(d[old], list)):
                    self._add("info", line, path, f"'{old}:' still works, but the current key is '{new}:'", "2024.10")

        # --- trigger items
        if parent in TRIGGER_LIST_KEYS and ("platform" in d or "trigger" in d):
            self._check_trigger(d, path, line)

        # --- condition items
        if isinstance(d.get("condition"), str):
            self._check_condition(d, path, line)

        # --- action steps
        self._check_action_step(d, path, line)

        # --- legacy template entities (removed 2026.6). ESPHome files never get here.
        if d.get("platform") == "template" and parent in LEGACY_TEMPLATE_DOMAINS and "template" not in ancestors:
            self._add("error", line, path,
                      f"Legacy template {parent} (`platform: template` under `{parent}:`) was removed. "
                      f"Move it to `template:` > `- {parent}:` with `name`/`state` keys", "2026.6")

        # --- legacy keys inside modern template entities
        if "template" in ancestors and parent in TEMPLATE_PLATFORMS:
            for old, new in LEGACY_TEMPLATE_KEYS.items():
                if old in d:
                    self._add("error", line, path, f"'{old}' is a legacy template key; in `template:` use '{new}'", "2026.6")

        # --- MQTT entities
        if "mqtt" in ancestors and "object_id" in d:
            self._add("error", line, path, "MQTT `object_id` was removed; use `default_entity_id`", "2026.4")

        # --- blueprint target selector with device filter
        if parent == "target" and len(ancestors) >= 2 and ancestors[-2] == "selector" and "device" in d:
            self._add("error", line, path, "Target selectors no longer accept a `device:` filter (validation fails)", "2026.11")

        # --- collapsed blueprint sections: inputs without a default are easy to miss
        if d.get("collapsed") is True and isinstance(d.get("input"), dict):
            for name, spec in d["input"].items():
                if isinstance(spec, dict) and "default" not in spec:
                    self._add("info", line_of(spec) or line, f"{path}.input.{name}",
                              "Input in a collapsed section has no `default`: users only see it if they "
                              "expand the section. Add a default or leave the section expanded", "2024.6")

        # --- legacy device tracker platforms
        if parent == "device_tracker" and isinstance(d.get("platform"), str):
            self._add("info", line, path,
                      f"Legacy device_tracker platform '{d['platform']}': the legacy API is removed in 2027.5", "2026.4")

        # --- entity id format
        eid = d.get("entity_id")
        for value in (eid if isinstance(eid, list) else [eid]):
            if isinstance(value, str) and not isinstance(value, HATag) and not _is_template(value):
                if value not in ("all", "none") and not ENTITY_ID.match(value) and not REGISTRY_ID.match(value):
                    self._add("warning", line, f"{path}.entity_id", f"'{value}' is not a valid entity_id (domain.object_id, lowercase)")

    def _check_trigger(self, d: dict, path: str, line: int):
        if "platform" in d and "trigger" in d:
            self._add("error", line, path, "Trigger has both 'platform' and 'trigger'; keep only 'trigger'", "2024.10")
        elif "platform" in d:
            self._add("info", line, path, f"`platform: {d['platform']}` still works, but the current key is `trigger: {d['platform']}`", "2024.10")
        kind = d.get("trigger") or d.get("platform")
        if not isinstance(kind, str):
            return
        if kind in REMOVED_TRIGGERS:
            new, since = REMOVED_TRIGGERS[kind]
            self._add("error", line, path, f"Trigger '{kind}' no longer exists; use '{new}'", since)
        options = d.get("options") if isinstance(d.get("options"), dict) else {}
        if "." in kind:
            # purpose-specific trigger: target top-level, settings under options
            for key in ("behavior", "for", "threshold", "offset"):
                if key in d and key not in options:
                    self._add("warning", line, path,
                              f"In purpose-specific triggers `{key}` goes under `options:`", "2026.7")
            if "entity_id" in d and "target" not in d:
                self._add("warning", line, path, "Purpose-specific triggers take `target:` (entity_id/area_id/...), not a bare entity_id", "2026.7")
            behavior = options.get("behavior")
            if kind.startswith("zone.") and behavior in ZONE_BEHAVIOR_RENAMES:
                self._add("error", line, path,
                          f"Zone behavior '{behavior}' was renamed to '{ZONE_BEHAVIOR_RENAMES[behavior]}'", "2026.6")
            if (kind.startswith("sun.") or kind in ("calendar.event_started", "calendar.event_ended")) \
                    and "offset" in options and "offset_type" not in options:
                self._add("warning", line, path,
                          "Offset without `offset_type`: from 2026.11 the sign decides (negative = before, "
                          "positive = after). Check the sign or set `offset_type` explicitly", "2026.11")

    def _check_condition(self, d: dict, path: str, line: int):
        kind = d.get("condition")
        if kind in REMOVED_CONDITIONS:
            new, since = REMOVED_CONDITIONS[kind]
            self._add("error", line, path, f"Condition '{kind}' no longer exists; use '{new}'", since)
        if kind == "state" and "for" in d:
            if "attribute" in d:
                self._add("error", line, path, "State condition with both `for` and `attribute` fails validation", "2026.10")
            state = d.get("state")
            if isinstance(state, str) and ENTITY_ID.match(state) and state.split(".")[0] in ENTITY_STATE_DOMAINS:
                self._add("error", line, path, "State condition with `for` and a state taken from another entity fails validation", "2026.10")
        if isinstance(kind, str) and kind.startswith("zone.") and isinstance(d.get("options"), dict):
            behavior = d["options"].get("behavior")
            if behavior in ZONE_BEHAVIOR_RENAMES:
                self._add("error", line, path,
                          f"Zone behavior '{behavior}' was renamed to '{ZONE_BEHAVIOR_RENAMES[behavior]}'", "2026.6")

    def _check_action_step(self, d: dict, path: str, line: int):
        service = d.get("service")
        action = d.get("action")
        is_old = isinstance(service, str) and (ACTION_ID.match(service) or _is_template(service))
        is_new = isinstance(action, str) and (ACTION_ID.match(action) or _is_template(action))
        if is_old and is_new:
            self._add("error", line, path, "Step has both 'service' and 'action'; keep only 'action'", "2024.8")
        elif is_old:
            self._add("info", line, path, f"`service: {service}` still works, but the current key is `action:`", "2024.8")
        if "service_template" in d:
            self._add("warning", line, path, "`service_template` is long deprecated; use `action:` (templates are allowed there)")
        if "data_template" in d:
            self._add("warning", line, path, "`data_template` is long deprecated; use `data:` (templates are allowed there)")
        if not (is_old or is_new):
            return
        name = str(action if is_new else service)
        data = d.get("data") if isinstance(d.get("data"), dict) else {}
        if isinstance(d.get("data_template"), dict):
            data = {**d["data_template"], **data}
        if name.startswith("light."):
            for key in ("color_temp", "kelvin"):
                if key in data:
                    self._add("error", line_of(data) or line, f"{path}.data.{key}",
                              f"`{key}` is no longer supported for lights; use `color_temp_kelvin`", "2026.3")
        if name == "mqtt.publish":
            for key in ("topic_template", "payload_template"):
                if key in data:
                    self._add("error", line_of(data) or line, f"{path}.data.{key}",
                              f"`{key}` was removed; use `{key.replace('_template', '')}` (templates allowed)", "2025.2")
        if name.startswith("hassio.") and not d.get("continue_on_error"):
            self._add("info", line, path,
                      "Supervisor actions raise on failure since 2026.5; add `continue_on_error: true` if the script should go on", "2026.5")

    def _check_root(self, data: dict, path: Path):
        if "http" in data and path.name == "configuration.yaml":
            self._add("warning", line_of(data.get("http")) or 1, "http",
                      "`http:` is imported into the UI once (Settings > System > Network); later YAML edits are ignored. "
                      "Remove the block after the import", "2026.8")
        lovelace = data.get("lovelace")
        if isinstance(lovelace, dict) and lovelace.get("mode") == "yaml":
            self._add("warning", line_of(lovelace), "lovelace.mode",
                      "Top-level `lovelace: mode: yaml` is deprecated. Use `resource_mode: yaml` plus "
                      "`dashboards: lovelace: {mode: yaml, filename: ui-lovelace.yaml}`", "2026.2")
        notify = data.get("notify")
        for item in notify if isinstance(notify, list) else []:
            if isinstance(item, dict) and item.get("platform") == "telegram":
                self._add("warning", line_of(item), "notify", "`platform: telegram` notify is removed; use the Telegram bot notify entities", "2026.11")


CARD_HINTS = {"cards", "card", "entity", "entities", "tap_action", "features", "badges", "sections"}


def is_dashboard_data(data: Any) -> bool:
    """A dashboard, a view, a card, or a list of cards (snippets people keep in /config)."""
    if isinstance(data, dict):
        if "views" in data:
            return True
        return isinstance(data.get("type"), str) and bool(CARD_HINTS & set(map(str, data.keys())))
    if isinstance(data, list) and data and all(isinstance(x, dict) for x in data):
        return all(isinstance(x.get("type"), str) and not ("triggers" in x or "trigger" in x) for x in data)
    return False


def looks_like_ha(path: Path, data: Any) -> bool:
    """Heuristic: is this file Home Assistant config (not ESPHome, CI, compose...)?"""
    parts = [p.lower() for p in Path(path).resolve().parts]
    if "esphome" in parts or "node_modules" in parts or ".github" in parts:
        return False
    if isinstance(data, dict) and ("esphome" in data or "substitutions" in data and "esphome" in str(data)):
        return False
    if is_dashboard_data(data) or (isinstance(data, dict) and "services" in data and "version" in data):
        return False  # dashboard or card (lovelace_validator.py) or docker-compose
    if "blueprints" in parts:
        return True
    if len(parts) > 1 and parts[1] in ("config", "homeassistant"):
        return True
    parent = Path(path).resolve().parent
    for _ in range(5):
        if (parent / "configuration.yaml").exists():
            return True
        if parent.parent == parent:
            break
        parent = parent.parent
    if isinstance(data, dict):
        if set(map(str, data.keys())) & HA_TOP_KEYS:
            return True
        # scripts.yaml: {script_id: {sequence: [...]}}
        if data and all(isinstance(v, dict) and "sequence" in v for v in data.values()):
            return True
    if isinstance(data, list) and data and isinstance(data[0], dict):
        first = data[0]
        if ("triggers" in first or "trigger" in first) and ("actions" in first or "action" in first):
            return True
    return False


def rules_note(version: Optional[str]) -> Optional[str]:
    """A warning when Home Assistant is newer than what these rules know about."""
    running, known = parse_version(version), parse_version(RULES_CURRENT_TO)
    if running and known and running > known:
        return (f"These rules cover Home Assistant up to {RULES_CURRENT_TO}; this install runs {version}. "
                "Changes after that are not checked: read the release notes and Settings > Repairs.")
    return None


def main(argv: List[str]) -> int:
    ensure_yaml()
    missing = require_yaml()
    if missing:
        print(json.dumps({"valid": False, "error": missing}))
        return 1
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 1
    strict = "--strict" in argv
    force = True if "--all" in argv else None
    quiet = "--quiet" in argv
    include_unloaded = "--include-unloaded" in argv
    version_arg = next((a.split("=", 1)[1] for a in argv if a.startswith("--ha-version=")), "auto")

    targets = []
    not_loaded: List[str] = []
    for a in args:
        root = find_config_root(Path(a)) if Path(a).is_dir() else None
        loaded = loaded_files(root) if root and not include_unloaded else None
        for f in iter_yaml_files(Path(a)):
            if f.name == "secrets.yaml" and Path(a).is_dir():
                continue  # a syntax error message would quote the line, value included
            if root and is_unloaded(f, root, loaded):
                not_loaded.append(str(f))
            else:
                targets.append(f)
    results = []
    for f in targets:
        r = HAYamlValidator(strict=strict, ha_rules=force, ha_version=version_arg).validate_file(str(f))
        results.append(r)

    if len(results) == 1 and Path(args[0]).is_file():
        out = results[0]
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0 if out.get("valid") else 1

    version = results[0].get("ha_version") if results else None
    summary = {
        "files": len(results),
        "ha_version": version or "unknown (no .HA_VERSION; every rule applied)",
        "rules_current_to": RULES_CURRENT_TO,
        "valid": all(r.get("valid") for r in results),
        "errors": sum(len(r.get("errors") or []) + (1 if r.get("error") else 0) for r in results),
        "warnings": sum(len(r.get("warnings") or []) for r in results),
        "info": sum(len(r.get("info") or []) for r in results),
        "upcoming": sum(len(r.get("upcoming") or []) for r in results),
    }
    if not_loaded:
        summary["not_loaded"] = {
            "count": len(not_loaded),
            "files": not_loaded[:20],
            "note": "Not loaded by configuration.yaml (no !include reaches them), so skipped. "
                    "Use --include-unloaded to check them too.",
        }
    if rules_note(version):
        summary["note"] = rules_note(version)
    shown = [r for r in results if not quiet or r.get("errors") or r.get("warnings") or r.get("info")
             or r.get("upcoming") or r.get("error")]
    for r in shown:
        r.pop("findings", None)
        r.pop("keys", None)
        r.pop("ha_version", None)
        r.pop("note", None)
    print(json.dumps({"summary": summary, "results": shown}, indent=2, ensure_ascii=False))
    return 0 if summary["valid"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
