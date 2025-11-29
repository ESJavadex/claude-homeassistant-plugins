# Home Assistant Configuration Skill

A skill for creating and managing Home Assistant configuration files with proper YAML syntax, automations, scripts, and templates.

## Contents

- **SKILL.md** - Core instructions and quick reference
- **references/** - Detailed guides loaded as needed
  - patterns.md - Common automation patterns
  - templates.md - Template sensor examples
  - troubleshooting.md - Error solutions
  - best-practices.md - Optimization and maintenance
- **examples/** - Complete working configuration files

## Usage

Claude will automatically load this skill when you ask about Home Assistant configuration, automations, scripts, or YAML syntax. The skill uses progressive disclosure: core instructions are always available, detailed references are loaded only when needed.

## Features

- YAML syntax validation and best practices
- Automation creation with triggers, conditions, and actions
- Script development with parameters and sequences
- Template sensors using Jinja2
- Secrets management for sensitive data
- File organization and includes

## Installation

```bash
claude install homeassistant-config
```

## Examples

Ask Claude things like:
- "Create an automation to turn on lights when motion is detected"
- "Help me set up a template sensor for energy usage"
- "Fix the YAML syntax error in my configuration"
- "Create a script to control my climate system"
