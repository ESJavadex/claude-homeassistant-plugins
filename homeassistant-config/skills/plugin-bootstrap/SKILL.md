---
name: plugin-bootstrap
description: Bootstrap the Home Assistant plugin environment. Use AUTOMATICALLY when invoking any /ha-* command or when needing to run validation scripts. Sets up the plugin path resolver for script execution.
---

# Plugin Environment Bootstrap

This skill ensures the Home Assistant plugin scripts are accessible by creating a local resolver script.

## Why Bootstrap is Needed

Claude Code plugins are installed to a cache directory that varies by environment. Due to a known limitation (anthropics/claude-code#9354), the `${PLUGIN_DIR}` variable is not available in markdown commands. This bootstrap creates a small resolver script that discovers where the plugin is installed, enabling the validation scripts to run.

## When This Activates

- Before running any `/ha-*` command
- When validation scripts are needed
- When the user asks to validate YAML or find duplicates

## Bootstrap Process

IMPORTANT: Before each step, explain to the user what you're doing and why. This helps them understand the permission prompts they'll see.

### Step 1: Check if Bootstrap is Needed

Tell the user:
> "Let me check if the Home Assistant plugin environment is already set up. This resolver script helps locate the plugin's validation tools."

Then run:
```bash
test -f .claude/ha-plugin-root.sh && echo "EXISTS" || echo "MISSING"
```

If EXISTS, skip to "Using the Resolver" section below.

### Step 2: Create the Resolver Script

If MISSING, tell the user:
> "I need to create a small resolver script in your project's `.claude/` directory. This script discovers where the Home Assistant plugin is installed so I can run validation tools like YAML syntax checking and duplicate detection."
>
> "The script will be created at `.claude/ha-plugin-root.sh` and only reads Claude's plugin registry - it doesn't modify anything."

First, create the directory:
```bash
mkdir -p .claude
```

Then create `.claude/ha-plugin-root.sh` with this content:

```bash
#!/bin/bash
# Home Assistant Plugin Root Resolver
# This script discovers where the homeassistant-config plugin is installed.
# It's needed because Claude Code doesn't expose plugin paths to commands.
# See: https://github.com/anthropics/claude-code/issues/9354

PLUGIN_NAME="homeassistant-config"

# Method 1: Check CLAUDE_PLUGIN_ROOT environment variable
# This is set automatically in hooks and MCP contexts
if [ -n "${CLAUDE_PLUGIN_ROOT}" ] && [ -d "${CLAUDE_PLUGIN_ROOT}" ]; then
  echo "${CLAUDE_PLUGIN_ROOT%/}"
  exit 0
fi

# Method 2: Look up from Claude's plugin registry
# Check multiple locations to support Docker/container environments
for PLUGINS_JSON in \
  "${HOME}/.claude/plugins/installed_plugins.json" \
  "/data/home/.claude/plugins/installed_plugins.json" \
  "/root/.claude/plugins/installed_plugins.json"; do
  if [ -f "$PLUGINS_JSON" ]; then
    PLUGIN_ROOT=$(jq -r --arg name "$PLUGIN_NAME" '
      .plugins | to_entries[] |
      select(.key | contains($name)) |
      .value[0].installPath
    ' "$PLUGINS_JSON" 2>/dev/null | head -1)

    if [ -n "$PLUGIN_ROOT" ] && [ "$PLUGIN_ROOT" != "null" ] && [ -d "$PLUGIN_ROOT" ]; then
      echo "$PLUGIN_ROOT"
      exit 0
    fi
  fi
done

# Method 3: Search common plugin cache locations
for base in "${HOME}/.claude/plugins" "/data/home/.claude/plugins" "/root/.claude/plugins"; do
  for dir in \
    "${base}/"*"${PLUGIN_NAME}"* \
    "${base}/cache/"*"/${PLUGIN_NAME}"/*; do
    if [ -d "$dir" ] && [ -f "$dir/.claude-plugin/plugin.json" ]; then
      echo "$dir"
      exit 0
    fi
  done
done

# Method 4: Development mode - check if we're in the plugin repo
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/../homeassistant-config/.claude-plugin/plugin.json" ]; then
  echo "$SCRIPT_DIR/../homeassistant-config"
  exit 0
fi

echo "ERROR: Could not locate $PLUGIN_NAME plugin. Is it installed?" >&2
echo "Try: /plugin install homeassistant-config@claude-homeassistant-plugins" >&2
exit 1
```

### Step 3: Make Executable

Tell the user:
> "Making the resolver script executable so it can be run."

```bash
chmod +x .claude/ha-plugin-root.sh
```

### Step 4: Verify Setup

Tell the user:
> "Testing the resolver to make sure it can find the plugin installation."

```bash
.claude/ha-plugin-root.sh
```

If successful, this outputs the plugin path. Tell the user:
> "Bootstrap complete! The plugin was found at: [path]. I can now run validation scripts."

If it fails, see Troubleshooting section.

## Using the Resolver

Once bootstrapped, run validation scripts like this:

```bash
# Get the plugin installation path
PLUGIN_ROOT="$(.claude/ha-plugin-root.sh)"

# Run the desired validation script
python3 "$PLUGIN_ROOT/skills/homeassistant-config/scripts/validate_yaml.py" /path/to/file.yaml
python3 "$PLUGIN_ROOT/skills/homeassistant-config/scripts/check_config.py" /path/to/config
python3 "$PLUGIN_ROOT/skills/homeassistant-config/scripts/find_duplicates.py" /path/to/config
python3 "$PLUGIN_ROOT/skills/homeassistant-config/scripts/lovelace_validator.py" /path/to/dashboard.yaml
```

When running these, tell the user what each script does:
- **validate_yaml.py**: Checks YAML syntax and Home Assistant-specific issues (tabs, unquoted booleans, deprecated syntax)
- **check_config.py**: Analyzes configuration structure, finds entities, tracks includes and secrets
- **find_duplicates.py**: Finds duplicate/similar automations and scripts, detects trigger conflicts
- **lovelace_validator.py**: Validates dashboard configurations (card types, entity IDs, actions)

## Troubleshooting

If the resolver fails, explain to the user:

1. **jq not installed**: The resolver needs `jq` to parse JSON. Install with:
   - macOS: `brew install jq`
   - Linux: `apt-get install jq` or `yum install jq`
   - Docker: Add to your image or use `apk add jq`

2. **Plugin not installed**: Verify the plugin is installed:
   ```bash
   cat ~/.claude/plugins/installed_plugins.json | jq '.plugins | keys'
   ```
   If `homeassistant-config` is missing, install it with `/plugin install homeassistant-config@claude-homeassistant-plugins`

3. **Container environment**: If running in Docker/container where `$HOME` differs from the actual data directory, the resolver checks `/data/home/.claude/` and `/root/.claude/` as fallbacks. If your environment uses a different path, check `installed_plugins.json` location manually:
   ```bash
   find / -name "installed_plugins.json" 2>/dev/null
   ```

4. **Manual override**: If all else fails, you can find the plugin manually and set the path directly:
   ```bash
   find ~/.claude -name "plugin.json" -exec grep -l homeassistant {} \; 2>/dev/null
   ```
