# homeassistant-config

Claude Code plugin to write, check and modernise Home Assistant YAML with the
syntax of Home Assistant 2026 (rules up to 2026.11).

## Install

```bash
/plugin marketplace add ESJavadex/claude-homeassistant-plugins
/plugin install homeassistant-config@claude-homeassistant-plugins
```

Requirements: `python3` with PyYAML (`pip install pyyaml`, or `apk add py3-yaml`
on Alpine / Home Assistant add-ons). Without PyYAML the hook stays silent and the
scripts tell you what to install.

## Components

### Skill: `homeassistant-config`

Loads automatically when Claude works on Home Assistant config. It covers:

- the current syntax and what each release changed (2024.8 → 2026.11);
- version gates, so Claude doesn't write 2026.11 features for a 2025 install;
- how to find entity IDs, check the config with `ha core check` and reload
  without a restart from the Claude Terminal add-on;
- references for automation patterns, purpose-specific triggers, template
  entities, blueprints, dashboards (sections, tile features, badges,
  visibility, strategies), AI tasks and Assist, best practices and
  troubleshooting;
- complete example files.

### Commands

| Command | What it does |
|---------|--------------|
| `/ha-check [path]` | Full check: YAML with HA tags, removed/deprecated syntax, dashboards, missing includes, undefined secrets, duplicate ids, plus `ha core check` |
| `/ha-upgrade [path]` | Finds outdated syntax, proposes a plan by risk level, backs up and migrates the files you approve |
| `/ha-find-duplicates [path]` | Exact duplicates, near-duplicate groups (e.g. ten room scripts that could be one with `fields:`) and trigger conflicts |

### Agent: `ha-suggestions`

Reads your entities, areas and automations and suggests new automations,
scenes and devices, with ready-to-use YAML. It only reports; nothing is
written until you pick.

### Hook: YAML check after every edit

After Claude writes or edits a `.yaml` file, `hooks/validate_ha_yaml.py`
validates the whole file on disk:

- **errors** (syntax, tabs, duplicate keys, removed syntax) are sent back to
  Claude, which fixes them in the same turn;
- **warnings** (deprecated or ignored syntax) are passed to Claude as context;
- old-but-working syntax (`service:`, `platform:`) is not reported, so Claude
  doesn't rewrite your files uninvited.

Home Assistant rules only apply to files that look like HA config. ESPHome
files (which use `platform: template` legitimately), CI workflows and
docker-compose files only get the syntax check.

### Scripts

All of them parse Home Assistant tags (`!include*`, `!secret`, `!input`,
`!env_var`, ESPHome's `!lambda`), and print JSON.

| Script | Checks |
|--------|--------|
| `validate_yaml.py <file-or-dir> [--strict] [--quiet] [--all]` | syntax, tabs, duplicate keys, 30+ rules for removed/deprecated/old syntax, each tagged with the release |
| `lovelace_validator.py <file> [--strict]` | dashboards in YAML or `.storage/lovelace*`: card types, tile features, actions, sections, badges, deprecated options |
| `check_config.py <dir> [--verbose]` | domains, missing `!include` files, undefined `!secret` names (never values), duplicate automation ids |
| `find_duplicates.py <dir> [--verbose]` | exact and near duplicates, clustered; old and new syntax compare equal |

Levels: **error** = will not work on current HA, **warning** = deprecated or
ignored, **info** = old style that still works.

## Examples of what it catches

```text
error   Legacy template sensor (`platform: template` under `sensor:`) was removed [HA 2026.6]
error   `color_temp` is no longer supported for lights; use `color_temp_kelvin` [HA 2026.3]
error   Trigger 'battery.low' no longer exists; use 'battery.became_low' [HA 2026.7]
error   Both 'trigger' and 'triggers' in the same block; keep only 'triggers' [HA 2024.10]
warning `http:` is imported into the UI once; later YAML edits are ignored [HA 2026.8]
warning Offset without `offset_type`: from 2026.11 the sign decides [HA 2026.11]
warning Unquoted on is read as a boolean, not the string "on"
info    `service: light.turn_on` still works, but the current key is `action:` [HA 2024.8]
```

## Development

```bash
python3 -m unittest discover -s homeassistant-config/tests
claude plugin validate ./homeassistant-config --strict
claude --plugin-dir ./homeassistant-config
```

See [CHANGELOG.md](CHANGELOG.md).
