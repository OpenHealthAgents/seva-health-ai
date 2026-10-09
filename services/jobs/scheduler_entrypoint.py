"""Standalone Periodic Scheduler Entrypoint for SevaHealth AI.

Orchestrates automated background surveillance, scheduled cohort checks,
daily habit reminders, and periodic aggregate population rollups.
"""

import asyncio
import signal
import sys
import os
from datetime import datetime, timezone
from aiohttp import web
import structlog

from packages.config.settings import settings

logger = structlog.get_logger(__name__)


class CronScheduler:
    """Production-grade periodic task runner for public health surveillance."""

    def __init__(self):
        self.is_running = False
        self._tasks = []
        self._last_runs = {}

    async def start(self):
        self.is_running = True
        logger.info(
            "scheduler_started",
            environment=settings.ENVIRONMENT,
            version=settings.APP_VERSION,
        )
        self._tasks.append(asyncio.create_task(self._run_habit_reminders_loop()))
        self._tasks.append(asyncio.create_task(self._run_risk_surveillance_loop()))
        self._tasks.append(asyncio.create_task(self._run_population_rollup_loop()))

    async def stop(self):
        self.is_running = False
        logger.info("scheduler_stopping")
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        logger.info("scheduler_stopped_cleanly")

    async def _run_habit_reminders_loop(self):
        """Simulates periodic habit reminder evaluation loop."""
        interval = int(os.getenv("HABIT_REMINDER_INTERVAL_SEC", "300"))
        while self.is_running:
            try:
                self._last_runs["habit_reminders"] = datetime.now(timezone.utc).isoformat()
                logger.info("scheduler_executing_habit_reminders_cycle")
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("scheduler_habit_reminders_error", error=str(e))
                await asyncio.sleep(30)

    async def _run_risk_surveillance_loop(self):
        """Simulates periodic cohort risk surveillance."""
        interval = int(os.getenv("RISK_SURVEILLANCE_INTERVAL_SEC", "600"))
        while self.is_running:
            try:
                self._last_runs["risk_surveillance"] = datetime.now(timezone.utc).isoformat()
                logger.info("scheduler_executing_risk_surveillance_cycle")
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("scheduler_risk_surveillance_error", error=str(e))
                await asyncio.sleep(60)

    async def _run_population_rollup_loop(self):
        """Simulates periodic district/state aggregate population rollup."""
        interval = int(os.getenv("POPULATION_ROLLUP_INTERVAL_SEC", "1800"))
        while self.is_running:
            try:
                self._last_runs["population_rollup"] = datetime.now(timezone.utc).isoformat()
                logger.info("scheduler_executing_population_rollup_cycle")
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("scheduler_population_rollup_error", error=str(e))
                await asyncio.sleep(120)


scheduler = CronScheduler()


async def health_handler(request):
    """Scheduler liveness and readiness probe for Docker / K8s."""
    is_healthy = scheduler.is_running
    status_code = 200 if is_healthy else 503
    return web.json_response(
        {
            "status": "HEALTHY" if is_healthy else "UNHEALTHY",
            "service": "sevahealth-scheduler",
            "environment": settings.ENVIRONMENT,
            "version": settings.APP_VERSION,
            "is_running": is_healthy,
            "last_runs": scheduler._last_runs,
        },
        status=status_code,
    )


async def run_scheduler_service():
    """Main scheduler service runner."""
    await scheduler.start()

    # Minimal HTTP health server on port 8003
    health_app = web.Application()
    health_app.router.add_get("/health", health_handler)

    runner = web.AppRunner(health_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("SCHEDULER_HEALTH_PORT", "8003")))
    await site.start()
    logger.info("scheduler_health_probe_listening", port=int(os.getenv("SCHEDULER_HEALTH_PORT", "8003")))

    stop_event = asyncio.Event()

    def _signal_handler():
        logger.info("scheduler_shutdown_signal_received")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            pass

    try:
        await stop_event.wait()
    except asyncio.CancelledError:
        pass
    finally:
        await scheduler.stop()
        await runner.cleanup()
        logger.info("sevahealth_scheduler_stopped")


if __name__ == "__main__":
    try:
        asyncio.run(run_scheduler_service())
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
