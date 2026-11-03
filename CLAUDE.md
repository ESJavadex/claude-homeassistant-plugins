# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Claude Code Plugin Marketplace containing plugins for Home Assistant, ESPHome, and smart home automation. Currently includes the `homeassistant-config` plugin for managing Home Assistant YAML configuration files.

## What are Plugins and Skills?

### Plugins
Plugins are a lightweight way to extend Claude Code with custom functionality. A plugin can include any combination of:
- **Skills with slash commands**: e.g. `/ha-check` (commands/ and skills/ are merged; use skills)
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
.claude-plugin/marketplace.json      # marketplace (name, owner, plugin list + versions)
homeassistant-config/
├── .claude-plugin/plugin.json       # manifest (components are auto-discovered)
├── .claude-plugin/icon.png
├── hooks/hooks.json                 # PostToolUse Write|Edit -> validate_ha_yaml.py
├── hooks/validate_ha_yaml.py        # reads the hook event from stdin
├── agents/ha-suggestions.md
├── skills/homeassistant-config/     # main skill: SKILL.md, references/, examples/, scripts/
├── skills/ha-check/ ha-upgrade/ ha-find-duplicates/   # slash commands (skills)
└── tests/                           # unittest + fixtures
```

- Scripts share `scripts/ha_yaml.py` (HA-tag aware loader). Never use plain
  `yaml.safe_load` on HA files: it rejects `!include`/`!secret`/`!input`.
- In skill bodies use `${CLAUDE_SKILL_DIR}` (same skill) or
  `${CLAUDE_PLUGIN_ROOT}` (other skills/hooks) for script paths.
- Hooks get their input as JSON on stdin; there is no `$CLAUDE_TOOL_INPUT`.

## Keeping it current

Home Assistant ships monthly. When a release changes YAML:
1. Add or adjust the rule in `scripts/validate_yaml.py` (or
   `lovelace_validator.py`) with the `since` version, plus a fixture/test.
2. Update the "Outdated → current" table of the affected reference and, if it
   is a common case, the table in `SKILL.md`.
3. Bump the version in `plugin.json` **and** `marketplace.json`, add a
   CHANGELOG entry.

## Checks before committing

```bash
python3 -m unittest discover -s homeassistant-config/tests
claude plugin validate . && claude plugin validate ./homeassistant-config --strict
```

This repo is public: examples and fixtures use made-up entity IDs, never
anyone's real config, hostnames, IPs, tokens or names.

## Version Management

Semantic versioning, in `plugin.json` and `marketplace.json`:
- **patch**: fixes, doc updates
- **minor**: new rules, references, commands
- **major**: breaking changes to plugin structure

## Adding a New Plugin

1. Create directory: `new-plugin-name/`
2. Add plugin metadata: `.claude-plugin/plugin.json`
3. Create skill file: `skills/new-plugin-name/SKILL.md`
4. Add references in `references/` and examples in `examples/`
5. Add it to `.claude-plugin/marketplace.json` and the root `README.md` table
6. Run `claude plugin validate`

## Plugin Installation (for users)

```bash
# Add marketplace
/plugin marketplace add ESJavadex/claude-homeassistant-plugins

# Browse and install interactively
/plugin

# Or install directly
/plugin install homeassistant-config@claude-homeassistant-plugins
```
