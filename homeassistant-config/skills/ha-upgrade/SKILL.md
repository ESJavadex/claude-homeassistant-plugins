---
name: ha-upgrade
description: Modernise a Home Assistant config to current syntax — legacy template entities, removed light color_temp/kelvin, renamed purpose-specific triggers, service→action, platform→trigger, plural keys, call-service→perform-action, layout_options→grid_options, lovelace mode yaml. Use when the user asks to upgrade, migrate, modernise or clean up old YAML, or after a release removed something they use.
argument-hint: "[file or folder, default /config]"
disable-model-invocation: true
allowed-tools: Bash(python3 *), Bash(cp *), Bash(mkdir *), Bash(git -C * status*), Bash(git -C * rev-parse*), Bash(ha core check*), Read, Edit, Grep, Glob
---

# Upgrade Home Assistant YAML to current syntax

Target: `$ARGUMENTS`, or `/config`.

1. **Inventory.** Run
   `python3 "${CLAUDE_PLUGIN_ROOT}/skills/homeassistant-config/scripts/validate_yaml.py" <target> --quiet`
   and, for dashboards, `lovelace_validator.py`. Get the HA version
   (`cat /config/.HA_VERSION`, `ha core info`) so you never write syntax newer
   than the install.
   **Before an update:** `ha core info` shows `version_latest`; re-run the
   validator with `--ha-version=<that release>` to list what the update will
   break, and fix that first.
2. **Plan.** Show the user a short table: file, how many findings per level,
   what you would change. Order by risk:
   - errors first (things that already do not work: legacy `platform: template`,
     `color_temp`/`kelvin`, removed trigger IDs, mixed old/new keys);
   - then warnings (deprecated, ignored, about to break);
   - info last (`service:` → `action:`, `platform:` → `trigger:`, plural keys):
     purely cosmetic, only if the user wants it.
   **Imported blueprints** (the validator counts them under
   `imported_blueprints`, they have a `source_url`) are left alone: they are
   updated by re-importing a newer version (Settings > Blueprints > Re-import),
   and an edit would be lost on the next re-import. Mention them, don't edit
   them, unless the user asks. The user's own blueprints are upgraded like any
   other file.
   Ask which levels to apply. Stop here until they answer.
3. **Back up** every file you will edit, without leaving copies where they
   get picked up:
   - If the config folder is a git repository
     (`git -C /config rev-parse --is-inside-work-tree`), git is the backup:
     check `git -C /config status --short`. If the files you will touch have
     uncommitted changes, ask the user to commit them first. Make no `.bak`
     files there: a nightly `git add .` would commit them.
   - Otherwise copy them to one folder outside the files Home Assistant reads:
     `mkdir -p /config/.claude-backups/$(date +%Y%m%d-%H%M)` and `cp` each file
     there, keeping its relative path.
4. **Migrate** with the Edit tool: targeted edits, keeping comments, order and
   formatting. Never rewrite a file through a script (`yaml.safe_load` +
   `yaml.dump`, sed over the whole file): that drops comments and `!include`
   / `!secret` tags, and a script that fails halfway leaves the file empty.
   Read `references/templates.md` (legacy → modern template table) and
   `references/patterns.md` (renamed triggers) from the homeassistant-config
   skill first. Rules:
   - Legacy template entity: move it to `template:`, keep the entity ID with
     `default_entity_id: sensor.<old_object_id>` and add a `unique_id`.
   - `color_temp` (mireds) → `color_temp_kelvin` = round(1000000 / mireds).
   - Never mix old and new keys in one block; convert the whole block.
   - UI-managed `automations.yaml` / `scripts.yaml`: editing is fine, keep `id`s.
   - Do not touch `.storage/` files while HA is running; for UI dashboards,
     tell the user what to change in the editor instead, or edit the JSON
     only if they stop Home Assistant first. Name the dashboard and copy the
     finding's `where` (view title and tab, section heading, card number and
     type), not just `views[1].sections[1].cards[0]`: the JSON has no line
     numbers and the editor shows titles, not indexes.
5. **Verify.** Re-run the validator (the error and warning counts must drop to
   zero for the levels you applied), then `ha core check` if available, then
   reload (`automation.reload`, `script.reload`, `template.reload`) or ask the
   user to restart when templates moved between domains.
6. **Report** what changed per file, where the backups are (or the git
   commit to go back to), and which imported blueprints were left alone.
