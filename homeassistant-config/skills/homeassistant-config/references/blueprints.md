# Blueprints (Home Assistant 2026)

Blueprints are automations, scripts or template entities with inputs. Docs:
https://www.home-assistant.io/docs/blueprint/schema/ and selectors at
https://www.home-assistant.io/docs/blueprint/selectors/

## Outdated → current

| Outdated | Current | Since |
|---|---|---|
| `trigger:` / `action:` / `service:` / `platform:` in the blueprint body | `triggers:` / `actions:` / `action:` / `- trigger:` | 2024.8 / 2024.10 |
| Flat list of many inputs | Input sections with `collapsed:` | 2024.6 |
| Inputs always shown | Conditional `visible:` inputs | 2026.11 |
| `target` selector with a `device:` filter | `entity:` filter only (`integration`, `domain`, `device_class`…) | validation fails 2026.11 |
| Only automation/script blueprints | `domain: template` blueprints | 2024.11 |
| Hand-written trigger lists for user extras | `- triggers: !input extra_triggers` | 2024.10 |
| `color_temp` mireds in light actions | `color_temp_kelvin` | 2026.3 |
| Purpose-specific trigger IDs from before 2026.7 (`battery.low`…) | Renamed IDs (see `patterns.md`) | 2026.7 |

## File location

| Domain | Folder |
|---|---|
| automation | `config/blueprints/automation/<author>/<name>.yaml` |
| script | `config/blueprints/script/<author>/<name>.yaml` |
| template | `config/blueprints/template/<author>/<name>.yaml` |

Reload after editing: Settings → Automations & scenes → Blueprints → reload,
or restart. Blueprint WebSocket commands are admin-only since 2026.1.2.

## Schema

```yaml
blueprint:
  name: "Motion light"
  description: >-
    Turn on lights when motion is detected and off after a delay.
  domain: automation              # automation | script | template
  author: "Your name"
  source_url: "https://github.com/you/blueprints/blob/main/motion_light.yaml"
  homeassistant:
    min_version: "2026.11.0"      # refuse to load on older HA
  input:
    motion_entity:
      name: "Motion sensor"
      description: "Binary sensor that detects motion."
      selector:
        entity:
          filter:
            - domain: binary_sensor
              device_class: motion
    light_target:
      name: "Lights"
      selector:
        target:
          entity:
            - domain: light
```

Set `min_version` to the oldest release that has every feature you use
(`visible:` → 2026.11, `exclude` in targets → 2026.11, purpose-specific
triggers as default → 2026.7).

## Input sections

```yaml
  input:
    motion_entity:
      name: "Motion sensor"
      selector:
        entity:
          filter:
            - domain: binary_sensor
              device_class: motion
    timing:
      name: "Timing"
      icon: mdi:timer-outline
      description: "How long to keep the lights on."
      collapsed: true
      input:
        no_motion_wait:
          name: "Wait time"
          default: 120
          selector:
            number:
              min: 0
              max: 3600
              unit_of_measurement: seconds
```

- A section has `name`, `icon`, `description`, `collapsed` and `input`.
- Every input in a `collapsed: true` section needs a `default`.
- Inputs are referenced by name only (`!input no_motion_wait`), never by
  section. Input names must be unique across all sections.

## Conditional inputs (2026.11)

An input, or a whole section, can be shown only when another input has a given
value. Hidden fields are not required and their value is not saved, so give
them a `default`.

```yaml
    dim_mode:
      name: "Brightness"
      default: auto
      selector:
        select:
          options:
            - label: "Automatic by time of day"
              value: auto
            - label: "Fixed"
              value: fixed
    fixed_brightness:
      name: "Fixed brightness"
      default: 80
      visible:
        field: dim_mode
        value: fixed
      selector:
        number:
          min: 1
          max: 100
          unit_of_measurement: "%"
```

This is new in 2026.11; check the schema page for other forms of `visible`
(several values, sections).

## Using inputs

`!input` can only replace a whole value. To use an input inside a template,
copy it to a variable first.

```yaml
variables:
  wait_seconds: !input no_motion_wait
  brightness: !input fixed_brightness

actions:
  - action: light.turn_on
    target: !input light_target
    data:
      brightness_pct: "{{ brightness }}"
  - delay:
      seconds: "{{ wait_seconds }}"
```

`trigger_variables` are rendered before the triggers are attached and only
support limited templates (no state access). Use them for things like an event
type in a trigger:

```yaml
trigger_variables:
  event_kind: !input event_kind
triggers:
  - trigger: event
    event_type: "{{ event_kind }}"
```

### Letting users add triggers or actions

```yaml
blueprint:
  name: "Extensible example"
  domain: automation
  input:
    motion_entity:
      name: "Motion sensor"
      selector:
        entity:
          filter:
            - domain: binary_sensor
    extra_triggers:
      name: "Extra triggers"
      default: []
      selector:
        trigger:
    extra_actions:
      name: "Extra actions"
      default: []
      selector:
        action:

triggers:
  - trigger: state
    entity_id: !input motion_entity
    to: "on"
  - triggers: !input extra_triggers      # merged into this list (2024.10)

actions:
  - sequence: !input extra_actions
```

## Selectors

| Selector | Use for | Notes |
|---|---|---|
| `entity` | one or more entities | `filter:` list with `domain`, `device_class`, `integration`, `supported_features`; `multiple: true` |
| `target` | entities/devices/areas/floors/labels for `target:` | Filter with `entity:` only. A `device:` filter fails validation from 2026.11 |
| `device` | devices | Filter by `integration`, `manufacturer`, `model`; by model ID since 2025.4 |
| `area`, `floor`, `label` | IDs for templates | `multiple: true` returns a list |
| `number` | numbers | `min`, `max`, `step`, `unit_of_measurement`, `mode: box\|slider` |
| `boolean` | toggles | |
| `text` | strings | `multiline`, `type: password`, `multiple` |
| `select` | dropdown | `options` as strings or `label`/`value`; `multiple`, `custom_value`, `mode: dropdown\|list` |
| `time`, `duration`, `date`, `datetime` | times | `duration` returns a dict (`hours`, `minutes`, `seconds`) |
| `color_temp` | colour temperature | `unit: kelvin`, `min`, `max` |
| `color_rgb`, `icon`, `media`, `location`, `template` | | |
| `action`, `trigger`, `condition` | user-supplied steps | Merge with `- triggers: !input` / `sequence: !input` |
| `object` | structured data | `fields` and `multiple` since 2025.7 |
| `constant` | fixed value with a toggle | |
| `device_class`, `state_class` | pick a class | 2026.9; check the selector page for options |
| `unit_of_measurement` | pick a unit | 2026.10; check the selector page for options |

There is also a `choose` selector (2026.1) aimed at integrations; its YAML
keys are not confirmed here, so check the selectors page before using it.

### Target selector without `device:` (2026.11)

```yaml
# Fails validation from 2026.11
selector:
  target:
    device:
      integration: hue
    entity:
      domain: light
```

```yaml
# Use an entity filter
selector:
  target:
    entity:
      - integration: hue
        domain: light
```

## Complete automation blueprint

```yaml
blueprint:
  name: "Motion light (2026)"
  description: "Lights on with motion, off after no motion for a while."
  domain: automation
  homeassistant:
    min_version: "2026.11.0"
  input:
    motion_entity:
      name: "Motion sensor"
      selector:
        entity:
          filter:
            - domain: binary_sensor
              device_class:
                - motion
                - occupancy
    light_target:
      name: "Lights"
      selector:
        target:
          entity:
            - domain: light
    options:
      name: "Options"
      icon: mdi:tune
      collapsed: true
      input:
        no_motion_wait:
          name: "Turn off after"
          default: 120
          selector:
            number:
              min: 0
              max: 3600
              unit_of_measurement: seconds
        dim_mode:
          name: "Brightness"
          default: auto
          selector:
            select:
              options:
                - label: "By time of day"
                  value: auto
                - label: "Fixed"
                  value: fixed
        fixed_brightness:
          name: "Fixed brightness"
          default: 80
          visible:
            field: dim_mode
            value: fixed
          selector:
            number:
              min: 1
              max: 100
              unit_of_measurement: "%"
        illuminance_entity:
          name: "Illuminance sensor (optional)"
          default: ""
          selector:
            entity:
              filter:
                - domain: sensor
                  device_class: illuminance
        illuminance_max:
          name: "Only when below (lx)"
          default: 50
          selector:
            number:
              min: 0
              max: 1000
        extra_conditions:
          name: "Extra conditions"
          default: []
          selector:
            condition:

mode: restart
max_exceeded: silent

variables:
  dim_mode: !input dim_mode
  fixed_brightness: !input fixed_brightness
  wait_seconds: !input no_motion_wait
  lux_entity: !input illuminance_entity
  lux_max: !input illuminance_max

triggers:
  - trigger: state
    entity_id: !input motion_entity
    from: "off"
    to: "on"

conditions:
  - condition: template
    value_template: >-
      {{ lux_entity == '' or not has_value(lux_entity)
         or states(lux_entity) | float(0) < lux_max }}
  - condition: and
    conditions: !input extra_conditions

actions:
  - action: light.turn_on
    target: !input light_target
    data:
      brightness_pct: >-
        {% if dim_mode == 'fixed' %}{{ fixed_brightness }}
        {% elif now().hour >= 22 or now().hour < 7 %}20
        {% else %}100{% endif %}
  - wait_for_trigger:
      - trigger: state
        entity_id: !input motion_entity
        from: "on"
        to: "off"
  - delay:
      seconds: "{{ wait_seconds }}"
  - action: light.turn_off
    target: !input light_target
```

## Script blueprint

Blueprint inputs are filled in once, when the script is created. Values that
change on every call go in script `fields` in the blueprint body.

```yaml
blueprint:
  name: "Announce on speakers"
  domain: script
  input:
    speakers:
      name: "Speakers"
      selector:
        entity:
          multiple: true
          filter:
            - domain: media_player
    tts_entity:
      name: "TTS engine"
      selector:
        entity:
          filter:
            - domain: tts

mode: queued

fields:
  message:
    name: "Message"
    required: true
    selector:
      text:

variables:
  speakers: !input speakers

sequence:
  - action: tts.speak
    target:
      entity_id: !input tts_entity
    data:
      media_player_entity_id: "{{ speakers }}"
      message: "{{ message }}"
```

## Template blueprint

```yaml
# config/blueprints/template/homeassistant/inverted_binary_sensor.yaml
blueprint:
  name: "Invert a binary sensor"
  domain: template
  input:
    reference_entity:
      name: "Binary sensor to invert"
      selector:
        entity:
          filter:
            - domain: binary_sensor

variables:
  reference_entity: !input reference_entity

binary_sensor:
  state: >-
    {{ not is_state(reference_entity, 'on') }}
  availability: "{{ has_value(reference_entity) }}"
```

Use it under `template:`:

```yaml
template:
  - use_blueprint:
      path: homeassistant/inverted_binary_sensor.yaml
      input:
        reference_entity: binary_sensor.front_door
    name: "Front door closed"
    unique_id: front_door_closed
```

## Creating an automation from a blueprint

```yaml
# automations.yaml
- id: "hall_motion_light_bp"
  alias: "Hall - motion light"
  use_blueprint:
    path: you/motion_light.yaml
    input:
      motion_entity: binary_sensor.hall_motion
      light_target:
        area_id: hall
      no_motion_wait: 180
```

Import from a URL in the UI: Settings → Automations & scenes → Blueprints →
Import blueprint.

## Checklist

- Current keys in the body (`triggers`, `actions`, `action`, `- trigger:`).
- `homeassistant.min_version` set to the newest feature you rely on.
- Every input in a collapsed section, and every `visible:` input, has a
  `default`.
- Inputs used in templates are copied to `variables` first.
- `target` selectors filter with `entity:` only.
- Optional entity inputs default to `""` and the template checks for it.
- Test with a real automation created from the blueprint, then read its trace.
