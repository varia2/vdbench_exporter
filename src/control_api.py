from pathlib import Path

from fastapi import FastAPI
import logging

logger = logging.getLogger(__name__)

def create_control_api(
        controller,
        runtime_state,
        output_file,
        stop_mode
):
    app = FastAPI()

    @app.get("/health")
    async def health():
        logger.info("HEALTH: entered")
        output_exists = Path(output_file).exists() if output_file else False

        stale = False

        if runtime_state.seconds_since_last_update:
            stale = (
                    runtime_state.seconds_since_last_update > 30
            )
        logger.info("HEALTH: returning payload")
        return {
            "status": "degraded" if stale else "ok",

            "reader_running":
                runtime_state.reader_running,

            "shutdown_requested":
                controller.is_stopped,

            "output_file_exists":
                output_exists,

            "last_metrics_update":
                runtime_state.last_metrics_update,

            "seconds_since_last_update":
                runtime_state.seconds_since_last_update,

            "mode":
                stop_mode,

            "uptime_seconds":
                runtime_state.uptime_seconds,

            "last_raw_line":
                runtime_state.last_raw_line,
            "last_metrics": {
                "iops": runtime_state.last_metrics.iops if runtime_state.last_metrics else None,
                "latency": runtime_state.last_metrics.latency_ms if runtime_state.last_metrics else None,
                "throughput": runtime_state.last_metrics.throughput_bytes if runtime_state.last_metrics else None,
            },

            "offline_completed": runtime_state.offline_completed,
        }

    @app.post("/shutdown")
    async def shutdown():
        controller.stop()
        return {"status": "stopping"}

    return app