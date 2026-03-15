from typing import (Any, ClassVar, Dict, Final, List, Mapping, Optional,
                    Sequence, Tuple)

from typing_extensions import Self
from viam.components.component_base import ComponentBase
from viam.components.switch import *
from viam.components.board import Board
from viam.proto.app.robot import ComponentConfig
from viam.proto.common import Geometry, ResourceName
from viam.resource.base import ResourceBase
from viam.resource.easy_resource import EasyResource
from viam.resource.types import Model, ModelFamily
from viam.utils import ValueTypes


class Solenoid(Switch, EasyResource):
    # To enable debug-level logging, either run viam-server with the --debug option,
    # or configure your resource/machine to display debug logs.
    MODEL: ClassVar[Model] = Model(ModelFamily("biotinker", "solenoid-ac"), "solenoid")

    # Shared PWM state: one PWM pin drives all solenoids, keyed by "board_name:pin"
    _active_pwm: ClassVar[Dict[str, int]] = {}  # key -> frequency in Hz
    _instance_count: ClassVar[Dict[str, int]] = {}  # key -> instance count

    def __init__(self, name: str):
        super().__init__(name)
        self.board: Optional[Board] = None
        self.board_name: Optional[str] = None
        self.control_pin: Optional[str] = None
        self.pwm_pin: Optional[str] = None
        self.pwm_frequency: int = 60  # Default 60Hz
        self.position: int = 0  # 0 = off, 1 = on
        self._pwm_key: Optional[str] = None

    @classmethod
    def new(
        cls, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]
    ) -> Self:
        """This method creates a new instance of this Switch component.
        The default implementation sets the name from the `config` parameter.

        Args:
            config (ComponentConfig): The configuration for this resource
            dependencies (Mapping[ResourceName, ResourceBase]): The dependencies (both required and optional)

        Returns:
            Self: The resource
        """
        instance = super().new(config, dependencies)

        # Get board from dependencies
        board_name = config.attributes.fields["board"].string_value
        instance.board = dependencies[Board.get_resource_name(board_name)]
        instance.board_name = board_name

        # Get pin numbers from config
        instance.control_pin = config.attributes.fields["control_pin"].string_value
        instance.pwm_pin = config.attributes.fields["pwm_pin"].string_value

        # Get optional PWM frequency (defaults to 60Hz if not specified)
        if "pwm_frequency" in config.attributes.fields:
            instance.pwm_frequency = int(config.attributes.fields["pwm_frequency"].number_value)

        # Track this instance for the shared PWM pin
        instance._pwm_key = f"{board_name}:{instance.pwm_pin}"
        cls._instance_count[instance._pwm_key] = cls._instance_count.get(instance._pwm_key, 0) + 1

        return instance

    @classmethod
    def validate_config(
        cls, config: ComponentConfig
    ) -> Tuple[Sequence[str], Sequence[str]]:
        """This method allows you to validate the configuration object received from the machine,
        as well as to return any required dependencies or optional dependencies based on that `config`.

        Args:
            config (ComponentConfig): The configuration for this resource

        Returns:
            Tuple[Sequence[str], Sequence[str]]: A tuple where the
                first element is a list of required dependencies and the
                second element is a list of optional dependencies
        """
        # Validate required fields
        board_name = config.attributes.fields.get("board")
        control_pin = config.attributes.fields.get("control_pin")
        pwm_pin = config.attributes.fields.get("pwm_pin")

        if not board_name or not board_name.string_value:
            raise ValueError("'board' attribute is required in config")
        if not control_pin or not control_pin.string_value:
            raise ValueError("'control_pin' attribute is required in config")
        if not pwm_pin or not pwm_pin.string_value:
            raise ValueError("'pwm_pin' attribute is required in config")

        # Validate optional pwm_frequency if provided
        pwm_frequency = config.attributes.fields.get("pwm_frequency")
        if pwm_frequency and pwm_frequency.number_value <= 0:
            raise ValueError("'pwm_frequency' must be greater than 0")

        # Return board as a required dependency
        return [board_name.string_value], []

    async def _ensure_pwm_started(self):
        """Start the shared PWM signal if not already running for this pin."""
        if self._pwm_key in Solenoid._active_pwm:
            existing_freq = Solenoid._active_pwm[self._pwm_key]
            if existing_freq != self.pwm_frequency:
                raise ValueError(
                    f"PWM pin {self.pwm_pin} is already running at {existing_freq}Hz, "
                    f"but this solenoid requests {self.pwm_frequency}Hz. "
                    f"All solenoids sharing a PWM pin must use the same frequency."
                )
            return
        pwm_gpio = await self.board.gpio_pin_by_name(self.pwm_pin)
        await pwm_gpio.set_pwm_frequency(self.pwm_frequency)
        await pwm_gpio.set_pwm(0.5)  # 50% duty cycle
        Solenoid._active_pwm[self._pwm_key] = self.pwm_frequency
        self.logger.info(f"Started shared PWM at {self.pwm_frequency}Hz on pin {self.pwm_pin}")

    async def get_position(
        self,
        *,
        extra: Optional[Mapping[str, Any]] = None,
        timeout: Optional[float] = None,
        **kwargs
    ) -> int:
        """Returns the current position (0=off, 1=on)"""
        return self.position

    async def set_position(
        self,
        position: int,
        *,
        extra: Optional[Mapping[str, Any]] = None,
        timeout: Optional[float] = None,
        **kwargs
    ) -> None:
        """Sets the position (0=off, 1=on)"""
        if position not in [0, 1]:
            raise ValueError(f"Position must be 0 or 1, got {position}")

        await self._ensure_pwm_started()

        self.position = position
        control_gpio = await self.board.gpio_pin_by_name(self.control_pin)
        await control_gpio.set(position == 1)

    async def get_number_of_positions(
        self,
        *,
        extra: Optional[Mapping[str, Any]] = None,
        timeout: Optional[float] = None,
        **kwargs
    ) -> int:
        """Returns the number of positions (2: off and on)"""
        return 2

    async def close(self):
        """Cleanup when the component is closed"""
        if self.board and self.control_pin:
            try:
                control_gpio = await self.board.gpio_pin_by_name(self.control_pin)
                await control_gpio.set(False)
            except Exception as e:
                self.logger.error(f"Error setting control pin low during close: {e}")

        # Decrement instance count; stop PWM only when last instance closes
        if self._pwm_key:
            Solenoid._instance_count[self._pwm_key] = Solenoid._instance_count.get(self._pwm_key, 1) - 1
            if Solenoid._instance_count[self._pwm_key] <= 0:
                try:
                    if self.board and self.pwm_pin:
                        pwm_gpio = await self.board.gpio_pin_by_name(self.pwm_pin)
                        await pwm_gpio.set_pwm(0.0)
                        self.logger.info(f"Stopped shared PWM on pin {self.pwm_pin}")
                except Exception as e:
                    self.logger.error(f"Error stopping PWM during close: {e}")
                Solenoid._active_pwm.pop(self._pwm_key, None)
                Solenoid._instance_count.pop(self._pwm_key, None)

    async def do_command(
        self,
        command: Mapping[str, ValueTypes],
        *,
        timeout: Optional[float] = None,
        **kwargs
    ) -> Mapping[str, ValueTypes]:
        """Handle custom commands"""
        return {}

    async def get_geometries(
        self, *, extra: Optional[Dict[str, Any]] = None, timeout: Optional[float] = None
    ) -> Sequence[Geometry]:
        """Return geometries (empty for this component)"""
        return []

