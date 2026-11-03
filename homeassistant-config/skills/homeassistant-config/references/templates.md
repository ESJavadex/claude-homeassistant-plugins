# Templates and Template Entities (Home Assistant 2026)

Jinja templates and the `template:` integration. Docs moved in 2026.5:
https://www.home-assistant.io/docs/templating/ and
https://www.home-assistant.io/template-functions/ (one page per function, for
example `/template-functions/entity_name/`).

## Outdated → current

| Outdated | Current | Since |
|---|---|---|
| `sensor:` / `binary_sensor:` / `switch:` … with `- platform: template` | `template:` block with a list of entities | deprecated 2025.12, **removed 2026.6** |
| `value_template:` inside a template entity | `state:` | 2026.6 (legacy removed) |
| `friendly_name:` inside a template entity | `name:` | 2026.6 |
| `icon_template:` / `entity_picture_template:` / `availability_template:` | `icon:` / `picture:` / `availability:` | 2026.6 |
| Entity ID from the dict key (`sensors: my_key:`) | `default_entity_id: sensor.my_key` | 2025.9 |
| `trigger:` / `platform:` in trigger-based templates | `triggers:` / `- trigger:` (plus `conditions:`, `actions:`) | 2024.10 |
| `relative_time(x)` | `time_since(x)` | deprecated |
| `state_attr(x, 'friendly_name')` | `entity_name(x)`, `device_name(x)`, `area_name(x)` | 2026.4; `friendly_name` planned for deprecation 2026.11 |
| `states(x) == 'None'` | `is none` / `has_value(x)` | — |
| Template binary_sensor rendering `None` = off | Renders `unknown` | 2025.8 |
| MQTT `object_id` | `default_entity_id` | 2026.4 |

## Modern template entities

```yaml
# configuration.yaml: template: !include templates.yaml
# templates.yaml is a list of blocks:
- sensor:
    - name: "Outside temperature"
      unique_id: outside_temperature
      default_entity_id: sensor.outside_temperature
      unit_of_measurement: "°C"
      device_class: temperature
      state_class: measurement
      state: "{{ states('sensor.weather_station_temp') | float(0) | round(1) }}"
      availability: "{{ has_value('sensor.weather_station_temp') }}"

- binary_sensor:
    - name: "Someone home"
      unique_id: someone_home
      state: "{{ states('zone.home') | int(0) > 0 }}"
      delay_off: "00:05:00"
```

- `unique_id` makes the entity editable in the UI (rename, area, labels).
- `default_entity_id` (2025.9) sets the entity ID it gets on creation. Without
  it, the ID comes from `name`.
- `availability` should return true/false. When false, the entity is
  `unavailable` and `state` is not rendered.
- Never mix legacy and modern keys in one entity.

### Migrating legacy `platform: template`

Since 2026.6 the legacy format "isn't supported anymore": those entities don't
load. Convert them:

```yaml
# Before (no longer loads)
sensor:
  - platform: template
    sensors:
      power_kw:
        friendly_name: "Power (kW)"
        unit_of_measurement: "kW"
        value_template: "{{ states('sensor.power_w') | float(0) / 1000 }}"
        icon_template: mdi:flash
        availability_template: "{{ has_value('sensor.power_w') }}"
        attribute_templates:
          source: "meter"
```

```yaml
# After
template:
  - sensor:
      - name: "Power (kW)"
        unique_id: power_kw
        default_entity_id: sensor.power_kw      # keeps the old entity ID
        unit_of_measurement: "kW"
        state: "{{ states('sensor.power_w') | float(0) / 1000 }}"
        icon: mdi:flash
        availability: "{{ has_value('sensor.power_w') }}"
        attributes:
          source: "meter"
```

| Legacy key | Modern key |
|---|---|
| `sensors:` / `switches:` / `covers:` … (dict keyed by object ID) | list of entities under `sensor:` / `switch:` / `cover:` … |
| object ID (dict key) | `default_entity_id: <domain>.<object_id>` |
| `friendly_name` | `name` |
| `value_template` | `state` |
| `icon_template` | `icon` |
| `entity_picture_template` | `picture` |
| `availability_template` | `availability` |
| `attribute_templates` | `attributes` |
| `unique_id`, `device_class`, `unit_of_measurement`, `delay_on`/`delay_off`, `turn_on`/`turn_off` | same name |

Platform-specific keys (cover `position_template`, light `level_template`, …)
also lose the `_template` suffix in most cases; check the template docs page
for each platform: https://www.home-assistant.io/integrations/template/

An unofficial helper exists (Petro31/hass-migrate-template on GitHub). Review
its output before using it.

### Template platforms under `template:`

`alarm_control_panel`, `binary_sensor`, `button`, `climate` (2026.10), `cover`,
`device_tracker` (2026.6, replaces the deprecated `device_tracker.see`),
`event` (2025.9), `fan`, `image`, `light`, `lock`, `number`, `select`,
`sensor`, `switch`, `update` (2025.9), `vacuum`, `weather`.

```yaml
- switch:
    - name: "Garden pump"
      unique_id: garden_pump
      state: "{{ is_state('switch.relay_3', 'on') }}"
      turn_on:
        - action: switch.turn_on
          target:
            entity_id: switch.relay_3
      turn_off:
        - action: switch.turn_off
          target:
            entity_id: switch.relay_3

- number:
    - name: "Night brightness"
      unique_id: night_brightness
      state: "{{ states('input_number.night_brightness') }}"
      min: 1
      max: 100
      step: 1
      set_value:
        - action: input_number.set_value
          target:
            entity_id: input_number.night_brightness
          data:
            value: "{{ value }}"

- button:
    - name: "Restart router"
      unique_id: restart_router_button
      press:
        - action: switch.turn_off
          target:
            entity_id: switch.router_plug
        - delay: "00:00:10"
        - action: switch.turn_on
          target:
            entity_id: switch.router_plug
```

Behaviour changes:
- 2025.8: a template binary_sensor that renders `None` is `unknown`, not off.
- 2026.3: a template fan with a state syntax error is `unavailable`; `None`
  gives `unknown`.
- 2026.8: template fan, cover and device_tracker restore their state after a
  restart.

## Trigger-based template entities

The state only updates when a trigger fires. Since 2024.10 the block can have
`conditions` and `actions`; variables from actions (including
`response_variable`) are available to the entity templates.

```yaml
- triggers:
    - trigger: time_pattern
      hours: "/1"
    - trigger: homeassistant
      event: start
  actions:
    - action: weather.get_forecasts
      target:
        entity_id: weather.home
      data:
        type: daily
      response_variable: forecast
  sensor:
    - name: "Tomorrow max temperature"
      unique_id: tomorrow_max_temperature
      unit_of_measurement: "°C"
      device_class: temperature
      state: "{{ forecast['weather.home'].forecast[1].temperature }}"
      attributes:
        condition: "{{ forecast['weather.home'].forecast[1].condition }}"
```

```yaml
# Only update while someone is home
- triggers:
    - trigger: state
      entity_id: sensor.living_room_co2
  conditions:
    - condition: state
      entity_id: binary_sensor.someone_home
      state: "on"
  sensor:
    - name: "CO2 while occupied"
      unique_id: co2_while_occupied
      unit_of_measurement: "ppm"
      state: "{{ trigger.to_state.state }}"
```

- 2026.9 added per-entity `conditions` and fully templatable `attributes`
  (custom attributes on most platforms). Check the template docs for the
  per-entity syntax.
- Trigger-based entities restore their last state after a restart.
- The `trigger` variable is available in all templates of the block.
- An `ai_task.generate_data` call can feed a sensor (2025.8; more in
  `ai-and-assist.md`):

```yaml
- triggers:
    - trigger: state
      entity_id: binary_sensor.coop_motion
      to: "on"
  actions:
    - action: ai_task.generate_data
      data:
        task_name: "Count birds"
        instructions: "How many birds (chickens, geese, ducks) are inside the coop?"
        structure:
          birds:
            selector:
              number:
        attachments:
          - media_content_id: media-source://camera/camera.coop
            media_content_type: image/jpeg
      response_variable: result
  sensor:
    - name: "Birds in coop"
      unique_id: birds_in_coop
      state_class: measurement
      state: "{{ result.data.birds }}"
```

## `this`

`this` is the entity's state object before the current render, which is
useful for counters and "keep the old value" logic:

```yaml
- triggers:
    - trigger: state
      entity_id: binary_sensor.front_door
      to: "on"
    - trigger: time
      at: "00:00:00"
      id: reset
  sensor:
    - name: "Front door openings today"
      unique_id: front_door_openings_today
      state_class: total_increasing
      state: >-
        {% if trigger.id == 'reset' %}0
        {% else %}{{ (this.state | int(0)) + 1 }}{% endif %}
```

## Safe templates

```jinja
{# Numbers: always give a default #}
{{ states('sensor.power') | float(0) }}

{# Is there a usable value? (not unknown/unavailable) #}
{{ has_value('sensor.power') }}

{# Compare states #}
{{ is_state('light.kitchen', 'on') }}
{{ is_state('alarm_control_panel.home', ['armed_away', 'armed_night']) }}

{# None checks #}
{{ state_attr('climate.hall', 'current_temperature') is not none }}

{# Names: entity_name (2026.4) instead of the friendly_name attribute #}
{{ entity_name('sensor.kitchen_temperature') }}
{{ device_name('sensor.kitchen_temperature') }}
{{ area_name('sensor.kitchen_temperature') }}
```

State values change between releases (snake_case states, media players
reporting `off` instead of `standby` since 2025.8, vacuum `battery` attributes
removed). Check the current value in Developer tools → States and prefer
`has_value()` / `is_state()` over string comparisons on attributes.

Test templates in Developer tools → Template. Output is capped at 256 KiB
(2024.10).

## Functions and filters added 2024.10 – 2026.10

| Release | Added | Notes |
|---|---|---|
| 2024.10 | `merge_response` | Flattens action responses from several entities into one list |
| 2025.4 | `combine`, `difference`, `flatten`, `intersect`, `symmetric_difference`, `union` | Dict and list set operations |
| 2025.4 | `shuffle`, `typeof`, `md5`, `sha1`, `sha256`, `sha512` | `typeof` helps when debugging types |
| 2025.4 | `floor_entities` | Entities on a floor |
| 2025.5 | `device_name` | `area_id()`/`floor_id()` also match aliases |
| 2025.6 | `from_hex` | |
| 2025.7 | `label_description` | |
| 2025.12 | `clamp`, `wrap`, `remap` | Numeric range helpers |
| 2025.12 | `issues()` | Returns only active repairs |
| 2026.4 | `entity_name`, `state_attr_translated` | Prefer `entity_name` over `friendly_name` |
| 2026.10 | `timedelta_string` | Formats a time span |

Check argument order on `/template-functions/<name>/` before using the newer
math and formatting helpers.

Examples:

```jinja
{{ floor_entities('upstairs') | select('match', 'light.') | select('is_state', 'on') | list | count }}
{{ ['a', 'b'] | union(['b', 'c']) }}
{{ {'a': 1} | combine({'b': 2}) }}
{{ label_entities('battery_powered') | map('area_name') | unique | join(', ') }}
{{ time_since(states.sensor.washer_power.last_changed) }}
```

### Deprecations

- `relative_time()` → `time_since()` (and `time_until()` for the future).
- `friendly_name` attribute → `entity_name()`, `device_name()`, `area_name()`
  (planned for deprecation from 2026.11). In 2026.11 entity names are composed
  from the device name plus the entity name, so text built from
  `friendly_name` may read differently.

## Response data

```yaml
# Calendar events for the next 24 h, inside an automation or script
- action: calendar.get_events
  target:
    entity_id:
      - calendar.work
      - calendar.family
  data:
    duration:
      hours: 24
  response_variable: agenda
- variables:
    events: "{{ merge_response(agenda) | sort(attribute='start') }}"
```

`merge_response` adds an `entity_id` key to each item, so you can still tell
which calendar it came from.

## Loops and lists

```jinja
{# Lights on in an area #}
{{ area_entities('living_room') | select('match', 'light.') | select('is_state', 'on') | list }}

{# Low batteries by label, with names #}
{% for e in label_entities('battery_powered')
     if has_value(e) and states(e) | float(100) < 20 -%}
  {{ entity_name(e) }}: {{ states(e) }}%
{% endfor %}

{# Count with a namespace (loops don't leak plain variables) #}
{% set ns = namespace(n=0) %}
{% for s in states.binary_sensor if s.attributes.device_class == 'window' and s.state == 'on' %}
  {% set ns.n = ns.n + 1 %}
{% endfor %}
{{ ns.n }}
```

## Template blueprints (2024.11)

Reusable template entities. Blueprint files go in
`config/blueprints/template/` with `domain: template`; see `blueprints.md`.

```yaml
template:
  - use_blueprint:
      path: homeassistant/inverted_binary_sensor.yaml
      input:
        reference_entity: binary_sensor.front_door
    name: "Front door closed"
    unique_id: front_door_closed
```

## Quick checklist

- `template:` block, never `platform: template`.
- `state`, `name`, `icon`, `availability`, `attributes`; no `_template`
  suffixes and no `friendly_name`.
- `unique_id` on every entity, `default_entity_id` when the ID matters.
- Filters with defaults: `float(0)`, `int(0)`, `| default(...)`.
- `has_value()` in `availability`.
- Names via `entity_name()`.
