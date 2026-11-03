# Best Practices (Home Assistant 2026)

How to organise and maintain a configuration so it keeps working across
monthly releases.

## Outdated → current

| Outdated | Current | Since |
|---|---|---|
| Integrations configured in `configuration.yaml` | UI config entries (Settings → Devices & services) | ongoing; many moved 2025–2026 |
| `http:` block edited in YAML | Imported into the UI; change it in Settings → System → Network | 2026.8 |
| Reading `/config/home-assistant.log` on HA OS | `ha core logs` or Settings → System → Logs | 2025.11 |
| `ha addons …` | `ha apps …` (add-ons are now called apps) | seen on 2026.10 |
| HACS as a custom integration | Built in as "Marketplace" | 2026.11 |
| `sensor: - platform: template` | `template:` entities | removed 2026.6 |
| `service:`, `platform:` in triggers, singular `trigger:`/`action:` | `action:`, `- trigger:`, `triggers:`/`conditions:`/`actions:` | 2024.8 / 2024.10 |
| Lists of entity IDs in targets | Areas, floors, labels, plus `exclude` | 2026.11 for `exclude` |
| `friendly_name` in templates and messages | `entity_name()` / `device_name()` / `area_name()` | 2026.4 / 2026.11 |
| Hard-coded state strings (`standby`, `"None"`) | `is_state()`, `has_value()`, `is none` | — |
| Core or Supervised installs, 32-bit hardware | HA OS or Container on 64-bit | unsupported since 2025.12 |

## UI first, YAML where it still belongs

Integrations keep moving from YAML to the UI. On the first restart after the
change, HA imports the YAML and creates a config entry; after that the YAML is
ignored and a repair asks you to remove it. Examples: Bayesian (2025.9),
InfluxDB, Ness and Splunk (2026.3), SMTP (2026.7), `http:` (2026.8), Bitcoin
(2026.11). In 2026.11 `tellduslive:` YAML is no longer imported and the
`platform: telegram` notify was removed.

Before adding an integration in YAML, check its docs page for "Configuration
via the UI". If it has one, use the UI.

### `http:` (2026.8)

The `http:` YAML block is imported into the UI. Leaving it in YAML does not
break anything, but a repair asks to remove it, and edits to it are ignored
after the import. Change proxy settings, SSL and ports in Settings → System →
Network. Don't add `http:` to new configurations.

### What is still normal in YAML

- `automation:`, `script:`, `scene:` (either UI-managed files or your own).
- `template:` entities, including trigger-based ones.
- `homeassistant: packages:` and `customize:`.
- `recorder:`, `logger:`, `default_config:`.
- MQTT entities (`mqtt:`), helpers such as `input_boolean:` (optional, the UI
  can create them too), `command_line:`, `rest:`.
- Blueprints.

Name, location, units, time zone and currency: set them in Settings → System →
General. If they are in YAML under `homeassistant:`, the UI fields are locked.

## File layout

```yaml
# configuration.yaml
default_config:

homeassistant:
  packages: !include_dir_named packages

automation ui: !include automations.yaml          # written by the UI editor
automation manual: !include_dir_merge_list automations/
script: !include scripts.yaml
scene: !include scenes.yaml
template: !include templates.yaml
```

```
config/
├── configuration.yaml
├── automations.yaml          # UI editor writes here (entries need an id)
├── automations/              # hand-written, one list per file
├── scripts.yaml
├── scenes.yaml
├── templates.yaml            # list of template blocks
├── packages/
│   ├── kitchen.yaml
│   └── energy.yaml
├── blueprints/
│   ├── automation/
│   ├── script/
│   └── template/
└── secrets.yaml
```

- The UI editor only edits automations in `automations.yaml` that have an
  `id`. Automations in other files show as read-only.
- `automation ui:` / `automation manual:` are two labels for the same domain;
  any suffix after a space works.

### Packages

A package groups everything for one feature. Each top-level key is an
integration, merged with the rest of the configuration.

```yaml
# packages/kitchen.yaml
template:
  - sensor:
      - name: "Kitchen temperature"
        unique_id: kitchen_temperature
        unit_of_measurement: "°C"
        device_class: temperature
        state: "{{ state_attr('climate.kitchen', 'current_temperature') }}"
        availability: "{{ state_attr('climate.kitchen', 'current_temperature') is not none }}"

automation:
  - id: "kitchen_motion_light"
    alias: "Kitchen - motion light"
    triggers:
      - trigger: state
        entity_id: binary_sensor.kitchen_motion
        to: "on"
    actions:
      - action: light.turn_on
        target:
          area_id: kitchen
```

## Keys: current, and never mixed

Old keys (`service:`, `platform:`, singular top-level keys) still load, but:

- Write `action:`, `triggers:`, `conditions:`, `actions:`, `- trigger:` in
  everything new.
- Never mix old and new keys in the same block. `trigger:` and `triggers:`
  side by side, or `service:` and `action:` in one step, is not allowed
  ("use either the old key or the new key, not both in the same place").
- When you touch an old automation, convert the whole automation, not one
  step.
- Removed keys don't load at all: legacy template entities (2026.6), light
  `color_temp`/`kelvin` (2026.3), MQTT `topic_template`/`payload_template`
  (2025.2) and `object_id` (2026.4, use `default_entity_id`), old
  purpose-specific IDs (2026.5–2026.7).

## Naming and IDs

- `id:` on every automation (snake_case, unique); `unique_id:` on every
  template and MQTT entity. Without `unique_id`, the entity can't be renamed in
  the UI, and since 2026.11 MQTT entities without one ignore `device:`.
- Aliases as "Area - what it does": `"Kitchen - lights off after 30 min"`.
- From 2026.11 entity names are composed from the device name plus the entity
  name. In templates and notifications use `entity_name()`, `device_name()` and
  `area_name()` instead of the `friendly_name` attribute.
- Entity IDs whose domain doesn't match the entity stop working in 2027.5.

## Targets that follow the house

Point actions and purpose-specific triggers at areas, floors and labels
instead of entity lists. Add a light to the kitchen and it is included without
editing the automation. Use `exclude` (2026.11) for exceptions.

```yaml
- action: light.turn_off
  target:
    floor_id: ground_floor
    exclude:
      label_id: always_on
```

Since 2025.10 label targets include configuration and diagnostic entities with
that label, so keep labels specific.

## Purpose-specific triggers for new automations

Since 2026.7 the editor offers purpose-specific triggers and conditions first
(`light.turned_on`, `battery.became_low`, `zone.entered`). They handle
`unknown`/`unavailable` for you and work with area targets. Classic triggers
remain supported. Look up IDs and options on
https://www.home-assistant.io/triggers/ rather than writing them from memory;
several were renamed in 2026.5–2026.7.

## State values change

Integrations change state values between releases: snake_case states, media
players reporting `off` instead of `standby` (2025.8), vacuum `battery`
attributes removed (2025.8, 2026.8–2026.9), Ring `ding` → `ring` (2026.5),
person state showing the zone's friendly name (2025.11).

- Check the actual value in Developer tools → States.
- Use `has_value('sensor.x')` to guard against `unknown`/`unavailable`.
- Use `is_state()` (accepts a list) over `states(x) == '...'`.
- Prefer a dedicated sensor (battery level, power) over an attribute.
- Use `is none` rather than comparing to the string `"None"`.

## Templates

```yaml
# Compute once with variables, then reuse
actions:
  - variables:
      temp: "{{ states('sensor.outside_temperature') | float(0) }}"
  - action: notify.mobile_app_anna_phone
    data:
      message: "Outside: {{ temp }} °C ({{ 'cold' if temp < 5 else 'mild' }})"
```

- Always give filters a default: `float(0)`, `int(0)`, `| default('n/a')`.
- Use trigger-based template entities for values that only need refreshing
  on an event or a schedule.
- Avoid templates that iterate over all `states` in entities that update
  often; they re-render on every state change.

## Error handling

```yaml
actions:
  - action: hassio.backup_partial         # raises on failure since 2026.5
    data:
      homeassistant: true
    continue_on_error: true
  - wait_for_trigger:
      - trigger: state
        entity_id: binary_sensor.front_door
        to: "off"
    timeout: "00:30:00"
    continue_on_timeout: true
```

- `continue_on_error: true` only on steps whose failure is acceptable.
- Give every `wait_for_trigger` / `wait_template` a `timeout`.
- `response_variable` only on actions that return data.

## Recorder and database

```yaml
recorder:
  purge_keep_days: 10
  commit_interval: 5
  exclude:
    entity_globs:
      - sensor.*_linkquality
      - sensor.*_uptime
    entities:
      - sensor.date_time
```

- Exclude high-churn entities you never chart.
- Since 2024.8 the recorder no longer stores light colour and brightness
  attributes.
- Long-term statistics need `state_class` on the sensor.

## Logs and CLI on HA OS

- Since 2025.11 HA OS does not write `home-assistant.log`. Use `ha core logs`
  or Settings → System → Logs. To get the file back (2026.1+):
  `ha core options --duplicate-log-file=true` then `ha core rebuild`.
- `ha apps` replaces `ha addons` (the old command prints a deprecation
  warning).
- `ha core check` validates the configuration before a restart.

## Secrets and version control

```yaml
# configuration.yaml
recorder:
  db_url: !secret recorder_db_url    # value comes from secrets.yaml
```

```gitignore
secrets.yaml
.storage/
.cloud/
*.db
*.db-shm
*.db-wal
*.log
tts/
backups/
```

- Keep `secrets.yaml` out of git; commit a `secrets.yaml.example` with
  placeholders.
- `.storage/` holds UI-managed config and tokens. Git of your YAML does not
  back it up; use HA backups (Settings → System → Backups) with off-device
  copies.

## Before every upgrade

1. Read the release notes' "Backward-incompatible changes" section.
2. Check Settings → Repairs for deprecations already flagged.
3. Take a backup.
4. After the upgrade: Repairs again, then `ha core logs` for errors.

Known upcoming removals: legacy `device_tracker:` YAML platforms (luci, snmp,
google_maps…) and entity IDs with mismatched domains, both in 2027.5.
