---
name: homeassistant-config
description: Write, fix and modernise Home Assistant YAML with current (2026) syntax — automations, scripts, scenes, template entities, blueprints, packages, configuration.yaml and dashboards. Use whenever the task touches Home Assistant config files (/config or /homeassistant, automations.yaml, scripts.yaml, configuration.yaml, blueprints/, dashboards) or the user asks for an HA automation, sensor, template, blueprint or dashboard, or why one does not work.
when_to_use: Also use before editing any YAML inside a Home Assistant config folder, when a config check or repair mentions deprecated syntax, and when migrating old examples from forums or blogs (most of them are outdated).
---

# Home Assistant configuration

Home Assistant changes every month and most examples on the internet are old.
Write for the version the user actually runs, with the syntax below, and check
the result before telling the user it is done.

## 1. Before writing anything

1. **Find the version.** In the Claude Terminal add-on: `ha core info` (or
   `curl -s -H "Authorization: Bearer $SUPERVISOR_TOKEN" http://supervisor/core/info`).
   Elsewhere: Settings > About. Gate new features on it (table in section 3).
2. **Find the config folder.** `/config` on HA OS and in most add-ons, sometimes
   `/homeassistant`. `configuration.yaml` is the root.
3. **Look before you add.** Read how the user already organises things
   (`!include`, `packages/`, UI-managed `automations.yaml`) and follow it.
   Reuse their entity IDs: list them with
   `curl -s -H "Authorization: Bearer $SUPERVISOR_TOKEN" http://supervisor/core/api/states | jq -r '.[].entity_id'`
   or ask. Never invent entity IDs.
4. **Back up** a file before rewriting it (`cp automations.yaml automations.yaml.bak-$(date +%Y%m%d-%H%M)`).

## 2. Rules for current syntax

| Write this | Not this (old) | Since |
|---|---|---|
| `action: light.turn_on` | `service: light.turn_on` | 2024.8 |
| `triggers:` / `conditions:` / `actions:` | `trigger:` / `condition:` / `action:` (top-level lists) | 2024.10 |
| `- trigger: state` | `- platform: state` | 2024.10 |
| `template:` > `- sensor:` > `name:` / `state:` | `sensor:` > `- platform: template` (**removed 2026.6**) | 2026.6 |
| `color_temp_kelvin: 2700` | `color_temp:` (mireds), `kelvin:` (**removed**) | 2026.3 |
| `data:` with templates inside | `data_template:`, `service_template:` | long ago |
| `{{ has_value('sensor.x') }}` | `states('sensor.x') not in ['unknown','unavailable']` | 2023+ |
| `entity_name('light.x')`, `device_name()`, `area_name()` | `state_attr(x, 'friendly_name')` (planned deprecation) | 2026.4 / 2026.11 |
| `time_since(dt)` | `relative_time(dt)` (deprecated) | — |
| dashboards: `action: perform-action` + `perform_action:` | `action: call-service` + `service:` | 2024.8 |
| dashboards: `grid_options` (12 columns) | `layout_options` | 2024.11 |

Hard rules:
- **Never mix old and new keys in the same block** (`trigger` and `triggers`,
  `service` and `action`): Home Assistant rejects it.
- 2 spaces, never tabs. Quote `"on"`, `"off"`, `"yes"`, `"no"` when you mean
  the string (`to: "on"`), otherwise YAML turns them into booleans.
- Targets use IDs, lowercase: `entity_id`, `device_id`, `area_id`, `floor_id`,
  `label_id` (not names).
- Every new automation gets a unique `id:` (the UI editor and traces need it)
  and a clear `alias:`; pick `mode:` on purpose (`single` is the default).
- Actions that always return data need `response_variable:`.
- Supervisor actions (`hassio.*`) stop the script on failure since 2026.5;
  add `continue_on_error: true` when the script should carry on.
- Some things are UI-only now. `http:` is imported into the UI once (2026.8)
  and later YAML edits are ignored; many integrations can no longer be set up in
  YAML. Check the integration's docs page before writing YAML for it.
- Don't edit files in `.storage/` while Home Assistant runs. Never print or
  copy the contents of `secrets.yaml`; refer to `!secret name` only.
- Don't rewrite a user's whole file just to modernise style. Old keys like
  `service:` still work. Modernise what you touch; offer `/ha-upgrade` for the rest.

## 3. What depends on the version

| Feature | Needs |
|---|---|
| `action:` key, plural `triggers:` / `- trigger:` | 2024.8 / 2024.10 |
| Sections dashboards, `grid_options` | 2024.11 |
| `ai_task.generate_data` | 2025.8 |
| Purpose-specific triggers/conditions (`light.turned_on`, `light.is_on`, `zone.entered`) without Labs | 2026.7 |
| `target:` with `exclude:` | 2026.11 |
| Blueprint inputs with `visible:` | 2026.11 |

If the version is older than what a feature needs, use the classic form
(`trigger: state`, `condition: state`). When unsure, the classic form works everywhere.

## 4. Core snippets

**Automation** (classic triggers work in every version):
```yaml
- id: hallway_motion_light
  alias: Hallway light on motion
  mode: restart
  triggers:
    - trigger: state
      entity_id: binary_sensor.hallway_motion
      to: "on"
  conditions:
    - condition: sun
      after: sunset
  actions:
    - action: light.turn_on
      target:
        area_id: hallway
      data:
        brightness_pct: 60
        color_temp_kelvin: 2700
    - wait_for_trigger:
        - trigger: state
          entity_id: binary_sensor.hallway_motion
          to: "off"
          for: "00:02:00"
    - action: light.turn_off
      target:
        area_id: hallway
```

**Purpose-specific trigger and condition** (2026.7+): `target:` at the top,
settings under `options:`.
```yaml
triggers:
  - trigger: light.turned_on
    target:
      area_id: downstairs
    options:
      behavior: first        # each (default) | first | all
conditions:
  - condition: light.is_on
    target:
      entity_id: light.living_room
    options:
      behavior: all          # any (default) | all
```
Each trigger and condition has its own options: check its page under
https://www.home-assistant.io/triggers/ or /conditions/ before using one you
have not seen in this skill.
Renamed in 2026.5–2026.7 (old IDs no longer work): `battery.low` →
`battery.became_low`, `vacuum.docked` → `vacuum.returned_to_dock`,
`schedule.turned_on` → `schedule.block_started`, `person.entered_home` →
`zone.entered`, `climate.target_temperature` (condition) →
`climate.is_target_temperature`. Full table in `references/patterns.md`.
From 2026.11 the sign of `offset` on `sun.*` / `calendar.event_*` triggers
decides before (negative) or after (positive).

**Script with fields**:
```yaml
good_night:
  alias: Good night
  fields:
    delay:
      name: Delay
      default: 5
      selector:
        number: {min: 0, max: 60, unit_of_measurement: s}
  sequence:
    - action: light.turn_off
      target:
        floor_id: ground_floor
    - delay:
        seconds: "{{ delay }}"
```

**Template entity** (the only supported format since 2026.6):
```yaml
template:
  - sensor:
      - name: Total power
        unique_id: total_power
        unit_of_measurement: W
        device_class: power
        state_class: measurement
        state: "{{ states('sensor.plug_1_power') | float(0) + states('sensor.plug_2_power') | float(0) }}"
        availability: "{{ has_value('sensor.plug_1_power') and has_value('sensor.plug_2_power') }}"
```

**Dashboard card** (sections view is the default):
```yaml
type: tile
entity: light.living_room
features_position: bottom
features:
  - type: light-brightness
tap_action:
  action: perform-action
  perform_action: light.toggle
  target:
    entity_id: light.living_room
grid_options:
  columns: 6
  rows: 2
```
YAML-mode dashboards: top-level `lovelace: mode: yaml` is deprecated (2026.2);
use `lovelace: dashboards: lovelace: {mode: yaml, filename: ui-lovelace.yaml}`
plus `resource_mode: yaml`.

## 5. Check your work

Run the bundled checkers. They understand `!include`, `!secret` and `!input`
(plain `yaml.safe_load` does not) and know what changed up to 2026.11:

```bash
# syntax, tabs, duplicate keys, removed/deprecated syntax (file or whole folder)
python3 "${CLAUDE_SKILL_DIR}/scripts/validate_yaml.py" /config --quiet
# dashboards (YAML or .storage/lovelace*)
python3 "${CLAUDE_SKILL_DIR}/scripts/lovelace_validator.py" /config/.storage/lovelace
# structure: missing !include files, undefined !secret names, duplicate automation ids
python3 "${CLAUDE_SKILL_DIR}/scripts/check_config.py" /config
# duplicate and near-duplicate automations/scripts
python3 "${CLAUDE_SKILL_DIR}/scripts/find_duplicates.py" /config
```
Levels: **error** = will not work, **warning** = deprecated or ignored,
**info** = old style that still works.

Then let Home Assistant itself check and load it:
```bash
ha core check                      # official config check (add-on / SSH)
ha core logs | tail -50            # HA OS has no home-assistant.log since 2025.11
# reload without restarting
curl -s -X POST -H "Authorization: Bearer $SUPERVISOR_TOKEN" \
  http://supervisor/core/api/services/automation/reload
```
Reload actions: `automation.reload`, `script.reload`, `scene.reload`,
`template.reload`, `homeassistant.reload_core_config`, `homeassistant.reload_all`.
Without the CLI: Developer tools > YAML > Check configuration. After a change,
look at Settings > Repairs too: Home Assistant lists deprecated config there.

A plugin hook runs `validate_yaml.py` after every YAML edit and reports errors
back to you. If it reports something, fix it before moving on.

## 6. References (read when the task needs them)

| File | Read it when |
|---|---|
| `references/patterns.md` | writing automations: motion, presence, notifications, purpose-specific triggers, renames table |
| `references/templates.md` | template entities, Jinja, new functions, legacy → modern migration |
| `references/blueprints.md` | creating or fixing blueprints, selectors, input sections |
| `references/lovelace.md` | any dashboard work: sections, tile features, badges, visibility, strategies |
| `references/ai-and-assist.md` | `ai_task`, Assist, conversation triggers, MCP server |
| `references/best-practices.md` | organising config, packages, naming, performance |
| `references/troubleshooting.md` | an automation does not fire, config check errors, 2026 breakages |
| `examples/*.yaml` | complete working files to copy from |

Commands in this plugin: `/ha-check` (check a config folder end to end),
`/ha-upgrade` (find and migrate outdated syntax), `/ha-find-duplicates`.
The `ha-suggestions` agent proposes new automations from the user's devices.
