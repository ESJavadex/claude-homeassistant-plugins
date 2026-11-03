# Changelog

## 2.1.1 (2026-11-03)

- The PyYAML fallback now works with a real venv. A venv's `python3` is a
  symlink to the system Python, and 2.1.0 skipped it as "the same
  interpreter", although outside the venv it sees PyYAML. Found by testing on
  a real install; the test now builds a venv.

## 2.1.0 (2026-11-03)

From the first round of feedback on real installs (thanks @nsleigh and
@satscan1 in ESJavadex/claude-code-ha#75).

### The hook
- **No more silent skip without PyYAML.** When `python3` is a venv without
  PyYAML (the add-on's persistent packages make one), the hook and the scripts
  re-run themselves with the system Python. If no Python has PyYAML, the hook
  says the check was skipped instead of passing in silence.
- **Only a broken file blocks**: YAML syntax errors, tabs, duplicate keys.
  Home Assistant rules (removed or deprecated syntax) come back as advice, so a
  stale or wrong rule costs a sentence, never a forced edit.
- The advice ends with "if `ha core check` or Repairs disagree, they are right".

### Version-aware rules
- Rules are compared with the installed release (`.HA_VERSION` in the config
  folder, or `HA_VERSION`). A rule from a newer release is reported as
  **upcoming** ("fine now, changes when you update"), not as an error.
- `--ha-version=X` previews another release: `/ha-upgrade` uses it with
  `version_latest` to list what an update will break before you install it.
- When Home Assistant is newer than the rules (2026.11), the checkers say so.

### Fewer false positives
- Files that `configuration.yaml` never loads (archive or draft folders, card
  snippets, add-on repos) are skipped and counted under `not_loaded`;
  `--include-unloaded` checks them too. Applies to `validate_yaml.py`,
  `check_config.py` and `find_duplicates.py`.
- `!secret` is resolved like Home Assistant does (next to the file, then each
  parent folder), so ESPHome files use `esphome/secrets.yaml`.
- `!include` and `!secret` are read from the parsed YAML: commented-out lines
  no longer count.
- Duplicate automation IDs name the full relative path (two `automations.yaml`
  in different folders were indistinguishable).
- Entity registry IDs (32 hex characters, written by the UI editor in device
  triggers and actions) are valid entity references.
- Custom cards (`custom:*`) keep their own options: `features:` and
  `entity: ''` are no longer checked as built-in card syntax. Cards nested
  inside them still are.
- `.storage/lovelace_dashboards` and `lovelace_resources` are skipped (they
  list dashboards, they are not dashboards).
- Blueprint inputs without a `default` in a collapsed section: info, not error.
- `validate_yaml.py` on a folder never opens `secrets.yaml` (a syntax error
  message would quote the line, value included).

### Guidance
- If a Home Assistant MCP server is connected (the MCP Server integration or
  ha-mcp), the skill and the `ha-suggestions` agent use it for entity IDs,
  states and Repairs instead of `curl`.

## 2.0.1 (2026-11-03)

- Dashboard and card snippets kept as YAML files in the config folder (a
  `type:` with `cards:`, `entity:`... or a list of cards) are now checked with
  the dashboard rules, not as automations. A card `tap_action` with
  `action: call-service` + `service:` was reported as "Step has both 'service'
  and 'action'". Found on a real install.
- Mixing `service:` and `action:` is only an error when both name an action.

## 2.0.0 (2026-11-03)

Updated for Home Assistant 2026 (rules up to 2026.11) and the current Claude
Code plugin format.

### Home Assistant knowledge
- Skill rewritten around current syntax, with a table of what each release
  changed and version gates (purpose-specific triggers need 2026.7,
  `target: exclude` and blueprint `visible:` need 2026.11).
- New: purpose-specific triggers and conditions, including the 2026.5–2026.7
  renames and the 2026.11 `offset` sign change on sun/calendar triggers.
- Template entities: modern `template:` format only (legacy removed in 2026.6),
  migration table, new functions up to 2026.10, `entity_name()` instead of
  `friendly_name`.
- Dashboards: sections view as default, `grid_options`, badges, heading card,
  every tile feature, visibility conditions, `perform-action`, naming objects,
  strategies, new YAML-mode dashboard config.
- Lights: `color_temp_kelvin` everywhere (`color_temp`/`kelvin` removed in 2026.3).
- New reference `ai-and-assist.md`: `ai_task`, Assist satellites, MCP.
- Config notes for 2026: `http:` moved to the UI, no `home-assistant.log` on HA
  OS, `ha apps` instead of `ha addons`, Supervisor actions raising on failure.

### Checkers
- New shared loader (`ha_yaml.py`): all scripts now parse `!include`,
  `!secret`, `!input` and ESPHome tags. Before, every real
  `configuration.yaml` was reported as a syntax error.
- `validate_yaml.py`: context-aware rules with error/warning/info levels and
  the release of each change; duplicate keys; folder mode. It no longer warns
  about the correct `action:` and `trigger:` keys.
- `lovelace_validator.py`: current card and tile feature lists, sections,
  badges, deprecated dashboard options.
- `check_config.py`: reads `automations.yaml`/`scripts.yaml`, reports missing
  includes, undefined secrets (names only) and duplicate automation ids.
- `find_duplicates.py`: old and new syntax compare equal, action names no
  longer count as shared entities, near duplicates are clustered, similarity
  scores fixed (they could exceed 100 %).

### Plugin
- Hook rewritten: it read `$CLAUDE_TOOL_INPUT`, which does not exist, so it
  never validated anything. Now a PostToolUse hook reads the event from stdin
  and checks the whole file after Write/Edit.
- Commands are skills now: `/ha-find-duplicates`, plus new `/ha-check` and
  `/ha-upgrade`. Script paths use `${CLAUDE_PLUGIN_ROOT}` / `${CLAUDE_SKILL_DIR}`,
  which fixes "file not found" when running the scripts.
- Tests (unittest) and CI, including `claude plugin validate --strict`.

## 1.5.2 (2025-11-29)
- `ha-suggestions` agent loads the skill.

## 1.5.0 (2025-11-29)
- `/ha-find-duplicates` command and `ha-suggestions` agent.
