# Claude Home Assistant Plugins

> A curated marketplace of Claude Code plugins for Home Assistant and smart home automation.

[![Marketplace](https://img.shields.io/badge/marketplace-claude--homeassistant--plugins-blue.svg)](https://github.com/ESJavadex/claude-homeassistant-plugins)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## Available Plugins

| Plugin | Description | Version | Features |
|--------|-------------|---------|----------|
| [homeassistant-config](./homeassistant-config) | Create, validate, and manage HA configuration files | 1.4.0 | Skills, Scripts, Hooks |

## Quick Start

```bash
# 1. Add this marketplace
/plugin marketplace add ESJavadex/claude-homeassistant-plugins

# 2. Install a plugin
/plugin install homeassistant-config@claude-homeassistant-plugins
```

## What You Get

### homeassistant-config

| Component | What it does |
|-----------|--------------|
| **Skill** | Auto-activates when working with HA files |
| **Pre-save Hook** | Validates YAML before saving |
| **validate_yaml.py** | Check syntax, tabs, booleans, deprecated keys |
| **check_config.py** | Analyze config structure, entities, secrets |
| **lovelace_validator.py** | Validate dashboards (YAML & JSON) |
| **References** | Patterns, templates, blueprints, Lovelace, troubleshooting |
| **Examples** | Complete working configurations |

**Ask Claude:**
- "Create an automation for motion-activated lights"
- "Validate my configuration.yaml"
- "Build a Lovelace dashboard with Mushroom cards"
- "Why isn't my automation firing?"

## Installation Options

### Option 1: Interactive (Recommended)

```bash
/plugin marketplace add ESJavadex/claude-homeassistant-plugins
/plugin  # Browse and install
```

### Option 2: Direct Install

```bash
/plugin install homeassistant-config@claude-homeassistant-plugins
```

### Managing Plugins

| Command | Action |
|---------|--------|
| `/plugin` | Browse/manage plugins |
| `/plugin enable <name>@<marketplace>` | Enable plugin |
| `/plugin disable <name>@<marketplace>` | Disable plugin |
| `/plugin uninstall <name>@<marketplace>` | Remove plugin |

## Repository Structure

```
claude-homeassistant-plugins/
├── .claude-plugin/
│   └── marketplace.json        # Marketplace metadata
├── homeassistant-config/       # Home Assistant plugin
│   ├── .claude-plugin/
│   │   └── plugin.json         # Plugin config + hooks
│   ├── hooks/                  # Pre/post hooks
│   ├── skills/                 # SKILL.md + scripts
│   └── README.md
└── README.md
```

## Contributing

1. Fork this repository
2. Create plugin directory with `.claude-plugin/plugin.json`
3. Add `skills/<plugin-name>/SKILL.md` with YAML frontmatter
4. Include references and examples
5. Submit PR

### Plugin Requirements

- `plugin.json` with name, description, version
- `SKILL.md` with YAML frontmatter (`name`, `description`)
- Working examples
- Documentation

## Roadmap

- [ ] ESPHome configuration plugin
- [ ] MQTT device templates
- [ ] Node-RED integration patterns
- [ ] Voice assistant (Assist) configurations

## License

MIT License - See [LICENSE](LICENSE)

## Resources

| Resource | Link |
|----------|------|
| Claude Code Plugins | [code.claude.com/docs/en/plugins](https://code.claude.com/docs/en/plugins) |
| Plugin Marketplaces | [code.claude.com/docs/en/plugin-marketplaces](https://code.claude.com/docs/en/plugin-marketplaces) |
| Home Assistant | [home-assistant.io](https://www.home-assistant.io/) |
| HACS | [hacs.xyz](https://hacs.xyz/) |
