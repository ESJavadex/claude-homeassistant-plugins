# Automation Patterns (Home Assistant 2026)

Working patterns for automations and scripts, written in current syntax. Every
example is an entry for `automations.yaml` (a list). In a package, put the same
entries under `automation:`.

## Outdated → current

| Outdated (still seen in old examples) | Current | Since |
|---|---|---|
| `service: light.turn_on` | `action: light.turn_on` | 2024.8 |
| `trigger:` / `condition:` / `action:` at the top level | `triggers:` / `conditions:` / `actions:` | 2024.10 |
| `- platform: state` inside triggers | `- trigger: state` | 2024.10 |
| `person.entered_home`, `left_home`, `is_home`, `is_not_home` | `zone.entered`, `zone.left`, `zone.in_zone` | removed 2026.5, replaced 2026.6 |
| Zone `behavior: any` / `last` | `behavior: each` / `all` | 2026.6 |
| `battery.low`, `vacuum.docked`, `schedule.turned_on`, … | See the rename table below | 2026.7 |
| `offset` on `sun.*` / `calendar.event_*` without `offset_type` (positive = before) | Sign decides: negative = before, positive = after | 2026.11 |
| `color_temp` (mireds), `kelvin` | `color_temp_kelvin` | removed 2026.3 |
| State condition with `for:` plus `attribute:` | Template condition, or a trigger with `for:` | fails validation 2026.10 |
| Expecting a failed `hassio.*` action to carry on | Add `continue_on_error: true` | 2026.5 |
| `state_attr(x, 'friendly_name')` in messages | `entity_name(x)` / `device_name(x)` / `area_name(x)` | 2026.4 / 2026.11 |

Old keys (`service:`, `platform:`, singular top-level keys) still load, but
never mix old and new keys in the same block. The docs say: "Use either the
old key or the new key, not both in the same place."

## Skeleton

```yaml
- id: "hall_motion_light"          # needed for the UI editor and traces
  alias: "Hall - motion light"
  description: "Turn on the hall light on motion when it is dark."
  mode: restart                      # single | restart | queued | parallel
  max_exceeded: silent               # don't log a warning when mode: single drops a run
  variables:
    target_light: light.hall
  triggers:
    - trigger: state
      entity_id: binary_sensor.hall_motion
      to: "on"
      id: motion
  conditions:
    - condition: numeric_state
      entity_id: sensor.hall_illuminance
      below: 30
  actions:
    - action: light.turn_on
      target:
        entity_id: "{{ target_light }}"
      data:
        brightness_pct: 70
```

Trigger IDs are hidden in the editor since 2026.10, but `id:` in YAML still
works and `trigger.id` is still set.

## Targets

`target:` accepts `entity_id`, `device_id`, `area_id`, `floor_id` and
`label_id`. Use IDs (lowercase, as shown in Settings), not display names.

```yaml
- action: light.turn_off
  target:
    floor_id: upstairs
    label_id: night_lights
```

Since 2025.10, label targets also hit configuration and diagnostic entities
that carry the label. Label only what you mean to control.

### Excluding part of a target (2026.11)

`exclude` goes inside `target` and takes the same keys as the target. It works
in triggers, conditions and actions. HA works it out on every run, so a light
added to the kitchen later is excluded too.

```yaml
- action: light.turn_on
  target:
    floor_id: ground_floor
    exclude:
      area_id: kitchen
      label_id: night_light
```

Limits: `exclude` cannot use `all`/`none`, cannot be nested, and is not a target
on its own. Docs: https://www.home-assistant.io/docs/automation/targets/#excluding-targets

## Purpose-specific triggers and conditions

Introduced in Labs in 2025.12, the default in the editor since 2026.7. They are
named after what happens (`light.turned_on`, `battery.became_low`) instead of
state values, accept any target (area, floor, label, device, entity), and deal
with `unknown`/`unavailable` themselves. Integrations can add their own.

Shape: `target` at the top level of the trigger; `behavior`, `for`,
`threshold` and other settings under `options`.

```yaml
triggers:
  - trigger: light.turned_on
    target:
      area_id: downstairs
    options:
      behavior: first      # each (default) | first | all
      for: "00:00:10"
conditions:
  - condition: light.is_on
    target:
      entity_id: light.living_room
    options:
      behavior: all        # any (default) | all
```

- Triggers are `domain.verb` (`light.turned_on`, `vacuum.returned_to_dock`,
  `doorbell.rang`, `button.pressed`, `event.received`).
- Conditions are `domain.is_x` (`light.is_on`, `climate.is_target_temperature`).
- Cross-domain classes exist for door, window, motion, occupancy, battery,
  temperature, humidity, power, air quality and more, next to the entity
  domains (climate, cover, lock, media_player, timer, todo, zone, sun, moon,
  calendar…).
- Each one has its own page with its options and YAML:
  https://www.home-assistant.io/triggers/ and
  https://www.home-assistant.io/conditions/ (for example
  `/triggers/air_quality.radon_crossed_threshold/`). Look up the exact ID and
  option keys there; don't guess them.

Threshold triggers look like this (illustrative, check the page for the exact
keys of the trigger you use):

```yaml
- trigger: temperature.crossed_threshold
  target:
    area_id: living_room
  options:
    threshold:
      type: above            # above | below | between | outside
      value:
        number: 22
        unit_of_measurement: "°C"
    for: "00:05:00"
```

### Purpose-specific or classic?

| Prefer purpose-specific when | Prefer classic `state` / `numeric_state` / `template` when |
|---|---|
| You target an area, floor or label ("any light downstairs") | You need `from:`/`to:` on exact states or attribute changes |
| You want first/all/each semantics across many entities | You need `trigger.from_state` / `trigger.to_state` details |
| Event entities (`event.received`): no "same state twice" trap | The trigger must work on HA older than 2026.7 |
| Battery/threshold logic you would otherwise template | No purpose-specific trigger exists for the case |

Classic triggers are not deprecated: `state`, `numeric_state`, `time`,
`time_pattern`, `template`, `event`, `sun`, `zone`, `calendar`, `mqtt`,
`webhook`, `tag`, `conversation`, `homeassistant` and `device` all still work.

### Renamed and removed keys (breaking)

| Release | Old (no longer works) | New |
|---|---|---|
| 2026.5 | `person.entered_home` / `device_tracker.entered_home` | `zone.entered` (2026.6) |
| 2026.5 | `person.left_home` / `device_tracker.left_home` | `zone.left` (2026.6) |
| 2026.5 | conditions `is_home` / `is_not_home` | `zone.in_zone` (2026.6, plus a "not in zone" condition) |
| 2026.6 | zone `behavior: any` / `last` | `each` / `all` (default `each`) |
| 2026.7 | `battery.low` / `battery.not_low` | `battery.became_low` / `battery.no_longer_low` |
| 2026.7 | `lawn_mower.docked` | `lawn_mower.returned_to_dock` |
| 2026.7 | `vacuum.docked` | `vacuum.returned_to_dock` |
| 2026.7 | `schedule.turned_on` / `schedule.turned_off` | `schedule.block_started` / `schedule.block_ended` |
| 2026.7 | `timer.time_remaining` | `timer.remaining_time_reached` |
| 2026.7 | `update.update_became_available` | `update.became_available` |
| 2026.7 | conditions `climate.target_temperature` / `climate.target_humidity` | `climate.is_target_temperature` / `climate.is_target_humidity` |

### Zones

2026.6 added zone triggers (enter, leave, zone becomes occupied, zone becomes
empty) and conditions (in zone, not in zone, zone occupied, not occupied). They
work with any zone, not just home, and support `for`. The release notes name
the IDs `zone.entered`, `zone.left` and `zone.in_zone`; check
https://www.home-assistant.io/triggers/ for the occupied/empty IDs and for the
option that selects the zone.

```yaml
# Illustrative: the option key that picks the zone must be checked on
# https://www.home-assistant.io/triggers/zone.entered/
- trigger: zone.entered
  target:
    entity_id: person.anna
  options:
    zone: zone.work
    for: "00:02:00"
```

Related state changes:
- Since 2025.11 a person in a custom zone reports the zone's friendly name as
  its state (for example `Work`), so `state: work` comparisons can break.
- Since 2026.7 a person seen by a home scanner no longer reports the home
  coordinates. Use the `in_zones` attribute or a zone condition instead of
  comparing latitude/longitude. A person can count toward several zones at once.

The classic zone trigger is still fine:

```yaml
- trigger: zone
  entity_id: person.anna
  zone: zone.work
  event: enter               # enter | leave
```

### Sun and calendar offsets (2026.11)

For the purpose-specific `sun.*`, `calendar.event_started` and
`calendar.event_ended` triggers, a missing `offset_type` used to mean "before",
so a positive offset fired early. Since 2026.11 the sign decides: negative is
before, positive is after. YAML that sets `offset` without `offset_type` must
flip the sign. Triggers saved from the UI always wrote `offset_type` and are
unaffected. Write `offset_type` explicitly to stay unambiguous.

The classic triggers already used signed offsets and did not change:

```yaml
- trigger: sun
  event: sunset
  offset: "-00:30:00"        # 30 minutes before sunset
- trigger: calendar
  event: start
  entity_id: calendar.work
  offset: "-00:15:00"        # 15 minutes before the event starts
```

## Lighting

### Motion light with timeout

`mode: restart` restarts the wait on every new motion event.

```yaml
- id: "living_motion_light"
  alias: "Living room - motion light"
  mode: restart
  triggers:
    - trigger: state
      entity_id: binary_sensor.living_room_motion
      to: "on"
  conditions:
    - condition: numeric_state
      entity_id: sensor.living_room_illuminance
      below: 50
  actions:
    - action: light.turn_on
      target:
        area_id: living_room
      data:
        brightness_pct: 80
    - wait_for_trigger:
        - trigger: state
          entity_id: binary_sensor.living_room_motion
          to: "off"
          for: "00:05:00"
      timeout: "01:00:00"
      continue_on_timeout: true
    - action: light.turn_off
      target:
        area_id: living_room
```

### Brightness and colour temperature by time of day

```yaml
- id: "bedroom_adaptive_on"
  alias: "Bedroom - adaptive brightness"
  triggers:
    - trigger: state
      entity_id: light.bedroom
      from: "off"
      to: "on"
  actions:
    - variables:
        hour: "{{ now().hour }}"
    - action: light.turn_on
      target:
        entity_id: light.bedroom
      data:
        brightness_pct: "{{ 20 if hour < 7 else (100 if hour < 20 else 50) }}"
        color_temp_kelvin: "{{ 2700 if hour >= 20 or hour < 7 else 4000 }}"
```

Use `color_temp_kelvin`; `color_temp` (mireds) and `kelvin` were removed in
2026.3. Light attributes are `min_color_temp_kelvin` / `max_color_temp_kelvin`.

### Everything off on a floor except the night lights

```yaml
- id: "upstairs_off_at_night"
  alias: "Upstairs - lights off at 23:30"
  triggers:
    - trigger: time
      at: "23:30:00"
  actions:
    - action: light.turn_off
      target:
        floor_id: upstairs
        exclude:
          label_id: night_light
```

## Presence

### Last person leaves

`zone.home` holds the number of people at home.

```yaml
- id: "goodbye"
  alias: "Presence - everyone left"
  triggers:
    - trigger: numeric_state
      entity_id: zone.home
      below: 1
      for: "00:05:00"
  actions:
    - action: light.turn_off
      target:
        entity_id: all
    - action: climate.set_preset_mode
      target:
        entity_id: climate.living_room
      data:
        preset_mode: away
```

### Welcome home after dark

```yaml
- id: "welcome_home"
  alias: "Presence - welcome home"
  triggers:
    - trigger: zone
      entity_id:
        - person.anna
        - person.ben
      zone: zone.home
      event: enter
  conditions:
    - condition: sun
      after: sunset
      before: sunrise
  actions:
    - action: light.turn_on
      target:
        area_id: hallway
      data:
        brightness_pct: 100
    - action: notify.mobile_app_anna_phone
      data:
        message: "{{ entity_name(trigger.entity_id) }} just got home."
```

## Climate

### Pause heating while a window is open

```yaml
- id: "window_pause_heating"
  alias: "Climate - pause heating while window open"
  mode: restart
  triggers:
    - trigger: state
      entity_id: binary_sensor.living_room_window
      to: "on"
      for: "00:02:00"
  conditions:
    - condition: not
      conditions:
        - condition: state
          entity_id: climate.living_room
          state: "off"
  actions:
    - variables:
        previous_mode: "{{ states('climate.living_room') }}"
    - action: climate.set_hvac_mode
      target:
        entity_id: climate.living_room
      data:
        hvac_mode: "off"
    - wait_for_trigger:
        - trigger: state
          entity_id: binary_sensor.living_room_window
          to: "off"
          for: "00:01:00"
      timeout: "04:00:00"
    - action: climate.set_hvac_mode
      target:
        entity_id: climate.living_room
      data:
        hvac_mode: "{{ previous_mode }}"
```

Quote `"off"` and `"on"` in data: unquoted they become booleans.

## Security

### Door left open, repeat reminder

```yaml
- id: "front_door_open_reminder"
  alias: "Security - front door left open"
  mode: single
  triggers:
    - trigger: state
      entity_id: binary_sensor.front_door
      to: "on"
      for: "00:10:00"
  actions:
    - repeat:
        sequence:
          - action: notify.mobile_app_anna_phone
            data:
              title: "Front door"
              message: >-
                Open for {{ time_since(states.binary_sensor.front_door.last_changed) }}.
          - delay: "00:10:00"
        until:
          - condition: state
            entity_id: binary_sensor.front_door
            state: "off"
```

`time_since()` replaces the deprecated `relative_time()`.

## Notifications

### Actionable notification with a unique action ID

Building the action ID from `context.id` stops two runs from answering each
other's buttons.

```yaml
- id: "garage_open_ask"
  alias: "Garage - ask to close"
  triggers:
    - trigger: state
      entity_id: cover.garage
      to: "open"
      for: "00:30:00"
  actions:
    - variables:
        action_close: "{{ 'CLOSE_' ~ context.id }}"
        action_ignore: "{{ 'IGNORE_' ~ context.id }}"
    - action: notify.mobile_app_anna_phone
      data:
        title: "Garage open"
        message: "The garage has been open for 30 minutes."
        data:
          actions:
            - action: "{{ action_close }}"
              title: "Close"
            - action: "{{ action_ignore }}"
              title: "Leave open"
    - wait_for_trigger:
        - trigger: event
          event_type: mobile_app_notification_action
          event_data:
            action: "{{ action_close }}"
        - trigger: event
          event_type: mobile_app_notification_action
          event_data:
            action: "{{ action_ignore }}"
      timeout: "00:10:00"
      continue_on_timeout: false
    - if:
        - condition: template
          value_template: "{{ wait.trigger.event.data.action == action_close }}"
      then:
        - action: cover.close_cover
          target:
            entity_id: cover.garage
```

Since 2025.3 `wait` is also visible after the step's enclosing block (see
variable scoping below).

### Several people at once

```yaml
- id: "doorbell_notify_all"
  alias: "Doorbell - notify everyone"
  triggers:
    - trigger: state
      entity_id: event.front_doorbell
      not_from: unavailable
  actions:
    - parallel:
        - action: notify.mobile_app_anna_phone
          data:
            message: "Someone is at the door."
        - action: notify.mobile_app_ben_phone
          data:
            message: "Someone is at the door."
```

A state trigger on an event entity fires on each new event (the state is the
event timestamp); `not_from: unavailable` skips the change after a restart.
Purpose-specific alternatives: `doorbell.rang` and `event.received`.

## Batteries

```yaml
- id: "battery_low_notify"
  alias: "Batteries - notify when low"
  triggers:
    - trigger: battery.became_low      # was battery.low before 2026.7
      target:
        label_id: battery_powered
  actions:
    - action: notify.mobile_app_anna_phone
      data:
        title: "Battery low"
        message: "{{ entity_name(trigger.entity_id) }} needs a new battery."
```

The trigger decides what "low" means for each device, so you don't have to
template percentages. Some integrations removed the vacuum `battery` /
`battery_level` attribute (2025.8, 2026.8–2026.9): read the battery sensor
entity instead. `trigger.entity_id` is assumed here; check the trigger's page
for the variables it sets.

## Calendar

```yaml
- id: "meeting_prepare_office"
  alias: "Office - prepare before meetings"
  triggers:
    - trigger: calendar
      event: start
      entity_id: calendar.work
      offset: "-00:10:00"
  conditions:
    - condition: template
      value_template: "{{ 'online' in (trigger.calendar_event.location | default('')) | lower }}"
  actions:
    - action: light.turn_on
      target:
        area_id: office
      data:
        brightness_pct: 100
        color_temp_kelvin: 4500
```

## One automation, several triggers

```yaml
- id: "office_button"
  alias: "Office - button"
  mode: queued
  triggers:
    - trigger: state
      entity_id: event.office_button
      not_from: unavailable
  variables:
    press: "{{ trigger.to_state.attributes.event_type }}"
  actions:
    - choose:
        - conditions: "{{ press == 'single' }}"
          sequence:
            - action: light.toggle
              target:
                area_id: office
        - conditions: "{{ press == 'double' }}"
          sequence:
            - action: scene.turn_on
              target:
                entity_id: scene.office_focus
        - conditions: "{{ press == 'long_press' }}"
          sequence:
            - action: light.turn_off
              target:
                floor_id: ground_floor
      default:
        - action: system_log.write
          data:
            level: warning
            message: "Unhandled press {{ press }}"
```

With several triggers, give each an `id:` and branch with
`condition: trigger` / `id: <id>` in `choose`.

## Variable scoping (2025.3, 2025.4)

- 2025.3: variables set by `wait_*` (`wait`) and by `response_variable` reach
  outer scopes, including out of `parallel` branches.
- 2025.4: a `variables` step inside a nested block updates a variable that
  already exists outside. A new name is created at the top-level scope of the
  run.

So a counter now works across a `repeat`:

```yaml
actions:
  - variables:
      lights_on: 0
  - repeat:
      for_each: "{{ label_entities('downstairs') | select('match', 'light.') | list }}"
      sequence:
        - if:
            - condition: template
              value_template: "{{ is_state(repeat.item, 'on') }}"
          then:
            - variables:
                lights_on: "{{ lights_on + 1 }}"   # updates the outer variable
  - action: system_log.write
    data:
      message: "{{ lights_on }} lights on downstairs"
```

Old automations that reused a variable name in an inner block, expecting the
outer value to stay put, now change it. Rename the inner variable.

## Responses, errors and stopping

```yaml
actions:
  - action: weather.get_forecasts
    target:
      entity_id: weather.home
    data:
      type: daily
    response_variable: forecast
  - variables:
      today: "{{ forecast['weather.home'].forecast[0] }}"
  - if:
      - condition: template
        value_template: "{{ today.precipitation_probability | default(0) > 60 }}"
    then:
      - action: notify.mobile_app_anna_phone
        data:
          message: "Rain likely today ({{ today.precipitation_probability }}%)."
```

- `response_variable` is required on actions that always return data, and
  rejected on actions that return nothing.
- `continue_on_error: true` lets the run go on after an action raises an
  error. It does not cover invalid configuration.
- Since 2026.5, Supervisor actions (`hassio.backup_partial`,
  `hassio.addon_start`, `hassio.host_reboot`…) raise on failure. Add
  `continue_on_error: true` if later steps must still run:

```yaml
actions:
  - action: hassio.backup_partial
    data:
      name: "nightly-{{ now().strftime('%Y%m%d') }}"
      homeassistant: true
    continue_on_error: true
  - action: notify.mobile_app_anna_phone
    data:
      message: "Nightly backup step finished."
```

- `stop: "reason"` ends the run; `error: true` marks it failed in the trace.
- `enabled: false` on any trigger, condition or action disables it without
  deleting it.

## Conditions: `for` rules (2026.10)

A state condition with `for:` fails validation when combined with
`attribute:`, or when `state:` refers to another entity. Lists of states with
`for:` are allowed again from 2026.10.2.

```yaml
# Fails since 2026.10
- condition: state
  entity_id: climate.living_room
  attribute: hvac_action
  state: heating
  for: "00:10:00"

# Works: put the duration on a trigger and check the attribute plainly
- condition: state
  entity_id: climate.living_room
  attribute: hvac_action
  state: heating
```

## Conversation trigger

```yaml
- id: "voice_bedtime"
  alias: "Voice - bedtime"
  triggers:
    - trigger: conversation
      command:
        - "good night"
        - "bedtime in {room}"
  actions:
    - action: light.turn_off
      target:
        area_id: "{{ trigger.slots.room | default('bedroom') | lower | replace(' ', '_') }}"
    - set_conversation_response: "Good night."
```

See `ai-and-assist.md` for satellites, AI tasks and LLM tools.

## Other details worth knowing

- `webhook_id` can be a template (2025.10); `local_only` must be a real boolean
  (2026.5).
- Some actions are admin-only when run by hand from the UI (update
  install/skip and Z-Wave lock credentials in 2026.9; `mqtt.publish`,
  `mqtt.dump` and Synology DSM reboot/shutdown in 2026.10). Automations
  still run them.
- Media players report `standby` as `off` since 2025.8.
- Many integrations switched state values to snake_case. Compare states with
  `is_state()` and check them in Developer tools → States before hard-coding.
