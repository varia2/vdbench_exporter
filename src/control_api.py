from pathlib import Path

from fastapi import FastAPI


def create_control_api(
        controller,
        runtime_state,
        output_file,
        stop_mode
):
    app = FastAPI()

    @app.get("/health")
    async def health():
        output_exists = Path(output_file).exists()

        stale = False

        if runtime_state.seconds_since_last_update:
            stale = (
                    runtime_state.seconds_since_last_update > 30
            )

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
                runtime_state.uptime_seconds
        }

    @app.post("/shutdown")
    async def shutdown():
        controller.stop()
        return {"status": "stopping"}

    return app