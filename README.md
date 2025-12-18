# AC Solenoid Module

This Viam module provides a Switch component for controlling AC solenoids using a control pin and a PWM pin.

## Models

This module provides the following model:

### `biotinker:solenoid-ac:solenoid`

A Switch component that controls an AC solenoid using a control pin and a PWM-capable GPIO pin.

#### Behavior

- **Position 0 (Off)**:
  - `control_pin` is set LOW
  - `pwm_pin` PWM duty cycle is set to 0% (effectively LOW)
- **Position 1 (On)**:
  - `control_pin` is set HIGH
  - `pwm_pin` outputs PWM at 50% duty cycle at the configured frequency (default 60Hz)

## Configuration

Add this component to your robot configuration with the following attributes:

```json
{
  "components": [
    {
      "name": "my-solenoid",
      "model": "biotinker:solenoid-ac:solenoid",
      "type": "switch",
      "namespace": "rdk",
      "attributes": {
        "board": "local",
        "control_pin": "11",
        "pwm_pin": "13",
        "pwm_frequency": 60
      },
      "depends_on": []
    }
  ]
}
```

### Attributes

| Attribute       | Type   | Required | Description |
|-----------------|--------|----------|-------------|
| `board`         | string | Yes      | Name of the Board component that provides GPIO pin access |
| `control_pin`   | string | Yes      | GPIO pin number for the control signal (HIGH when on, LOW when off) |
| `pwm_pin`       | string | Yes      | GPIO pin number for the PWM signal (must support PWM) |
| `pwm_frequency` | number | No       | PWM frequency in Hz (default: 60) |

### Example

```json
{
  "board": "local",
  "control_pin": "11",
  "pwm_pin": "13",
  "pwm_frequency": 60
}
```

## Usage

Once configured, you can control the solenoid using the standard Viam Switch API:

- `set_position(0)` - Turn off (control_pin LOW, pwm_pin duty cycle 0%)
- `set_position(1)` - Turn on (control_pin HIGH, pwm_pin PWM at 50% duty cycle)
- `get_position()` - Get current state (0 or 1)
- `get_number_of_positions()` - Returns 2

The module automatically handles cleanup when the robot shuts down, ensuring both GPIO pins are set LOW/off.
