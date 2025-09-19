import argparse
import asyncio
import json
import logging
import os
import sys
import time
import secrets
import torch

# Initialize CUDA before any other imports to prevent core dump.
if torch.cuda.is_available():
    torch.cuda.init()


from aiohttp import web, MultipartWriter
from aiohttp_cors import setup as setup_cors, ResourceOptions
from aiohttp import web
from aiortc import (
    MediaStreamTrack,
    RTCConfiguration,
    RTCIceServer,
    RTCPeerConnection,
    RTCSessionDescription,
)
# Import HTTP streaming modules
from http_streaming.routes import setup_routes
from aiortc.codecs import h264
from aiortc.rtcrtpsender import RTCRtpSender
from comfystream.pipeline import Pipeline
from twilio.rest import Client
from comfystream.server.utils import patch_loop_datagram, add_prefix_to_app_routes, FPSMeter
from comfystream.server.metrics import MetricsManager, StreamStatsManager
import time

logger = logging.getLogger(__name__)
logging.getLogger("aiortc.rtcrtpsender").setLevel(logging.WARNING)
logging.getLogger("aiortc.rtcrtpreceiver").setLevel(logging.WARNING)


MAX_BITRATE = 2000000
MIN_BITRATE = 2000000
TEXT_POLL_INTERVAL = 0.25  # Interval in seconds to poll for text outputs


class VideoStreamTrack(MediaStreamTrack):
    """video stream track that processes video frames using a pipeline.

    Attributes:
        kind (str): The kind of media, which is "video" for this class.
        track (MediaStreamTrack): The underlying media stream track.
        pipeline (Pipeline): The processing pipeline to apply to each video frame.
    """

    kind = "video"

    def __init__(self, track: MediaStreamTrack, pipeline: Pipeline):
        """Initialize the VideoStreamTrack.

        Args:
            track: The underlying media stream track.
            pipeline: The processing pipeline to apply to each video frame.
        """
        super().__init__()
        self.track = track
        self.pipeline = pipeline
        self.fps_meter = FPSMeter(
            metrics_manager=app["metrics_manager"], track_id=track.id
        )
        self.running = True
        self.collect_task = asyncio.create_task(self.collect_frames())
        
        # Add cleanup when track ends
        @track.on("ended")
        async def on_ended():
            logger.info("Source video track ended, stopping collection")
            await cancel_collect_frames(self)

    async def collect_frames(self):
        """Collect video frames from the underlying track and pass them to
        the processing pipeline. Stops when track ends or connection closes.
        """
        try:
            while self.running:
                try:
                    frame = await self.track.recv()
                    await self.pipeline.put_video_frame(frame)
                except asyncio.CancelledError:
                    logger.info("Frame collection cancelled")
                    break
                except Exception as e:
                    if "MediaStreamError" in str(type(e)):
                        logger.info("Media stream ended")
                    else:
                        logger.error(f"Error collecting video frames: {str(e)}")
                    self.running = False
                    break
            
            # Perform cleanup outside the exception handler
            logger.info("Video frame collection stopped")
        except asyncio.CancelledError:
            logger.info("Frame collection task cancelled")
        except Exception as e:
            logger.error(f"Unexpected error in frame collection: {str(e)}")
        finally:
            await self.pipeline.cleanup()

    async def recv(self):
        """Receive a processed video frame from the pipeline, increment the frame
        count for FPS calculation and return the processed frame to the client.
        """
        processed_frame = await self.pipeline.get_processed_video_frame()

                # Update the frame buffer with the processed frame
        try:
            from frame_buffer import FrameBuffer
            frame_buffer = FrameBuffer.get_instance()
            frame_buffer.update_frame(processed_frame)
        except Exception as e:
            # Don't let frame buffer errors affect the main pipeline
            print(f"Error updating frame buffer: {e}")

        # Increment the frame count to calculate FPS.
        await self.fps_meter.increment_frame_count()

        return processed_frame


class NoopVideoStreamTrack(MediaStreamTrack):
    """Simple passthrough video track that bypasses pipeline processing."""
    kind = "video"

    def __init__(self, track: MediaStreamTrack):
        super().__init__()
        self.track = track
        logger.debug(f"NoopVideoStreamTrack created for track {track.id}")

    async def recv(self):
        # Simple passthrough - return frames directly from source
        try:
            frame = await asyncio.wait_for(self.track.recv(), timeout=5.0)
            return frame
        except asyncio.TimeoutError:
            logger.warning("Noop video track: No frames received from client for 5 seconds")
            raise


class NoopAudioStreamTrack(MediaStreamTrack):
    """Simple passthrough audio track that bypasses pipeline processing."""
    kind = "audio"

    def __init__(self, track: MediaStreamTrack):
        super().__init__()
        self.track = track
        logger.debug(f"NoopAudioStreamTrack created for track {track.id}")

    async def recv(self):
        # Simple passthrough - return frames directly from source
        try:
            frame = await asyncio.wait_for(self.track.recv(), timeout=5.0)
            return frame
        except asyncio.TimeoutError:
            logger.warning("Noop audio track: No frames received from client for 5 seconds")
            raise


class AudioStreamTrack(MediaStreamTrack):
    kind = "audio"

    def __init__(self, track: MediaStreamTrack, pipeline):
        super().__init__()
        self.track = track
        self.pipeline = pipeline
        self.running = True
        logger.info(f"AudioStreamTrack created for track {track.id}")
        self.collect_task = asyncio.create_task(self.collect_frames())
        
        # Add cleanup when track ends
        @track.on("ended")
        async def on_ended():
            logger.info("Source audio track ended, stopping collection")
            await cancel_collect_frames(self)

    async def collect_frames(self):
        """Collect audio frames from the underlying track and pass them to
        the processing pipeline. Stops when track ends or connection closes.
        """
        try:
            while self.running:
                try:
                    frame = await self.track.recv()
                    await self.pipeline.put_audio_frame(frame)
                except asyncio.CancelledError:
                    logger.info("Audio frame collection cancelled")
                    break
                except Exception as e:
                    if "MediaStreamError" in str(type(e)):
                        logger.info("Media stream ended")
                    else:
                        logger.error(f"Error collecting audio frames: {str(e)}")
                    self.running = False
                    break
            
            # Perform cleanup outside the exception handler
            logger.info("Audio frame collection stopped")
        except asyncio.CancelledError:
            logger.info("Frame collection task cancelled")
        except Exception as e:
            logger.error(f"Unexpected error in audio frame collection: {str(e)}")
        finally:
            await self.pipeline.cleanup()

    async def recv(self):
        return await self.pipeline.get_processed_audio_frame()

def force_codec(pc, sender, forced_codec):
    kind = forced_codec.split("/")[0]
    codecs = RTCRtpSender.getCapabilities(kind).codecs
    transceiver = next(t for t in pc.getTransceivers() if t.sender == sender)
    codecPrefs = [codec for codec in codecs if codec.mimeType == forced_codec]
    transceiver.setCodecPreferences(codecPrefs)


def get_twilio_token():
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")

    if account_sid is None or auth_token is None:
        return None

    client = Client(account_sid, auth_token)

    token = client.tokens.create()

    return token


def get_ice_servers():
    ice_servers = []

    token = get_twilio_token()
    if token is not None:
        # Use Twilio TURN servers
        for server in token.ice_servers:
            if server["url"].startswith("turn:"):
                turn = RTCIceServer(
                    urls=[server["urls"]],
                    credential=server["credential"],
                    username=server["username"],
                )
                ice_servers.append(turn)

    return ice_servers


async def offer(request):
    pipeline = request.app["pipeline"]
    pcs = request.app["pcs"]

    params = await request.json()
    
    # Check if this is noop mode (no prompts provided)
    prompts = params.get("prompts")
    is_noop_mode = not prompts
    
    if is_noop_mode:
        logger.info("[Offer] No prompts provided - entering noop passthrough mode")
    else:
        await pipeline.set_prompts(prompts)
        logger.info("[Offer] Set workflow prompts")
    
    # Set resolution if provided in the offer
    resolution = params.get("resolution")
    if resolution:
        pipeline.width = resolution["width"]
        pipeline.height = resolution["height"]
        logger.info(f"[Offer] Set pipeline resolution to {resolution['width']}x{resolution['height']}")

    offer_params = params["offer"]
    offer = RTCSessionDescription(sdp=offer_params["sdp"], type=offer_params["type"])
    
    ice_servers = get_ice_servers()
    if len(ice_servers) > 0:
        pc = RTCPeerConnection(
            configuration=RTCConfiguration(iceServers=get_ice_servers())
        )
    else:
        pc = RTCPeerConnection()

    pcs.add(pc)

    tracks = {"video": None, "audio": None}
    
    # Flag to track if we've received resolution update
    resolution_received = {"value": False}

    # Add transceivers for both audio and video if present in the offer
    if "m=video" in offer.sdp:
        logger.debug("[Offer] Adding video transceiver")
        video_transceiver = pc.addTransceiver("video", direction="sendrecv")
        caps = RTCRtpSender.getCapabilities("video")
        prefs = list(filter(lambda x: x.name == "H264", caps.codecs))
        video_transceiver.setCodecPreferences(prefs)

        # Monkey patch max and min bitrate to ensure constant bitrate
        h264.MAX_BITRATE = MAX_BITRATE
        h264.MIN_BITRATE = MIN_BITRATE

    if "m=audio" in offer.sdp:
        logger.debug("[Offer] Adding audio transceiver")
        audio_transceiver = pc.addTransceiver("audio", direction="sendrecv")
        audio_caps = RTCRtpSender.getCapabilities("audio")
        # Prefer Opus for audio
        audio_prefs = [codec for codec in audio_caps.codecs if codec.name == "opus"]
        if audio_prefs:
            audio_transceiver.setCodecPreferences(audio_prefs)
            logger.debug("[Offer] Set audio transceiver to prefer Opus")

    # Handle control channel from client
    @pc.on("datachannel")
    def on_datachannel(channel):
        if channel.label == "control":

            @channel.on("message")
            async def on_message(message):
                try:
                    params = json.loads(message)

                    if params.get("type") == "get_nodes":
                        nodes_info = await pipeline.get_nodes_info()
                        response = {"type": "nodes_info", "nodes": nodes_info}
                        channel.send(json.dumps(response))
                    elif params.get("type") == "update_prompts":
                        if "prompts" not in params:
                            logger.warning(
                                "[Control] Missing prompt in update_prompt message"
                            )
                            return
                        try:
                            await pipeline.update_prompts(params["prompts"])
                        except Exception as e:
                            logger.error(f"Error updating prompt: {str(e)}")
                        response = {"type": "prompts_updated", "success": True}
                        channel.send(json.dumps(response))
                    elif params.get("type") == "update_resolution":
                        if "width" not in params or "height" not in params:
                            logger.warning("[Control] Missing width or height in update_resolution message")
                            return
                        
                        if is_noop_mode:
                            logger.info(f"[Control] Noop mode - resolution update to {params['width']}x{params['height']} (no pipeline involved)")
                        else:
                            # Update pipeline resolution for future frames
                            pipeline.width = params["width"]
                            pipeline.height = params["height"]
                            logger.info(f"[Control] Updated resolution to {params['width']}x{params['height']}")
                        
                        # Mark that we've received resolution
                        resolution_received["value"] = True
                        
                        if is_noop_mode:
                            logger.info("[Control] Noop mode - no warmup needed")
                        else:
                            # Note: Video warmup now happens during offer, not here
                            logger.info("[Control] Resolution updated - warmup was already performed during offer")
                            
                        response = {
                            "type": "resolution_updated",
                            "success": True
                        }
                        channel.send(json.dumps(response))
                    else:
                        logger.warning(
                            "[Server] Invalid message format - missing required fields"
                        )
                except json.JSONDecodeError:
                    logger.error("[Server] Invalid JSON received")
                except Exception as e:
                    logger.error(f"[Server] Error processing message: {str(e)}")

        elif channel.label == "data":
            if is_noop_mode:
                logger.debug("[TextChannel] Noop mode - skipping text output forwarding")
                # In noop mode, just acknowledge the data channel but don't forward anything
                @channel.on("open")
                def on_data_channel_open():
                    logger.debug("[TextChannel] Data channel opened in noop mode (no text forwarding)")
            else:
                if pipeline.produces_text_output():
                    async def forward_text():
                        try:
                            while channel.readyState == "open":
                                try:
                                    # Non-blocking poll; sleep if no text to avoid tight loop
                                    text = await pipeline.get_text_output()
                                    if text is None or text.strip() == "":
                                        await asyncio.sleep(TEXT_POLL_INTERVAL)
                                        continue
                                    if channel.readyState == "open":
                                        # Send as JSON string for extensibility
                                        try:
                                            channel.send(json.dumps({"type": "text", "data": text}))
                                        except Exception as e:
                                            logger.debug(f"[TextChannel] Send failed, stopping forwarder: {e}")
                                            break
                                except asyncio.CancelledError:
                                    logger.debug("[TextChannel] Forward text task cancelled")
                                    break
                        except Exception as e:
                            logger.error(f"[TextChannel] Error forwarding text: {e}")

                    # Store task reference for cleanup in request context
                    forward_task = asyncio.create_task(forward_text())
                    if "data_channel_tasks" not in request.app:
                        request.app["data_channel_tasks"] = set()
                    request.app["data_channel_tasks"].add(forward_task)

                    # Remove task from the set when done
                    def _remove_forward_task(t):
                        tasks = request.app.get("data_channel_tasks")
                        if tasks is not None:
                            tasks.discard(t)
                    forward_task.add_done_callback(_remove_forward_task)

                    # Ensure cancellation on channel close event
                    @channel.on("close")
                    def on_data_channel_close():
                        tasks = request.app.get("data_channel_tasks")
                        if tasks:
                            for t in list(tasks):
                                if not t.done():
                                    t.cancel()
                else:
                    logger.debug("[TextChannel] Workflow has no text outputs; not starting forward_text")

    @pc.on("track")
    def on_track(track):
        logger.info(f"Track received: {track.kind} (readyState: {track.readyState})")
        
        # Check if we already have a track of this type to avoid duplicate track errors
        if track.kind == "video" and tracks["video"] is not None:
            logger.debug(f"Video track already exists, ignoring duplicate track event")
            return
        elif track.kind == "audio" and tracks["audio"] is not None:
            logger.debug(f"Audio track already exists, ignoring duplicate track event")
            return
            
        if track.kind == "video":
            if is_noop_mode:
                # Use simple passthrough track that bypasses pipeline
                videoTrack = NoopVideoStreamTrack(track)
                logger.info("[Noop] Using noop video passthrough")
            else:
                # Always use pipeline processing - it handles passthrough internally based on workflow
                videoTrack = VideoStreamTrack(track, pipeline)
                logger.info("[Pipeline] Using video processing pipeline")
            
            tracks["video"] = videoTrack
            sender = pc.addTrack(videoTrack)

            # Store video track in app for stats (only for pipeline mode)
            if not is_noop_mode:
                stream_id = track.id
                request.app["video_tracks"][stream_id] = videoTrack

            codec = "video/H264"
            force_codec(pc, sender, codec)
            
            
        elif track.kind == "audio":
            logger.info(f"Creating audio track for track {track.id}")
            
            if is_noop_mode:
                # Use simple passthrough track that bypasses pipeline
                audioTrack = NoopAudioStreamTrack(track)
                logger.info("[Noop] Using noop audio passthrough")
            else:
                # Always use pipeline processing - it handles passthrough internally based on workflow
                audioTrack = AudioStreamTrack(track, pipeline)
                logger.info("[Pipeline] Using audio processing pipeline")
            
            tracks["audio"] = audioTrack
            sender = pc.addTrack(audioTrack)
            logger.debug(f"Audio track added to peer connection")

        @track.on("ended")
        async def on_ended():
            logger.info(f"{track.kind} track ended")
            request.app["video_tracks"].pop(track.id, None)

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        logger.info(f"Connection state is: {pc.connectionState}")
        if pc.connectionState == "failed":
            await pc.close()
            pcs.discard(pc)
            # Cancel any running data channel tasks
            if "data_channel_tasks" in request.app:
                for task in request.app["data_channel_tasks"]:
                    if not task.done():
                        task.cancel()
                request.app["data_channel_tasks"].clear()
        elif pc.connectionState == "closed":
            await pc.close()
            pcs.discard(pc)
            # Cancel any running data channel tasks
            if "data_channel_tasks" in request.app:
                for task in request.app["data_channel_tasks"]:
                    if not task.done():
                        task.cancel()
                request.app["data_channel_tasks"].clear()

    await pc.setRemoteDescription(offer)

    # Check transceiver states after negotiation
    transceivers = pc.getTransceivers()
    logger.debug(f"[Offer] After negotiation - Total transceivers: {len(transceivers)}")
    for i, t in enumerate(transceivers):
        logger.debug(f"[Offer] Transceiver {i}: {t.kind} - direction: {t.direction} - currentDirection: {t.currentDirection}")

    # Warm up the pipeline based on detected modalities and SDP content (skip in noop mode)
    if not is_noop_mode:
        if "m=video" in pc.remoteDescription.sdp and pipeline.accepts_video_input():
            logger.info("[Offer] Warming up video pipeline")
            await pipeline.warm_video()
            
        if "m=audio" in pc.remoteDescription.sdp and pipeline.accepts_audio_input():
            logger.info("[Offer] Warming up audio pipeline")
            await pipeline.warm_audio()
    else:
        logger.debug("[Offer] Skipping pipeline warmup in noop mode")

    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return web.Response(
        content_type="application/json",
        text=json.dumps(
            {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
        ),
    )

async def cancel_collect_frames(track):
    track.running = False
    if hasattr(track, 'collect_task') is not None and not track.collect_task.done():
        try:
            track.collect_task.cancel()
            await track.collect_task
        except (asyncio.CancelledError):
            pass

async def set_prompt(request):
    pipeline = request.app["pipeline"]

    prompt = await request.json()
    await pipeline.set_prompts(prompt)

    return web.Response(content_type="application/json", text="OK")

def health(_):
    return web.Response(content_type="application/json", text="OK")


async def on_startup(app: web.Application):
    if app["media_ports"]:
        patch_loop_datagram(app["media_ports"])

    app["pipeline"] = Pipeline(
        width=512,
        height=512,
        cwd=app["workspace"], 
        disable_cuda_malloc=True, 
        gpu_only=True, 
        preview_method='none',
        comfyui_inference_log_level=app.get("comfui_inference_log_level", None),
    )
    app["pcs"] = set()
    app["video_tracks"] = {}


async def on_shutdown(app: web.Application):
    pcs = app["pcs"]
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run comfystream server")
    parser.add_argument("--port", default=8889, help="Set the signaling port")
    parser.add_argument(
        "--media-ports", default=None, help="Set the UDP ports for WebRTC media"
    )
    parser.add_argument("--host", default="127.0.0.1", help="Set the host")
    parser.add_argument(
        "--workspace", default=None, required=True, help="Set Comfy workspace"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level",
    )
    parser.add_argument(
        "--monitor",
        default=False,
        action="store_true",
        help="Start a Prometheus metrics endpoint for monitoring.",
    )
    parser.add_argument(
        "--stream-id-label",
        default=False,
        action="store_true",
        help="Include stream ID as a label in Prometheus metrics.",
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
    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    app = web.Application()
    app["media_ports"] = args.media_ports.split(",") if args.media_ports else None
    app["workspace"] = args.workspace
    
    # Setup CORS
    cors = setup_cors(app, defaults={
        "*": ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods=["GET", "POST", "OPTIONS"]
        )
    })

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    app.router.add_get("/", health)
    app.router.add_get("/health", health)

    # WebRTC signalling and control routes.
    app.router.add_post("/offer", offer)
    app.router.add_post("/prompt", set_prompt)
    
    # Setup HTTP streaming routes
    setup_routes(app, cors)
    
    # Serve static files from the public directory
    app.router.add_static("/", path=os.path.join(os.path.dirname(__file__), "public"), name="static")

    # Add routes for getting stream statistics.
    stream_stats_manager = StreamStatsManager(app)
    app.router.add_get(
        "/streams/stats", stream_stats_manager.collect_all_stream_metrics
    )
    app.router.add_get(
        "/stream/{stream_id}/stats", stream_stats_manager.collect_stream_metrics_by_id
    )

    # Add Prometheus metrics endpoint.
    app["metrics_manager"] = MetricsManager(include_stream_id=args.stream_id_label)
    if args.monitor:
        app["metrics_manager"].enable()
        logger.info(
            f"Monitoring enabled - Prometheus metrics available at: "
            f"http://{args.host}:{args.port}/metrics"
        )
        app.router.add_get("/metrics", app["metrics_manager"].metrics_handler)

    # Add hosted platform route prefix.
    # NOTE: This ensures that the local and hosted experiences have consistent routes.
    add_prefix_to_app_routes(app, "/live")

    def force_print(*args, **kwargs):
        print(*args, **kwargs, flush=True)
        sys.stdout.flush()

    # Allow overriding of ComyfUI log levels.
    if args.comfyui_log_level:
        log_level = logging._nameToLevel.get(args.comfyui_log_level.upper())
        logging.getLogger("comfy").setLevel(log_level)
    if args.comfyui_inference_log_level:
        app["comfui_inference_log_level"] = args.comfyui_inference_log_level

    web.run_app(app, host=args.host, port=int(args.port), print=force_print)
