---
description: Find duplicate automations and scripts in Home Assistant configuration
---

# Find Duplicate Automations and Scripts

Scan Home Assistant configuration files to find duplicate automations and scripts.

## Instructions

Run the duplicate finder script to analyze the configuration:

```bash
python3 ${PLUGIN_DIR}/skills/homeassistant-config/scripts/find_duplicates.py ${1:-.} --verbose
```

If no path argument is provided, analyze the current directory.

## Analysis Steps

1. Run the script above to find duplicates
2. Report findings to the user in a clear format:
   - **Exact duplicates**: Items with identical triggers/actions
   - **Similar items**: Items with similar names or overlapping functionality
   - **Conflicting automations**: Multiple automations that could fire for the same event
3. For each duplicate found, suggest:
   - Which one to keep (the more complete/better named one)
   - How to consolidate them if they have different conditions
   - Entity IDs that may need updating after removal

## Output Format

Present results as:

### Exact Duplicates
- List automations/scripts with identical logic

### Similar Automations
- List automations with similar triggers or entity targets

### Recommendations
- Specific actions to take for cleanup
