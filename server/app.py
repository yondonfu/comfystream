import asyncio
import argparse
import os
import json
import logging

import torch

# Initialize CUDA before any other imports to prevent core dump.
if torch.cuda.is_available():
    torch.cuda.init()


from twilio.rest import Client
from aiohttp import web
from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    RTCConfiguration,
    RTCIceServer,
    MediaStreamTrack,
    RTCDataChannel,
)
from aiortc.rtcrtpsender import RTCRtpSender
from aiortc.codecs import h264
from pipeline import Pipeline
from utils import patch_loop_datagram

logger = logging.getLogger(__name__)
logging.getLogger('aiortc.rtcrtpsender').setLevel(logging.WARNING)
logging.getLogger('aiortc.rtcrtpreceiver').setLevel(logging.WARNING)


MAX_BITRATE = 2000000
MIN_BITRATE = 2000000


class VideoStreamTrack(MediaStreamTrack):
    kind = "video"

    def __init__(self, track: MediaStreamTrack, pipeline):
        super().__init__()
        self.track = track
        self.pipeline = pipeline

    async def recv(self):
        frame = await self.track.recv()
        return await self.pipeline(frame)


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

    pipeline.set_prompt(params["prompt"])
    await pipeline.warm()

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

    tracks = {"video": None}

    # Prefer h264
    transceiver = pc.addTransceiver("video")
    caps = RTCRtpSender.getCapabilities("video")
    prefs = list(filter(lambda x: x.name == "H264", caps.codecs))
    transceiver.setCodecPreferences(prefs)

    # Monkey patch max and min bitrate to ensure constant bitrate
    h264.MAX_BITRATE = MAX_BITRATE
    h264.MIN_BITRATE = MIN_BITRATE

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
                        response = {
                            "type": "nodes_info",
                            "nodes": nodes_info
                        }
                        channel.send(json.dumps(response))
                    elif params.get("type") == "update_prompt":
                        if "prompt" not in params:
                            logger.warning("[Control] Missing prompt in update_prompt message")
                            return
                        pipeline.set_prompt(params["prompt"])
                        response = {
                            "type": "prompt_updated",
                            "success": True
                        }
                        channel.send(json.dumps(response))
                    else:
                        logger.warning("[Server] Invalid message format - missing required fields")
                except json.JSONDecodeError:
                    logger.error("[Server] Invalid JSON received")
                except Exception as e:
                    logger.error(f"[Server] Error processing message: {str(e)}")

    @pc.on("track")
    def on_track(track):
        logger.info(f"Track received: {track.kind}")
        if track.kind == "video":
            videoTrack = VideoStreamTrack(track, pipeline)
            tracks["video"] = videoTrack
            sender = pc.addTrack(videoTrack)

            codec = "video/H264"
            force_codec(pc, sender, codec)

        @track.on("ended")
        async def on_ended():
            logger.info(f"{track.kind} track ended")

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        logger.info(f"Connection state is: {pc.connectionState}")
        if pc.connectionState == "failed":
            await pc.close()
            pcs.discard(pc)
        elif pc.connectionState == "closed":
            await pc.close()
            pcs.discard(pc)

    await pc.setRemoteDescription(offer)

    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return web.Response(
        content_type="application/json",
        text=json.dumps(
            {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
        ),
    )


async def set_prompt(request):
    pipeline = request.app["pipeline"]

    prompt = await request.json()
    pipeline.set_prompt(prompt)

    return web.Response(content_type="application/json", text="OK")


def health(_):
    return web.Response(content_type="application/json", text="OK")


async def on_startup(app: web.Application):
    if app["media_ports"]:
        patch_loop_datagram(app["media_ports"])

    app["pipeline"] = Pipeline(
        cwd=app["workspace"], disable_cuda_malloc=True, gpu_only=True
    )
    app["pcs"] = set()


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
    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level.upper(),
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S'
    )

    app = web.Application()
    app["media_ports"] = args.media_ports.split(",") if args.media_ports else None
    app["workspace"] = args.workspace

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    app.router.add_post("/offer", offer)
    app.router.add_post("/prompt", set_prompt)
    app.router.add_get("/", health)

    web.run_app(app, host=args.host, port=int(args.port))
