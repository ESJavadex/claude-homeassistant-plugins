---
description: Find duplicate automations and scripts in Home Assistant configuration
---

# Find Duplicate Automations and Scripts

Scan Home Assistant configuration files to find duplicate automations and scripts.

## What This Command Does

This command analyzes your Home Assistant YAML configuration files to find:
- **Exact duplicates**: Automations or scripts with identical triggers and actions
- **Similar items**: Items with similar names, entities, or overlapping functionality
- **Trigger conflicts**: Multiple automations that could fire for the same event

## Prerequisites Check

First, tell the user:
> "I'll check if the plugin environment is set up. This is needed to run the duplicate detection script."

```bash
test -f .claude/ha-plugin-root.sh && echo "Ready" || echo "Need bootstrap"
```

If "Need bootstrap" is shown, tell the user:
> "I need to set up the plugin environment first. This creates a small script that helps me locate the validation tools."

Then invoke the `plugin-bootstrap` skill to create the resolver.

## Running the Analysis

Tell the user:
> "Now I'll scan your Home Assistant configuration files to find duplicate automations and scripts. This reads your YAML files and analyzes them for duplicates."

```bash
PLUGIN_ROOT="$(.claude/ha-plugin-root.sh)" && \
python3 "$PLUGIN_ROOT/skills/homeassistant-config/scripts/find_duplicates.py" ${1:-.} --verbose
```

If no path argument is provided, analyze the current directory.

## Interpreting Results

The script outputs JSON with these sections:

1. **files_scanned**: Number of YAML files analyzed
2. **automations_found** / **scripts_found**: Total counts
3. **exact_duplicates**: Groups of items with identical logic
4. **similar_items**: Groups with high similarity scores (80%+ match)
5. **trigger_conflicts**: Automations that may interfere with each other

## Presenting Findings

After running, present results to the user clearly:

### Exact Duplicates Found
For each group, explain:
- Which automations/scripts are duplicates
- What file(s) they're in
- Recommendation: which to keep and which to remove

### Similar Automations
For items with overlapping functionality:
- Highlight what's similar (triggers, entities, actions)
- Suggest consolidation if appropriate

### Trigger Conflicts
For automations that could fire for the same event:
- Explain the potential conflict
- Suggest adding conditions or modes to prevent issues

### Recommendations
Provide actionable next steps:
- Specific files to edit
- Which items to remove or consolidate
- Any entity IDs that may need updating after cleanup

## Example Output Interpretation

If the script finds 7 automations grouped as "exact duplicates", this likely means they share similar structure (e.g., all are notification automations from blueprints). Review each to determine if they're truly duplicates or just following a common pattern.
