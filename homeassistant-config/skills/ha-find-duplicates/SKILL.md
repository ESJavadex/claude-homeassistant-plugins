---
name: ha-find-duplicates
description: Find duplicate, near-duplicate and conflicting automations and scripts in a Home Assistant config, and suggest how to merge them. Use when the user asks for duplicates, cleanup, or why two automations fight over the same device.
argument-hint: "[config path, default /config or current folder]"
allowed-tools: Bash(python3 *), Read, Grep, Glob
---

# Find duplicate automations and scripts

Path: `$ARGUMENTS`, or `/config` if it exists, else the current folder.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/homeassistant-config/scripts/find_duplicates.py" <path> --verbose
```

The finder treats old and new syntax as the same thing (`platform:`/`trigger:`,
`service:`/`action:`), so an old copy of a modern automation shows up as an
exact duplicate. Similar items are grouped into clusters; action names such as
`notify.mobile_app_x` do not count as shared entities.

Report, in this order:

1. **Exact duplicates**: same triggers, conditions and actions. Say which one
   to keep (the one with an `id`, the clearer alias, the newer syntax).
2. **Near-duplicate groups**: for each group, what differs. A group of many
   scripts that differ only in one value (a room, a scene, a brightness) is a
   candidate for one script with a `fields:` input; show that script.
3. **Trigger conflicts**: automations that fire on the same trigger. Explain
   whether they actually fight (one turns a light on, another off) or are
   harmless (two notifications). Intentional on/off pairs are fine.

Do not delete or edit anything until the user picks what to change. When they
do, back up the file first and run `validate_yaml.py` on it afterwards.
