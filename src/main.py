import asyncio
from viam.module.module import Module
try:
    from models.solenoid import Solenoid
except ModuleNotFoundError:
    # when running as local module with run.sh
    from .models.solenoid import Solenoid


if __name__ == '__main__':
    asyncio.run(Module.run_from_registry())
