import argparse
import asyncio
import logging
import os
import sys

import torch

# Initialize CUDA before any other imports to prevent core dump.
if torch.cuda.is_available():
    torch.cuda.init()

from aiohttp import web
from frame_processor import ComfyStreamFrameProcessor
from pytrickle.frame_overlay import OverlayConfig, OverlayMode
from pytrickle.frame_skipper import FrameSkipConfig
from pytrickle.stream_processor import StreamProcessor
from pytrickle.utils.register import RegisterCapability

from comfystream.exceptions import ComfyStreamTimeoutFilter

logger = logging.getLogger(__name__)

DEFAULT_WITHHELD_TIMEOUT_SECONDS = 0.5


def main():
    parser = argparse.ArgumentParser(
        description="Run comfystream server in BYOC (Bring Your Own Compute) mode using pytrickle."
    )
    parser.add_argument("--port", default=8000, help="Set the server port")
    parser.add_argument("--host", default="0.0.0.0", help="Set the host")
    parser.add_argument(
        "--workspace",
        default=os.getcwd() + "/../ComfyUI",
        help="Set Comfy workspace (Default: ../ComfyUI)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level",
    )
    parser.add_argument(
        "--comfyui-log-level",
        default=None,
        choices=logging._nameToLevel.keys(),
        help="Set the global logging level for ComfyUI",
    )
    parser.add_argument(
        "--comfyui-inference-log-level",
        default=None,
        choices=logging._nameToLevel.keys(),
        help="Set the logging level for ComfyUI inference",
    )
    parser.add_argument(
        "--disable-frame-skip",
        default=False,
        action="store_true",
        help="Disable adaptive frame skipping based on queue sizes (enabled by default)",
    )
    parser.add_argument(
        "--width",
        default=512,
        type=int,
        help="Default video width for processing",
    )
    parser.add_argument(
        "--height",
        default=512,
        type=int,
        help="Default video height for processing",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("comfy.model_detection").setLevel(logging.WARNING)

    # Allow overriding of ComfyUI log levels.
    if args.comfyui_log_level:
        log_level = logging._nameToLevel.get(args.comfyui_log_level.upper())
        logging.getLogger("comfy").setLevel(log_level)

    # Add ComfyStream timeout filter to suppress verbose execution logging
    timeout_filter = ComfyStreamTimeoutFilter()
    logging.getLogger("comfy.cmd.execution").addFilter(timeout_filter)
    logging.getLogger("comfystream").addFilter(timeout_filter)

    def force_print(*args, **kwargs):
        print(*args, **kwargs, flush=True)
        sys.stdout.flush()

    logger.info("Starting ComfyStream BYOC server with pytrickle StreamProcessor...")
    logger.info(
        "Send initial workflow parameters (width/height/prompts/warmup) via /stream/start "
        "params; runtime updates now apply incremental changes only."
    )

    # Create frame processor with configuration
    frame_processor = ComfyStreamFrameProcessor(
        width=args.width,
        height=args.height,
        workspace=args.workspace,
        disable_cuda_malloc=True,
        gpu_only=True,
        preview_method="none",
        blacklist_custom_nodes=["ComfyUI-Manager"],
        logging_level=args.comfyui_log_level,
        comfyui_inference_log_level=args.comfyui_inference_log_level,
    )

    # Create frame skip configuration only if enabled
    frame_skip_config = None
    if args.disable_frame_skip:
        logger.info("Frame skipping disabled")
    else:
        frame_skip_config = FrameSkipConfig()
        logger.info("Frame skipping enabled: adaptive skipping based on queue sizes")

    # Create StreamProcessor with frame processor
    processor = StreamProcessor(
        video_processor=frame_processor.process_video_async,
        audio_processor=frame_processor.process_audio_async,
        model_loader=frame_processor.load_model,
        param_updater=frame_processor.update_params,
        on_stream_start=frame_processor.on_stream_start,
        on_stream_stop=frame_processor.on_stream_stop,
        # Align processor name with capability for consistent logs
        name=(os.getenv("CAPABILITY_NAME") or "comfystream"),
        port=int(args.port),
        host=args.host,
        frame_skip_config=frame_skip_config,
        overlay_config=OverlayConfig(
            mode=OverlayMode.PROGRESSBAR,
            message="Loading...",
            enabled=True,
            auto_timeout_seconds=DEFAULT_WITHHELD_TIMEOUT_SECONDS,
            frame_count_to_disable=20,
        ),
        # Ensure server metadata reflects the desired capability name
        capability_name=(os.getenv("CAPABILITY_NAME") or "comfystream"),
        # server_kwargs...
        route_prefix="/",
    )

    # Set the stream processor reference for text data publishing
    frame_processor.set_stream_processor(processor)

    logger.info("Startup warmup runs automatically as part of on_stream_start.")

    # Create async startup function for orchestrator registration
    async def register_orchestrator_startup(app):
        try:
            orch_url = os.getenv("ORCH_URL")

            if orch_url and os.getenv("ORCH_SECRET", None):
                # CAPABILITY_URL always overrides host:port from args
                capability_url = os.getenv("CAPABILITY_URL") or f"http://{args.host}:{args.port}"

                os.environ.update(
                    {
                        "CAPABILITY_NAME": os.getenv("CAPABILITY_NAME") or "comfystream",
                        "CAPABILITY_DESCRIPTION": "ComfyUI streaming processor",
                        "CAPABILITY_URL": capability_url,
                        "CAPABILITY_CAPACITY": "1",
                        "ORCH_URL": orch_url,
                        "ORCH_SECRET": os.getenv("ORCH_SECRET", None),
                    }
                )

                result = await RegisterCapability.register(
                    logger=logger, capability_name=os.getenv("CAPABILITY_NAME") or "comfystream"
                )
                if result:
                    logger.info(f"Registered capability: {result.geturl()}")
                # Clear ORCH_SECRET from environment after use for security
                os.environ.pop("ORCH_SECRET", None)
        except Exception as e:
            logger.error(f"Orchestrator registration failed: {e}")
            # Clear ORCH_SECRET from environment even on error
            os.environ.pop("ORCH_SECRET", None)

    # Add registration to startup hooks
    processor.server.app.on_startup.append(register_orchestrator_startup)

    # Run the processor
    processor.run()


if __name__ == "__main__":
    main()
