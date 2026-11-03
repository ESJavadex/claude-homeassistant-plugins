# Troubleshooting (Home Assistant 2026)

Where to look, how to validate, and the breakages that show up most after
upgrading old YAML.

## Outdated → current

| Outdated | Current | Since |
|---|---|---|
| `tail -f /config/home-assistant.log` on HA OS | `ha core logs` / Settings → System → Logs | 2025.11 |
| Matching old voluptuous messages (`extra keys not allowed @ data[...]`) | New validation engine "Probatio" with different wording | 2026.9–2026.10 |
| Error paths as absolute container paths | Paths relative to the config folder, with suggested fixes | 2026.10 |
| Developer tools → Services | Developer tools → Actions | 2024.8 |
| `ha addons logs <slug>` | `ha apps logs <slug>` | seen on 2026.10 |
| "Entity not found" after upgrade, unknown cause | Check Settings → Repairs first: most removals are announced there | — |

## First steps

1. **Settings → Repairs.** Deprecations, YAML imported into the UI, removed
   keys and entities referenced by automations show up here, often with the
   exact file and fix.
2. **Check the configuration** before restarting:
   - UI: Developer tools → YAML → Check configuration.
   - HA OS / Supervisor CLI: `ha core check`.
   - Container: `docker exec homeassistant python -m homeassistant --script check_config -c /config`.
   - Offline, with this plugin:
     `python3 ${CLAUDE_SKILL_DIR}/scripts/check_config.py <config dir>`,
     `python3 ${CLAUDE_SKILL_DIR}/scripts/validate_yaml.py <file>`,
     `python3 ${CLAUDE_SKILL_DIR}/scripts/find_duplicates.py <config dir>`.
3. **Read the log**: `ha core logs` (HA OS), Settings → System → Logs, or
   `docker logs homeassistant`.
4. **Open the trace** of the automation or script (three-dot menu → Traces).

## Validation messages (Probatio)

Config validation moved from voluptuous to a new engine, Probatio
(developer blog, 30 Sep 2026:
https://developers.home-assistant.io/blog/2026/09/30/probatio-validation-engine).

- Messages are worded differently from older forum posts and from examples in
  this plugin's history. Read the message itself; don't search for the old
  voluptuous text.
- Some checks are stricter. YAML that loaded with a warning before may now be
  rejected (examples: webhook `local_only` must be a real boolean since 2026.5;
  state condition `for:` with `attribute:` since 2026.10).
- Since 2026.10 errors suggest a fix and give paths relative to the config
  folder, so the file and key are usually in the message.

## Logs

```yaml
# configuration.yaml
logger:
  default: warning
  logs:
    homeassistant.components.automation: info
    homeassistant.components.template: info
    custom_components.my_integration: debug
```

Change levels at runtime without a restart:

```yaml
action: logger.set_level
data:
  homeassistant.components.mqtt: debug
```

Or Settings → Devices & services → integration → Enable debug logging; when
you disable it, HA downloads the debug log.

HA OS since 2025.11 has no `home-assistant.log`. Tools that tail that file see
nothing. To restore the file (2026.1+): `ha core options --duplicate-log-file=true`
then `ha core rebuild`.

## Traces and history

- Each automation/script keeps its last 5 traces. Keep more while debugging:

```yaml
- id: "debug_me"
  alias: "Debug me"
  trace:
    stored_traces: 20
  triggers:
    - trigger: state
      entity_id: binary_sensor.hall_motion
  actions:
    - action: system_log.write
      data:
        level: warning
        message: "Fired by {{ trigger.entity_id }} -> {{ trigger.to_state.state }}"
```

- The trace shows which trigger fired, each condition's result and every
  variable at each step.
- 2026.6: condition rows in the editor show a live pass/fail badge.
- 2026.11: the Activity panel has a **Triggered by** filter, and the tools
  area has an **Action history** tab listing actions with their cause, user,
  context and data.

## Common 2026 breakages

| Symptom | Cause | Fix |
|---|---|---|
| Template sensors vanished after 2026.6 | Legacy `platform: template` removed | Move to `template:`; `state`/`name`/`icon`/`availability`; `default_entity_id` keeps the ID (see `templates.md`) |
| Automation with a person "home" trigger stopped loading | `entered_home`/`left_home`/`is_home`/`is_not_home` removed 2026.5 | `zone.entered` / `zone.left` / `zone.in_zone`, or classic `trigger: zone` |
| "Unknown trigger" for `battery.low`, `vacuum.docked`, `schedule.turned_on`, `timer.time_remaining`, `update.update_became_available` | Renamed 2026.7 | `battery.became_low`, `vacuum.returned_to_dock`, `schedule.block_started`, `timer.remaining_time_reached`, `update.became_available` |
| Zone trigger rejects `behavior: any` / `last` | Renamed 2026.6 | `each` / `all` |
| Purpose-specific trigger rejects `entity_id` / `behavior` | Wrong place | `target:` at top level; `behavior`, `for`, `threshold` under `options:` |
| Sunset/calendar automation fires at the wrong side of the event after 2026.11 | `offset` without `offset_type` on `sun.*` / `calendar.event_*`: sign now decides | Flip the sign or set `offset_type` explicitly |
| State condition with `for:` fails validation (2026.10) | `for:` combined with `attribute:` or another entity's state | Move the duration to a trigger, or use a template condition |
| `light.turn_on` with `color_temp` / `kelvin` errors | Removed 2026.3 | `color_temp_kelvin` |
| MQTT entity config rejected | `topic_template`/`payload_template` (2025.2) or `object_id` (2026.4) | `topic`/`payload` with templates; `default_entity_id` |
| MQTT entity not attached to its device (2026.11) | No `unique_id` | Add `unique_id` |
| Binary sensor shows `unknown` instead of off | Template renders `None` (2025.8) | Return `false` explicitly; add `availability` |
| Backup automation stops halfway (2026.5) | Supervisor actions now raise | `continue_on_error: true` on the `hassio.*` step |
| A variable has an unexpected value after a nested block | Scoping changed 2025.3/2025.4 | Rename the inner variable (see `patterns.md`) |
| Custom prompt calls `GetLiveContext` / `HassTurnOn` and fails | LLM tool names prefixed 2026.9 | `homeassistant__GetLiveContext`, `intent__HassTurnOn` |
| Blueprint fails to load after 2026.11 | `device:` filter in a `target` selector | Filter with `entity:` (see `blueprints.md`) |
| Notification text shows a different name after 2026.11 | Entity names now device + entity name | `entity_name()` / `device_name()` instead of `friendly_name` |
| `== 'standby'` never matches a media player | Reported as `off` since 2025.8 | Check Developer tools → States; use `is_state()` |
| `http:` changes have no effect | Imported into the UI in 2026.8 | Settings → System → Network |
| Integration YAML ignored, repair asks to remove it | Integration moved to the UI | Remove the YAML; configure in the UI |
| `notify` with `platform: telegram` fails (2026.11) | Removed | Telegram bot integration's notify entity / actions |
| Xiaomi Miio light/switch/fan action fails (2026.11) | Target now required | Add an explicit `target:` |
| Running an action by hand gives a permission error | Admin-only when run manually (update install/skip, Z-Wave lock credentials 2026.9; `mqtt.publish`, `mqtt.dump`, Synology reboot/shutdown 2026.10) | Use an admin account; automations are not affected |

## Scanning a config (or a forum example) for old syntax

Run from the config folder. Each hit is something to convert or check.

```bash
# Legacy template entities (removed 2026.6)
grep -rnE 'platform:\s*template' --include='*.yaml' .
grep -rnE '^\s*(value_template|icon_template|friendly_name):' --include='*.yaml' .

# Old automation keys (still load, but convert them)
grep -rnE '^\s*-?\s*(service|platform):' --include='*.yaml' automations* scripts* packages/
grep -rnE '^\s*(trigger|condition|action):\s*$' --include='*.yaml' automations* scripts* packages/

# Removed purpose-specific IDs (2026.5-2026.7)
grep -rnE '(entered_home|left_home|is_home|is_not_home|battery\.low|battery\.not_low|\.docked\b|schedule\.turned_|timer\.time_remaining|update_became_available|climate\.target_(temperature|humidity))' --include='*.yaml' .

# Offsets that changed meaning in 2026.11 (check if offset_type is missing)
grep -rnE -A4 'trigger:\s*(sun\.|calendar\.event_)' --include='*.yaml' .

# Lights, MQTT, names
grep -rnE '\b(color_temp|kelvin):' --include='*.yaml' .
grep -rnE '(topic_template|payload_template|object_id):' --include='*.yaml' .
grep -rnE "friendly_name'|relative_time\(|'standby'|== *'None'" --include='*.yaml' .

# Blueprint target selectors with a device filter (fails 2026.11)
grep -rnE -B2 -A3 'target:' blueprints/ | grep -n 'device:'
```

Notes:
- `condition:` and `action:` also appear legitimately inside steps
  (`- condition: state`, `- action: light.turn_on`); the second grep only
  flags them when they open a block at the top of an automation.
- `- trigger: state` inside a trigger list is current syntax; `trigger:` as
  a top-level automation key is not.
- `color_temp:` is also the name of a blueprint selector, which is fine; only
  the light parameter (mireds) is removed.

## YAML syntax

| Error text (PyYAML part) | Cause | Fix |
|---|---|---|
| `found character '\t' that cannot start any token` | Tab character | Spaces only, 2 per level |
| `mapping values are not allowed here` | Bad indentation, or an unquoted `:` in a value | Re-indent; quote values with `: ` |
| `found undefined alias` / `found unknown escape character` | `*` or `\` in an unquoted string | Quote it |
| `could not find expected ':'` | Missing colon, or a `{{ }}` value not quoted | Quote templates that start with `{` |
| Duplicate key warning, or an automation silently missing | Same key twice; last one wins | `python3 ${CLAUDE_SKILL_DIR}/scripts/find_duplicates.py` |

Quote these values: `"on"`, `"off"`, `"yes"`, `"no"`, times like `"07:30:00"`,
and anything starting with `{`, `*`, `&`, `!`, `%` or `@`.

```yaml
# Wrong: the value becomes a boolean / a YAML mapping
hvac_mode: off
message: {{ states('sensor.x') }}
```

```yaml
# Right
hvac_mode: "off"
message: "{{ states('sensor.x') }}"
```

## Templates

Test in Developer tools → Template first.

| Problem | Fix |
|---|---|
| `could not convert string to float: 'unavailable'` | `states('sensor.x') \| float(0)`, or guard with `has_value('sensor.x')` |
| `'None' has no attribute …` | Check `state_attr(...) is not none` first |
| Sensor goes `unknown` at startup | Add `availability: "{{ has_value('sensor.source') }}"` |
| Template never updates | It references no entities (only `now()` updates once a minute), or it is trigger-based and the trigger never fires |
| Output cut off | 256 KiB limit (2024.10) |
| `relative_time` deprecation warning | `time_since()` |

## Automation does not run

1. Is it enabled? Is the `id` unique? A duplicate `id` hides one of them.
2. Open the trace. No trace means the trigger never fired.
3. Trigger:
   - Entity ID exists and is spelled right (Developer tools → States).
   - `to:` matches the real state value (case, snake_case, `"on"` quoted).
   - `for:` resets each time the state changes.
   - Purpose-specific trigger: the ID exists in your version and options sit
     under `options:`.
4. Conditions: the trace shows which one was false. `condition: time` with
   `after` later than `before` spans midnight.
5. Mode: `mode: single` drops runs while one is active (warning in the log
   unless `max_exceeded: silent`).
6. Actions: a failing step stops the run unless `continue_on_error: true`.

## Action errors

| Message idea | Cause | Fix |
|---|---|---|
| Action not found | Integration not loaded or action removed (for example `bluesound.join`, removed 2026.11) | Developer tools → Actions to see what exists |
| Response variable required / not supported | `response_variable` missing on an action that returns data, or set on one that returns nothing | Add or remove it |
| Must specify a target | Target required (for example Xiaomi Miio since 2026.11) | Add `target:` |
| Expected int / float | Data given as a string with units | Pass a number; `"{{ x \| int }}"` in templates |

## Entities unavailable

- Settings → Devices & services: is the integration failing to set up? Use
  **Reload** on the integration.
- Check `ha core logs` for setup errors from the integration.
- Network devices: reachable? Same VLAN for discovery?
- After an upgrade: Repairs, and the release notes' backward-incompatible
  changes for that integration.

## Reload or restart?

- Developer tools → YAML lists what can be reloaded without a restart:
  automations, scripts, scenes, template entities, groups, input helpers,
  MQTT entities, `customize` and more.
- Anything not on that list (most YAML-configured integrations, `recorder:`,
  `logger:` defaults, `homeassistant: packages:` changes that add a new
  domain) needs a restart. Run the configuration check first.
- A reload that fails leaves the old configuration running and writes the
  error to the log and to a notification.

## Slow startup or high CPU

- Settings → System → Repairs and the startup timings in Settings → System →
  System information / Logs.
- Exclude high-churn entities from the recorder.
- Templates that loop over all `states` re-render on every state change;
  narrow them to a domain (`states.sensor`) or use trigger-based templates.
- Lower polling: `scan_interval` on `rest:` / `command_line:` entities.

## Checklist before saying "done"

- Configuration check passes (`ha core check` or Developer tools → YAML).
- No new items in Settings → Repairs.
- No errors for the changed domain in `ha core logs`.
- The automation ran once and its trace looks right.
