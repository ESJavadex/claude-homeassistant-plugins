# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Claude Code Plugin Marketplace containing plugins for Home Assistant, ESPHome, and smart home automation. Currently includes the `homeassistant-config` plugin for managing Home Assistant YAML configuration files.

## Repository Structure

```
plugin-name/
├── .claude-plugin/
│   └── plugin.json          # Plugin metadata (name, version, description)
├── skills/
│   └── plugin-name/
│       ├── SKILL.md         # Core instructions loaded by Claude
│       ├── references/      # Detailed guides (patterns, templates, troubleshooting)
│       └── examples/        # Working example configurations
└── README.md                # Plugin documentation
```

## Version Management

After every commit, bump the version in the plugin's `plugin.json` file following semantic versioning:
- **patch** (1.0.0 → 1.0.1): Bug fixes, documentation updates
- **minor** (1.0.0 → 1.1.0): New features, new reference files
- **major** (1.0.0 → 2.0.0): Breaking changes to plugin structure

## Adding a New Plugin

1. Create directory: `new-plugin-name/`
2. Add plugin metadata: `.claude-plugin/plugin.json`
3. Create skill file: `skills/new-plugin-name/SKILL.md`
4. Add references in `references/` and examples in `examples/`
5. Update root `README.md` plugins table
6. Bump version in `plugin.json`

## Plugin Installation (for users)

```bash
# Add marketplace
claude mcp add-json claude-plugins '{"type":"url","url":"https://raw.githubusercontent.com/USER/claude-homeassistant-plugins/main/.claude-plugin/plugin.json"}'

# Install plugin
claude install homeassistant-config
```
