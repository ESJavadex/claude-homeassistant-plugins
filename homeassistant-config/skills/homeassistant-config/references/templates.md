# Home Assistant Template Sensors

Comprehensive guide to creating template sensors with Jinja2.

## Basic Template Sensors

### Simple State Calculation
```yaml
template:
  - sensor:
      - name: "Total Power Usage"
        unit_of_measurement: "W"
        device_class: power
        state_class: measurement
        state: >
          {{ (states('sensor.plug_1_power') | float(0) +
              states('sensor.plug_2_power') | float(0) +
              states('sensor.plug_3_power') | float(0)) | round(1) }}
```

### Average Value
```yaml
template:
  - sensor:
      - name: "Average Indoor Temperature"
        unit_of_measurement: "C"
        device_class: temperature
        state: >
          {% set temps = [
            states('sensor.living_room_temp') | float(0),
            states('sensor.bedroom_temp') | float(0),
            states('sensor.kitchen_temp') | float(0)
          ] | reject('eq', 0) | list %}
          {{ (temps | sum / temps | count) | round(1) if temps else 'unknown' }}
```

### Min/Max Value
```yaml
template:
  - sensor:
      - name: "Highest Temperature"
        unit_of_measurement: "C"
        device_class: temperature
        state: >
          {% set temps = [
            states('sensor.room_1_temp') | float,
            states('sensor.room_2_temp') | float,
            states('sensor.room_3_temp') | float
          ] %}
          {{ temps | max }}

      - name: "Lowest Temperature"
        unit_of_measurement: "C"
        device_class: temperature
        state: >
          {% set temps = [
            states('sensor.room_1_temp') | float,
            states('sensor.room_2_temp') | float,
            states('sensor.room_3_temp') | float
          ] %}
          {{ temps | min }}
```

## Date and Time Templates

### Time Until Event
```yaml
template:
  - sensor:
      - name: "Time Until Sunset"
        state: >
          {% set sunset = as_timestamp(state_attr('sun.sun', 'next_setting')) %}
          {% set now_ts = as_timestamp(now()) %}
          {% set diff = sunset - now_ts %}
          {% if diff > 0 %}
            {{ (diff / 3600) | int }}h {{ ((diff % 3600) / 60) | int }}m
          {% else %}
            Past sunset
          {% endif %}
```

### Day of Week
```yaml
template:
  - sensor:
      - name: "Day Type"
        state: >
          {% set day = now().isoweekday() %}
          {% if day in [6, 7] %}
            Weekend
          {% else %}
            Weekday
          {% endif %}
```

### Time Period
```yaml
template:
  - sensor:
      - name: "Time of Day"
        state: >
          {% set hour = now().hour %}
          {% if 5 <= hour < 12 %}
            Morning
          {% elif 12 <= hour < 17 %}
            Afternoon
          {% elif 17 <= hour < 21 %}
            Evening
          {% else %}
            Night
          {% endif %}
```

## Attribute Templates

### Extract Attributes
```yaml
template:
  - sensor:
      - name: "Thermostat Target"
        unit_of_measurement: "C"
        state: "{{ state_attr('climate.thermostat', 'temperature') }}"

      - name: "Thermostat HVAC Action"
        state: "{{ state_attr('climate.thermostat', 'hvac_action') }}"
```

### With Custom Attributes
```yaml
template:
  - sensor:
      - name: "Solar Production"
        unit_of_measurement: "W"
        device_class: power
        state: "{{ states('sensor.solar_power') }}"
        attributes:
          daily_total: "{{ states('sensor.solar_daily_energy') }}"
          efficiency: >
            {% set power = states('sensor.solar_power') | float(0) %}
            {% set max_power = 5000 %}
            {{ ((power / max_power) * 100) | round(1) }}%
          status: >
            {% set power = states('sensor.solar_power') | float(0) %}
            {% if power > 3000 %}
              Excellent
            {% elif power > 1000 %}
              Good
            {% elif power > 0 %}
              Low
            {% else %}
              Not Producing
            {% endif %}
```

## Binary Sensor Templates

### Simple Threshold
```yaml
template:
  - binary_sensor:
      - name: "High Temperature Alert"
        device_class: heat
        state: "{{ states('sensor.temperature') | float > 30 }}"
```

### Complex Condition
```yaml
template:
  - binary_sensor:
      - name: "Home Occupied"
        device_class: occupancy
        state: >
          {{ is_state('person.john', 'home') or
             is_state('person.jane', 'home') or
             is_state('binary_sensor.motion', 'on') }}
        delay_off:
          minutes: 10
```

### Workday Sensor
```yaml
template:
  - binary_sensor:
      - name: "Workday"
        state: >
          {% set day = now().isoweekday() %}
          {{ day <= 5 }}
```

## Availability Templates

### Basic Availability
```yaml
template:
  - sensor:
      - name: "Calculated Value"
        state: "{{ states('sensor.source') | float * 2 }}"
        availability: >
          {{ states('sensor.source') not in ['unknown', 'unavailable', 'none'] }}
```

### Multiple Dependencies
```yaml
template:
  - sensor:
      - name: "Combined Sensor"
        state: >
          {{ states('sensor.a') | float + states('sensor.b') | float }}
        availability: >
          {{ states('sensor.a') not in ['unknown', 'unavailable'] and
             states('sensor.b') not in ['unknown', 'unavailable'] }}
```

## Icon Templates

### Dynamic Icons
```yaml
template:
  - sensor:
      - name: "Battery Level"
        unit_of_measurement: "%"
        state: "{{ states('sensor.phone_battery') }}"
        icon: >
          {% set level = states('sensor.phone_battery') | int(0) %}
          {% if level >= 90 %}
            mdi:battery
          {% elif level >= 70 %}
            mdi:battery-80
          {% elif level >= 50 %}
            mdi:battery-60
          {% elif level >= 30 %}
            mdi:battery-40
          {% elif level >= 10 %}
            mdi:battery-20
          {% else %}
            mdi:battery-alert
          {% endif %}
```

## Loop Templates

### Count Entities in State
```yaml
template:
  - sensor:
      - name: "Lights On Count"
        state: >
          {{ states.light | selectattr('state', 'eq', 'on') | list | count }}

      - name: "Open Doors"
        state: >
          {{ states.binary_sensor
             | selectattr('attributes.device_class', 'eq', 'door')
             | selectattr('state', 'eq', 'on')
             | list | count }}
```

### List Active Entities
```yaml
template:
  - sensor:
      - name: "Active Lights"
        state: >
          {% set lights = states.light | selectattr('state', 'eq', 'on') | list %}
          {{ lights | count }} lights on
        attributes:
          list: >
            {{ states.light
               | selectattr('state', 'eq', 'on')
               | map(attribute='name')
               | list }}
```

## Trigger-Based Templates

### Last Changed
```yaml
template:
  - trigger:
      - trigger: state
        entity_id: binary_sensor.front_door
        to: "on"
    sensor:
      - name: "Last Door Open"
        state: "{{ now().strftime('%H:%M:%S') }}"
        attributes:
          timestamp: "{{ now().isoformat() }}"
```

### Event Counter
```yaml
template:
  - trigger:
      - trigger: state
        entity_id: binary_sensor.motion
        to: "on"
    sensor:
      - name: "Motion Events Today"
        state: "{{ (this.state | int(0)) + 1 }}"
```

## Utility Helpers

### Format Numbers
```yaml
template:
  - sensor:
      - name: "Energy Cost"
        unit_of_measurement: "EUR"
        state: >
          {% set kwh = states('sensor.energy_today') | float(0) %}
          {% set rate = 0.25 %}
          {{ (kwh * rate) | round(2) }}
```

### Unit Conversion
```yaml
template:
  - sensor:
      - name: "Temperature Fahrenheit"
        unit_of_measurement: "F"
        state: >
          {% set celsius = states('sensor.temperature') | float(0) %}
          {{ ((celsius * 9/5) + 32) | round(1) }}
```
