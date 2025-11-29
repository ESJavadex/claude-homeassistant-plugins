# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Claude Code Plugin Marketplace containing plugins for Home Assistant, ESPHome, and smart home automation. Currently includes the `homeassistant-config` plugin for managing Home Assistant YAML configuration files.

## What are Plugins and Skills?

### Plugins
Plugins are a lightweight way to extend Claude Code with custom functionality. A plugin can include any combination of:
- **Slash commands**: Custom shortcuts (e.g., `/ha-validate`)
- **Subagents**: Purpose-built agents for specialized tasks
- **MCP servers**: Connect to external tools via Model Context Protocol
- **Hooks**: Customize behavior at key points in Claude's workflow
- **Skills**: Automatic capabilities activated based on context

### Skills (Agent Skills)
Skills are defined in `SKILL.md` files and teach Claude **when** and **how** to use the plugin automatically. Unlike slash commands which require explicit invocation, skills are activated based on conversation context.

A `SKILL.md` file contains:
- **Triggers**: When Claude should activate this skill (file patterns, keywords, task types)
- **Instructions**: Domain-specific knowledge and best practices
- **References**: Links to detailed guides in `references/` directory
- **Examples**: Working configurations in `examples/` directory

Example: When a user opens a `configuration.yaml` file, Claude automatically activates the Home Assistant skill and applies HA-specific knowledge.

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
/plugin marketplace add ESJavadex/claude-homeassistant-plugins

# Browse and install interactively
/plugin

# Or install directly
/plugin install homeassistant-config@claude-homeassistant-plugins
```
