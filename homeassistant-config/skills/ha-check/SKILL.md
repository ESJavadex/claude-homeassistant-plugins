---
name: ha-check
description: Check a Home Assistant config folder end to end — YAML syntax with HA tags, removed and deprecated syntax up to 2026.11, dashboards, missing includes, undefined secrets, duplicate ids — and HA's own config check when available. Use when the user asks to check, validate or review their configuration, or before and after a big change.
argument-hint: "[config path, default /config]"
allowed-tools: Bash(python3 *), Bash(ha core check*), Bash(ha core info*), Bash(ha core logs*), Read, Grep, Glob
---

# Check a Home Assistant configuration

Path: `$ARGUMENTS`, or `/config` if it exists, else the current folder.
Scripts live in `${CLAUDE_PLUGIN_ROOT}/skills/homeassistant-config/scripts/`.

1. Version: `cat <path>/.HA_VERSION`, and `ha core info 2>/dev/null | grep -E
   '^(version|version_latest):'` to see if an update is waiting.
2. YAML and syntax rules for every file:
   `python3 "${CLAUDE_PLUGIN_ROOT}/skills/homeassistant-config/scripts/validate_yaml.py" <path> --quiet`
3. Structure: `python3 "${CLAUDE_PLUGIN_ROOT}/skills/homeassistant-config/scripts/check_config.py" <path>`
4. Dashboards: run `lovelace_validator.py` on each YAML dashboard and on
   `<path>/.storage/lovelace` and `<path>/.storage/lovelace.*` (UI dashboards
   are stored there as JSON; `lovelace_dashboards` and `lovelace_resources`
   are lists, not dashboards, and are skipped). If reading `.storage` is
   denied by the user's permissions, skip this step and say so.
   Files like `lovelace.backup*` are copies, not live dashboards:
   `jq -r '.data.items[].url_path' <path>/.storage/lovelace_dashboards` lists
   the live ones (plus `lovelace`, the default). Report copies separately.
5. Home Assistant's own check, if available: `ha core check`.

Then report briefly:

- **Will not work** (errors), grouped by file, with line numbers and the fix.
- **Deprecated / ignored** (warnings): what breaks and when.
- **Old style, still works** (info): just a count per file, plus one line
  offering `/ha-upgrade` to modernise them.
- **Upcoming**: what will need changes when they update (if an update is waiting,
  say which release it is).
- **Not loaded**: how many files were skipped because nothing includes them
  (archive or draft folders); offer `--include-unloaded` if they want those too.
- Anything `ha core check` said that the scripts did not. If it disagrees
  with the scripts, Home Assistant is right.

Never print values from `secrets.yaml`. Do not change files in this command;
offer to fix the errors and wait for the user.
