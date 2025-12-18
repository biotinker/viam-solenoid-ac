from typing import (Any, ClassVar, Dict, Final, List, Mapping, Optional,
                    Sequence, Tuple)
import asyncio

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

    def __init__(self, name: str):
        super().__init__(name)
        self.board: Optional[Board] = None
        self.pin1: Optional[str] = None
        self.pin2: Optional[str] = None
        self.position: int = 0  # 0 = off, 1 = on
        self.alternating_task: Optional[asyncio.Task] = None

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

        # Get pin numbers from config
        instance.pin1 = config.attributes.fields["pin1"].string_value
        instance.pin2 = config.attributes.fields["pin2"].string_value

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
        pin1 = config.attributes.fields.get("pin1")
        pin2 = config.attributes.fields.get("pin2")

        if not board_name or not board_name.string_value:
            raise ValueError("'board' attribute is required in config")
        if not pin1 or not pin1.string_value:
            raise ValueError("'pin1' attribute is required in config")
        if not pin2 or not pin2.string_value:
            raise ValueError("'pin2' attribute is required in config")

        # Return board as a required dependency
        return [board_name.string_value], []

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

        self.position = position

        # Stop existing alternating task if running
        if self.alternating_task and not self.alternating_task.done():
            self.alternating_task.cancel()
            try:
                await self.alternating_task
            except asyncio.CancelledError:
                pass

        if position == 0:
            # Both pins low
            pin1_gpio = await self.board.gpio_pin_by_name(self.pin1)
            pin2_gpio = await self.board.gpio_pin_by_name(self.pin2)
            await pin1_gpio.set(False)
            await pin2_gpio.set(False)
        else:
            # Start alternating at 60Hz
            self.alternating_task = asyncio.create_task(self._alternate_pins())

    async def _alternate_pins(self):
        """Alternates the two GPIO pins at 60Hz (each pin high for 1/120 sec)"""
        pin1_gpio = await self.board.gpio_pin_by_name(self.pin1)
        pin2_gpio = await self.board.gpio_pin_by_name(self.pin2)

        # 60Hz means 60 cycles per second
        # Each cycle: pin1 high, then pin2 high
        # So each pin is high for 1/120 seconds (~8.33ms)
        period = 1.0 / 120.0  # Time each pin stays high

        try:
            while True:
                # Pin 1 high, Pin 2 low
                await pin1_gpio.set(True)
                await pin2_gpio.set(False)
                await asyncio.sleep(period)

                # Pin 1 low, Pin 2 high
                await pin1_gpio.set(False)
                await pin2_gpio.set(True)
                await asyncio.sleep(period)
        except asyncio.CancelledError:
            # Ensure both pins are low when cancelled
            await pin1_gpio.set(False)
            await pin2_gpio.set(False)
            raise

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
        # Stop the alternating task and set both pins low
        if self.alternating_task and not self.alternating_task.done():
            self.alternating_task.cancel()
            try:
                await self.alternating_task
            except asyncio.CancelledError:
                pass

        # Ensure both pins are low
        if self.board and self.pin1 and self.pin2:
            try:
                pin1_gpio = await self.board.gpio_pin_by_name(self.pin1)
                pin2_gpio = await self.board.gpio_pin_by_name(self.pin2)
                await pin1_gpio.set(False)
                await pin2_gpio.set(False)
            except Exception as e:
                self.logger.error(f"Error setting pins low during close: {e}")

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

