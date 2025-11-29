# Home Assistant Config Plugin

> Claude Code plugin for creating, validating, and managing Home Assistant configuration files.

[![Version](https://img.shields.io/badge/version-1.4.0-blue.svg)](https://github.com/ESJavadex/claude-homeassistant-plugins)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](../LICENSE)

## Features

| Feature | Description |
|---------|-------------|
| **Auto-Validation** | Pre-save hook validates YAML syntax before writing |
| **Validation Scripts** | CLI tools for YAML, config structure, and Lovelace dashboards |
| **2024+ Syntax** | Uses modern HA syntax (`action:` not `service:`, `triggers:` not `trigger:`) |
| **Comprehensive References** | Patterns, templates, blueprints, Lovelace, troubleshooting guides |
| **Working Examples** | Complete automation, script, dashboard, and template examples |

## Installation

```bash
# Add marketplace
/plugin marketplace add ESJavadex/claude-homeassistant-plugins

# Install plugin
/plugin install homeassistant-config@claude-homeassistant-plugins
```

## What's Included

### Validation Scripts

| Script | Usage |
|--------|-------|
| `validate_yaml.py` | `python3 {baseDir}/scripts/validate_yaml.py config.yaml [--strict]` |
| `check_config.py` | `python3 {baseDir}/scripts/check_config.py /config [--verbose]` |
| `lovelace_validator.py` | `python3 {baseDir}/scripts/lovelace_validator.py dashboard.yaml` |

**validate_yaml.py** - YAML Validator
- Syntax error detection with line numbers
- Tab character detection (HA requires spaces)
- Unquoted boolean warnings (`on`, `off`, `yes`, `no`)
- Deprecated syntax detection (`service:` → `action:`)
- Entity ID format validation

**check_config.py** - Configuration Analyzer
- Scans entire config directories
- Finds entities across all domains
- Tracks `!include` and `!secret` references
- Reports missing aliases/IDs in automations
- Suggests best practices

**lovelace_validator.py** - Dashboard Validator
- Supports YAML (`ui-lovelace.yaml`) and JSON (`.storage/lovelace`)
- Validates 30+ built-in card types
- Recognizes 25+ HACS custom cards (Mushroom, button-card, etc.)
- Checks entity ID formats
- Validates actions (`tap_action`, `hold_action`)

### Pre-Save Hook

Automatically validates YAML files before `Write` or `Edit` operations:
- Blocks saves with tab characters
- Blocks saves with YAML syntax errors
- Only affects `.yaml` and `.yml` files

### Reference Guides

| File | Content |
|------|---------|
| `patterns.md` | Common automation patterns (motion lights, presence, notifications) |
| `templates.md` | Jinja2 template sensors and examples |
| `blueprints.md` | Blueprint creation and usage |
| `lovelace.md` | Dashboard cards, layouts, custom cards |
| `troubleshooting.md` | Common errors and solutions |
| `best-practices.md` | Performance, organization, maintenance |

### Example Configurations

| File | Description |
|------|-------------|
| `configuration.yaml` | Base configuration with includes |
| `automations.yaml` | Motion, presence, climate, notification automations |
| `scripts.yaml` | Parameterized scripts with sequences |
| `templates.yaml` | Template sensors for energy, occupancy, etc. |
| `secrets.yaml` | Secrets file structure |
| `lovelace-dashboard.yaml` | Complete dashboard with multiple views |
| `lovelace-custom-cards.yaml` | Mushroom, button-card, and other HACS cards |

## Directory Structure

```
homeassistant-config/
├── .claude-plugin/
│   └── plugin.json              # Plugin metadata + hooks config
├── hooks/
│   └── validate-before-save.sh  # Pre-save YAML validation
├── skills/
│   └── homeassistant-config/
│       ├── SKILL.md             # Core skill instructions
│       ├── scripts/
│       │   ├── validate_yaml.py
│       │   ├── check_config.py
│       │   └── lovelace_validator.py
│       ├── references/
│       │   ├── patterns.md
│       │   ├── templates.md
│       │   ├── blueprints.md
│       │   ├── lovelace.md
│       │   ├── troubleshooting.md
│       │   └── best-practices.md
│       └── examples/
│           ├── configuration.yaml
│           ├── automations.yaml
│           ├── scripts.yaml
│           ├── templates.yaml
│           ├── secrets.yaml
│           ├── lovelace-dashboard.yaml
│           └── lovelace-custom-cards.yaml
└── README.md
```

## Usage Examples

Once installed, Claude automatically activates this skill when you work with Home Assistant files.

**Ask Claude:**
```
"Create an automation that turns on lights when motion is detected after sunset"

"Validate my configuration.yaml for errors"

"Help me create a Lovelace dashboard with Mushroom cards"

"Convert this automation to a blueprint"

"Why isn't my automation firing?"

"Create a template sensor that calculates daily energy cost"
```

## Requirements

- Python 3.8+ (for validation scripts)
- PyYAML (`pip install pyyaml`)

## Changelog

### v1.4.0
- Added pre-save YAML validation hook
- Added Lovelace dashboard validator
- Supports both YAML and JSON `.storage/lovelace` format

### v1.3.0
- Added validation scripts (`validate_yaml.py`, `check_config.py`)
- Scripts use `{baseDir}` for portability

### v1.2.4
- Added YAML frontmatter to SKILL.md for proper skill detection

### v1.2.0
- Initial release with skill, references, and examples

## License

MIT License - See [LICENSE](../LICENSE) for details.

## Links

- [Home Assistant](https://www.home-assistant.io/)
- [HA Automation Docs](https://www.home-assistant.io/docs/automation/)
- [Lovelace Dashboards](https://www.home-assistant.io/dashboards/)
- [HACS](https://hacs.xyz/)
