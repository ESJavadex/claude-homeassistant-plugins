# Changelog

## 2.1.3 (2026-11-03)

From testers' feedback on 2.1.2 (issue #75 of claude-code-ha).

- **Credentials never reach the output.** A YAML error quotes the line it
  failed on, and ESPHome nodes keep Wi-Fi and API passwords in plain text.
  Values of keys like `password`, `api_key`, `token`, `psk` or `key`, and
  passwords in URLs (`mqtt://user:pass@host`), are now masked in every
  checker's output and in what the hook sends back to Claude. `!secret` and
  `!env_var` references are kept.
- **Backups don't end up in git.** If the config folder is a git repository,
  git is the backup: the skills check for uncommitted changes and make no
  `.bak` files, which a nightly `git add .` would commit. Otherwise copies go
  to `/config/.claude-backups/<date>/`, which the checkers skip.
- **Edit YAML with the Edit tool, never through a script.** A rewrite through
  `yaml.safe_load` + `yaml.dump` drops comments and `!include` tags, and one
  that fails halfway leaves the file empty.
- **Imported blueprints are counted, not listed.** Blueprints with a
  `source_url` are updated by re-importing them, so their old-style (info)
  items now show as a count per blueprint under `imported_blueprints` in the
  summary. Errors and warnings in them are still listed. `/ha-upgrade` leaves
  them alone unless asked and still upgrades your own blueprints.

## 2.1.2 (2026-11-03)

False positives found by running the checkers over ten large public configs
on GitHub (`tests/smoke_public_configs.sh`). Each has a regression test.

- `!include /config/...` (absolute paths) now resolves when the config folder
  is mounted elsewhere (`/homeassistant`, a git checkout). Before, those
  includes were "missing" and everything behind them looked "not loaded".
- Dashboards declared in an included `lovelace.yaml` and lovelace_gen
  includes (`!include [file, {vars}]`) count as loaded.
- `<<: !include common.yaml` (ESPHome packages) no longer reads as a syntax error.
- Integration triggers that take a bare `entity_id` (`webostv.turn_on`,
  `samsungtv.turn_on`, `philips_js.turn_on`, `lg_netcast.turn_on`) are not
  purpose-specific triggers.
- `state: on` inside a scene is fine (scenes turn booleans into on/off); the
  warning stays for triggers and conditions.
- Entity IDs: uppercase is accepted (Home Assistant lowercases them), and
  button-card JavaScript (`[[[ ]]]`) and wildcards (`light.*`) are skipped.
- lovelace_gen files (`# lovelace_gen`, Jinja) are skipped: not YAML until rendered.
- No `secrets.yaml` at all: one issue instead of one per file.
- Duplicates: blueprint automations compare by blueprint and inputs (they all
  looked identical), scripts with the same sequence but different
  `variables` are not duplicates, and trigger-based template entities are not
  automations.

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
