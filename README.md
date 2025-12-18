# AC Solenoid Module

This Viam module provides a Switch component for controlling AC solenoids using two GPIO pins that alternate at 60Hz.

## Models

This module provides the following model:

### `biotinker:solenoid-ac:solenoid`

A Switch component that controls an AC solenoid by alternating two GPIO pins at 60Hz when turned on.

#### Behavior

- **Position 0 (Off)**: Both GPIO pins are set LOW
- **Position 1 (On)**: The two GPIO pins alternate at 60Hz
  - Each pin is HIGH for 1/120 second (~8.33ms)
  - Creates 60 complete cycles per second for AC solenoid operation

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
        "pin1": "11",
        "pin2": "13"
      },
      "depends_on": []
    }
  ]
}
```

### Attributes

| Attribute | Type   | Required | Description |
|-----------|--------|----------|-------------|
| `board`   | string | Yes      | Name of the Board component that provides GPIO pin access |
| `pin1`    | string | Yes      | GPIO pin number for the first solenoid connection |
| `pin2`    | string | Yes      | GPIO pin number for the second solenoid connection |

### Example

```json
{
  "board": "local",
  "pin1": "11",
  "pin2": "13"
}
```

## Usage

Once configured, you can control the solenoid using the standard Viam Switch API:

- `set_position(0)` - Turn off (both pins LOW)
- `set_position(1)` - Turn on (pins alternate at 60Hz)
- `get_position()` - Get current state (0 or 1)
- `get_number_of_positions()` - Returns 2

The module automatically handles cleanup when the robot shuts down, ensuring both GPIO pins are set LOW.
