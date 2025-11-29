# Home Assistant Configuration Skill

Create and manage Home Assistant YAML configuration files including automations, scripts, templates, and file organization.

## YAML Requirements

- **Indentation**: 2 spaces per level (never tabs)
- **Strings**: Quote boolean-like values ("on", "off", "yes", "no")
- **Lists**: Use `-` prefix with proper indentation
- **Comments**: Use `#` for inline documentation

## File Organization

### Basic Includes
```yaml
# configuration.yaml
automation: !include automations.yaml
script: !include scripts.yaml
sensor: !include sensors.yaml
```

### Directory Includes
```yaml
# Merge all files in directory
automation: !include_dir_merge_list automations/
sensor: !include_dir_merge_list sensors/
```

### Secrets Management
```yaml
# secrets.yaml
mqtt_password: "super_secret_password"
api_key: "your-api-key-here"

# configuration.yaml
mqtt:
  password: !secret mqtt_password
```

## Automations (2024+ Syntax)

### Basic Structure
```yaml
automation:
  - alias: "Descriptive Name"
    id: unique_automation_id
    description: "What this automation does"
    mode: single  # single, restart, queued, parallel
    triggers:
      - trigger: state
        entity_id: binary_sensor.motion
        to: "on"
    conditions:
      - condition: time
        after: "sunset"
    actions:
      - action: light.turn_on
        target:
          entity_id: light.living_room
```

### Common Triggers

**State Trigger**
```yaml
triggers:
  - trigger: state
    entity_id: sensor.temperature
    from: "off"
    to: "on"
    for:
      minutes: 5
```

**Time Trigger**
```yaml
triggers:
  - trigger: time
    at: "07:00:00"
```

**Numeric State Trigger**
```yaml
triggers:
  - trigger: numeric_state
    entity_id: sensor.temperature
    above: 25
    below: 30
```

**Sun Trigger**
```yaml
triggers:
  - trigger: sun
    event: sunset
    offset: "-00:30:00"
```

**Template Trigger**
```yaml
triggers:
  - trigger: template
    value_template: "{{ states('sensor.power') | float > 1000 }}"
```

### Common Actions

**Service Call**
```yaml
actions:
  - action: light.turn_on
    target:
      entity_id: light.bedroom
    data:
      brightness_pct: 50
      color_temp: 350
```

**Delay**
```yaml
actions:
  - delay:
      seconds: 30
```

**Conditional (Choose)**
```yaml
actions:
  - choose:
      - conditions:
          - condition: state
            entity_id: sun.sun
            state: "below_horizon"
        sequence:
          - action: light.turn_on
            target:
              entity_id: light.porch
    default:
      - action: light.turn_off
        target:
          entity_id: light.porch
```

**Repeat**
```yaml
actions:
  - repeat:
      count: 3
      sequence:
        - action: notify.mobile_app
          data:
            message: "Alert!"
        - delay:
            minutes: 1
```

## Scripts

```yaml
script:
  morning_routine:
    alias: "Morning Routine"
    description: "Start the day"
    fields:
      brightness:
        description: "Light brightness"
        example: 80
        default: 100
        selector:
          number:
            min: 0
            max: 100
    sequence:
      - action: light.turn_on
        target:
          area_id: bedroom
        data:
          brightness_pct: "{{ brightness }}"
      - action: media_player.play_media
        target:
          entity_id: media_player.speaker
        data:
          media_content_id: "morning_news"
          media_content_type: "music"
```

## Jinja2 Templates

### State Functions
```yaml
# Get state
{{ states('sensor.temperature') }}

# Get attribute
{{ state_attr('climate.thermostat', 'current_temperature') }}

# Check if entity exists
{{ states.sensor.temperature is defined }}
```

### Filters and Tests
```yaml
# Convert types
{{ states('sensor.temp') | float(0) }}
{{ states('sensor.count') | int(0) }}

# Math operations
{{ states('sensor.power') | float * 0.15 | round(2) }}

# Date/time
{{ now().strftime('%H:%M') }}
{{ as_timestamp(now()) }}
```

### Template Sensors
```yaml
template:
  - sensor:
      - name: "Total Power Usage"
        unit_of_measurement: "W"
        state: >
          {{ states('sensor.plug_1_power') | float(0) +
             states('sensor.plug_2_power') | float(0) }}
        availability: >
          {{ states('sensor.plug_1_power') not in ['unknown', 'unavailable'] }}
```

## Validation Tools

1. **Developer Tools > YAML**: Check configuration syntax
2. **Developer Tools > Template**: Test Jinja2 templates
3. **Developer Tools > States**: Verify entity states
4. **Logs**: Enable debug logging for troubleshooting

```yaml
logger:
  default: info
  logs:
    homeassistant.components.automation: debug
```

## Common Issues

| Problem | Solution |
|---------|----------|
| Tab characters | Replace with 2 spaces |
| Unquoted booleans | Quote "on", "off", "yes", "no" |
| Template errors | Test in Developer Tools first |
| Entity not found | Check entity_id spelling |
| Automation not firing | Verify trigger conditions in trace |

## Reference Files

For detailed patterns and examples, see:
- `references/patterns.md` - Common automation patterns
- `references/templates.md` - Template sensor examples
- `references/troubleshooting.md` - Error solutions
- `references/best-practices.md` - Optimization tips
- `examples/` - Complete working configurations
