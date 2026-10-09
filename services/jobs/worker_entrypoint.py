"""Standalone Background Worker Entrypoint for SevaHealth AI.

Executes asynchronous jobs from the queue without blocking the API or frontend:
- Document OCR
- Wearable timeseries backfill
- Deep Multi-Agent / LLM clinical summaries
- District/State population intelligence aggregation
- High-throughput notification dispatch
"""

import asyncio
import signal
import sys
import os
from aiohttp import web
import structlog

from packages.config.settings import settings
from packages.queue.manager import job_queue_manager

logger = structlog.get_logger(__name__)


async def health_handler(request):
    """Worker liveness and readiness probe for Docker / K8s."""
    is_healthy = job_queue_manager._is_running
    status_code = 200 if is_healthy else 503
    return web.json_response(
        {
            "status": "HEALTHY" if is_healthy else "UNHEALTHY",
            "service": "sevahealth-worker",
            "environment": settings.ENVIRONMENT,
            "version": settings.APP_VERSION,
            "is_running": is_healthy,
        },
        status=status_code,
    )


async def run_worker():
    """Main worker event loop."""
    logger.info(
        "sevahealth_worker_starting",
        environment=settings.ENVIRONMENT,
        version=settings.APP_VERSION,
    )

    # Start workers
    concurrency = int(os.getenv("WORKER_CONCURRENCY", "4"))
    await job_queue_manager.start_workers(concurrency_per_queue=concurrency)
    logger.info("sevahealth_worker_started", concurrency=concurrency)

    # Start minimal HTTP health probe server on port 8002
    health_app = web.Application()
    health_app.router.add_get("/health", health_handler)
    health_app.router.add_get("/metrics", lambda r: web.json_response(job_queue_manager.get_metrics()))
    
    runner = web.AppRunner(health_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("WORKER_HEALTH_PORT", "8002")))
    await site.start()
    logger.info("sevahealth_worker_health_probe_listening", port=int(os.getenv("WORKER_HEALTH_PORT", "8002")))

    stop_event = asyncio.Event()

    def _signal_handler():
        logger.info("worker_shutdown_signal_received")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            # Signal handling on Windows platform
            pass

    try:
        await stop_event.wait()
    except asyncio.CancelledError:
        pass
    finally:
        logger.info("draining_worker_queue_and_shutting_down")
        await job_queue_manager.stop_workers()
        await runner.cleanup()
        logger.info("sevahealth_worker_stopped_cleanly")


if __name__ == "__main__":
    try:
        asyncio.run(run_worker())
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
