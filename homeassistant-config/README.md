# Home Assistant Config Plugin

> Claude Code plugin for creating, validating, and managing Home Assistant configuration files.

[![Version](https://img.shields.io/badge/version-1.5.0-blue.svg)](https://github.com/ESJavadex/claude-homeassistant-plugins)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](../LICENSE)

## Features

| Feature | Description |
|---------|-------------|
| **Auto-Validation** | Pre-save hook validates YAML syntax before writing |
| **Validation Scripts** | CLI tools for YAML, config structure, Lovelace, and duplicate detection |
| **Slash Commands** | `/ha-find-duplicates` for finding duplicate automations/scripts |
| **Subagents** | `ha-suggestions` smart home improvement advisor |
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
| `find_duplicates.py` | `python3 {baseDir}/scripts/find_duplicates.py /config [--verbose]` |

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

**find_duplicates.py** - Duplicate Finder
- Finds exact duplicate automations and scripts
- Detects similar items (80%+ similarity threshold)
- Identifies trigger conflicts (same trigger, different automations)
- Reports entity overlap between automations

### Slash Commands

| Command | Description |
|---------|-------------|
| `/ha-find-duplicates [path]` | Find duplicate automations and scripts |

### Subagents

| Agent | Description |
|-------|-------------|
| `ha-suggestions` | Smart home improvement advisor |

**ha-suggestions** - Proactive smart home consultant that:
- Analyzes your HA configuration files automatically
- Suggests new automations (motion, presence, schedules, energy)
- Recommends scenes (movie night, morning, bedtime)
- Proposes device purchases to enhance your setup
- Identifies optimization opportunities in existing automations
- Generates ready-to-use YAML code

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
│   └── plugin.json              # Plugin metadata + hooks + agents config
├── agents/
│   └── ha-suggestions.md        # Smart home improvement advisor subagent
├── commands/
│   └── ha-find-duplicates.md    # Find duplicate automations/scripts
├── hooks/
│   └── validate-before-save.sh  # Pre-save YAML validation
├── skills/
│   └── homeassistant-config/
│       ├── SKILL.md             # Core skill instructions
│       ├── scripts/
│       │   ├── validate_yaml.py
│       │   ├── check_config.py
│       │   ├── lovelace_validator.py
│       │   └── find_duplicates.py
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

### v1.5.0
- Added `/ha-find-duplicates` slash command
- Added `find_duplicates.py` script for detecting duplicate automations/scripts
- Added `ha-suggestions` subagent for smart home improvement recommendations
- Detects exact duplicates, similar items, and trigger conflicts

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
