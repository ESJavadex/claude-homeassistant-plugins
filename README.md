# Claude Home Assistant Plugins

Claude Code plugins for Home Assistant. They teach Claude the syntax Home
Assistant uses **today** (2026), check what it writes, and help migrate old
configs.

[![CI](https://github.com/ESJavadex/claude-homeassistant-plugins/actions/workflows/ci.yml/badge.svg)](https://github.com/ESJavadex/claude-homeassistant-plugins/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## Plugins

| Plugin | What it does | Version |
|--------|--------------|---------|
| [homeassistant-config](./homeassistant-config) | Write, check and modernise HA YAML: automations, scripts, templates, blueprints, dashboards | 2.1.0 |

## Install

```bash
/plugin marketplace add ESJavadex/claude-homeassistant-plugins
/plugin install homeassistant-config@claude-homeassistant-plugins
```

Already installed? Update with `/plugin marketplace update claude-homeassistant-plugins`.

Running Claude Code inside Home Assistant? The
[Claude Terminal Pro add-on](https://github.com/ESJavadex/claude-code-ha) can
ship this plugin preinstalled.

## Why

Most Home Assistant YAML on the internet is out of date, and so is a lot of
what language models learned. Since 2024 Home Assistant has:

- renamed `service:` to `action:` and `platform:` to `trigger:` (2024.8, 2024.10);
- **removed** legacy `platform: template` entities (2026.6) and light
  `color_temp`/`kelvin` (2026.3);
- added purpose-specific triggers like `light.turned_on`, renamed several of
  them (2026.5–2026.7) and changed `offset` on sun/calendar triggers (2026.11);
- made sections the default dashboard view, replaced `layout_options` with
  `grid_options` and `call-service` with `perform-action`;
- moved `http:` and many integrations from YAML to the UI.

The plugin knows all of that, writes for the version you run, and checks every
YAML file Claude edits.

## What you get

| Component | Purpose |
|-----------|---------|
| `homeassistant-config` skill | Loads automatically for HA work: current syntax, version gates, snippets, references |
| `/ha-check` | Check a config folder end to end (syntax, removed/deprecated syntax, dashboards, includes, secrets, `ha core check`) |
| `/ha-upgrade` | Plan and apply a migration to current syntax, with backups |
| `/ha-find-duplicates` | Duplicate, near-duplicate and conflicting automations/scripts |
| `ha-suggestions` agent | Suggests automations, scenes and devices from what you have |
| PostToolUse hook | Validates every YAML file right after Claude writes or edits it |
| Python checkers | `validate_yaml.py`, `lovelace_validator.py`, `check_config.py`, `find_duplicates.py` (they understand `!include`, `!secret`, `!input`) |

## Development

```bash
pip install pyyaml
python3 -m unittest discover -s homeassistant-config/tests
claude plugin validate ./homeassistant-config --strict
claude --plugin-dir ./homeassistant-config     # try it without installing
```

Pull requests are welcome. Please keep examples on current syntax: CI runs the
validators on every example with `--strict`.

## License

MIT, see [LICENSE](LICENSE).
