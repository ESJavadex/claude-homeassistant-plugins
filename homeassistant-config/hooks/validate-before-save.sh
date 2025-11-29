#!/bin/bash
#
# Pre-save hook for Home Assistant YAML validation
# Runs before Write/Edit tools to validate YAML syntax
#

set -e

# Get tool input from environment
INPUT="$CLAUDE_TOOL_INPUT"

# Extract file path from the tool input
FILE_PATH=$(echo "$INPUT" | grep -oP '"file_path"\s*:\s*"\K[^"]+' 2>/dev/null || echo "")

# If no file path found, allow the operation
if [[ -z "$FILE_PATH" ]]; then
    exit 0
fi

# Only validate YAML files
if [[ ! "$FILE_PATH" =~ \.(yaml|yml)$ ]]; then
    exit 0
fi

# Check if this looks like a Home Assistant config file
# Skip validation for non-HA files
if [[ ! "$FILE_PATH" =~ (configuration|automations|scripts|scenes|secrets|lovelace|customize|groups|sensors|switches|lights|covers|fans|climate|ui-lovelace) ]]; then
    # Still validate basic YAML syntax for any .yaml file
    :
fi

# Try to extract content that will be written
CONTENT=$(echo "$INPUT" | python3 -c "
import sys
import json
try:
    data = json.load(sys.stdin)
    print(data.get('content', ''))
except:
    pass
" 2>/dev/null || echo "")

# If we have content, validate it
if [[ -n "$CONTENT" ]]; then
    # Check for tabs (HA requires spaces)
    if echo "$CONTENT" | grep -P '^\t' > /dev/null 2>&1; then
        echo "ERROR: Tab characters detected. Home Assistant requires spaces for indentation."
        exit 2
    fi

    # Basic YAML syntax check using Python
    RESULT=$(echo "$CONTENT" | python3 -c "
import sys
import yaml
try:
    yaml.safe_load(sys.stdin.read())
    print('OK')
except yaml.YAMLError as e:
    print(f'YAML Error: {e}')
    sys.exit(1)
" 2>&1)

    if [[ $? -ne 0 ]]; then
        echo "YAML Validation Failed:"
        echo "$RESULT"
        exit 2
    fi
fi

# Validation passed
exit 0
