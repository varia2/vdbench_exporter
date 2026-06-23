import asyncio
import logging

logger = logging.getLogger(__name__)


class ShutdownController:
    def __init__(self):
        self._event = asyncio.Event()

    def stop(self):
        logger.info("Shutdown signal received")
        self._event.set()

    async def wait(self):
        await self._event.wait()

    @property
    def is_stopped(self):
        return self._event.is_set()