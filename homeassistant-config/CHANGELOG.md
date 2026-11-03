# Changelog

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
