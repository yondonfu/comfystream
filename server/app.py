import asyncio
import argparse
import os
import json
import logging
import wave
import numpy as np

from twilio.rest import Client
from aiohttp import web
from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    RTCConfiguration,
    RTCIceServer,
    MediaStreamTrack,
)
from aiortc.rtcrtpsender import RTCRtpSender
from aiortc.codecs import h264
from pipeline import Pipeline
from utils import patch_loop_datagram

logger = logging.getLogger(__name__)

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
    
class AudioStreamTrack(MediaStreamTrack):
    """
    This custom audio track wraps an incoming audio MediaStreamTrack.
    It continuously records frames in 10-second chunks and saves each chunk
    as a separate WAV file with an incrementing index.
    """

    kind = "audio"

    def __init__(self, track: MediaStreamTrack):
        super().__init__()
        self.track = track
        self.start_time = None
        self.frames = []
        self._recording_duration = 10.0  # in seconds
        self._chunk_index = 0
        self._saving = False
        self._lock = asyncio.Lock()

    async def recv(self):
        frame = await self.track.recv()
        return await self.pipeline(frame)

    # async def recv(self):
    #     frame = await self.source.recv()
        
    #     # On the first frame, record the start time.
    #     if self.start_time is None:
    #         self.start_time = frame.time
    #         logger.info(f"Audio recording started at time: {self.start_time:.3f}")

    #     elapsed = frame.time - self.start_time
    #     self.frames.append(frame)

    #     logger.info(f"Received audio frame at time: {frame.time:.3f}, total frames: {len(self.frames)}")

    #     # Check if we've hit 10 seconds and we're not currently saving.
    #     if elapsed >= self._recording_duration and not self._saving:
    #         logger.info(f"10 second chunk reached (elapsed: {elapsed:.3f}s). Preparing to save chunk {self._chunk_index}.")
    #         self._saving = True
    #         # Handle saving in a background task so we don't block the recv loop.
    #         asyncio.create_task(self.save_audio())

    #     return frame

    async def save_audio(self):
        logger.info(f"Starting to save audio chunk {self._chunk_index}...")
        async with self._lock:
            # Extract properties from the first frame
            if not self.frames:
                logger.warning("No frames to save, skipping.")
                self._saving = False
                return

            sample_rate = self.frames[0].sample_rate
            layout = self.frames[0].layout
            channels = len(layout.channels)

            logger.info(f"Audio chunk {self._chunk_index}: sample_rate={sample_rate}, channels={channels}, frames_count={len(self.frames)}")

            # Convert all frames to ndarray and concatenate
            data_arrays = [f.to_ndarray() for f in self.frames]
            data = np.concatenate(data_arrays, axis=1)  # shape: (channels, total_samples)

            # Interleave channels (if multiple) since WAV expects interleaved samples.
            interleaved = data.T.flatten()

            # If needed, convert float frames to int16
            # interleaved = (interleaved * 32767).astype(np.int16)

            filename = f"output_{self._chunk_index}.wav"
            logger.info(f"Writing audio chunk {self._chunk_index} to file: {filename}")
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(channels)
                wf.setsampwidth(2)  # 16-bit PCM
                wf.setframerate(sample_rate)
                wf.writeframes(interleaved.tobytes())

            logger.info(f"Audio chunk {self._chunk_index} saved successfully as {filename}")

            # Increment the chunk index for the next segment
            self._chunk_index += 1

            # Reset for next recording chunk
            self.frames.clear()
            self.start_time = None
            self._saving = False
            logger.info(f"Ready to record next 10-second chunk. Current chunk index: {self._chunk_index}")


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

    tracks = {"video": None, "audio": None}

    # Prefer h264
    transceiver = pc.addTransceiver("video")
    caps = RTCRtpSender.getCapabilities("video")
    prefs = list(filter(lambda x: x.name == "H264", caps.codecs))
    transceiver.setCodecPreferences(prefs)

    # Monkey patch max and min bitrate to ensure constant bitrate
    h264.MAX_BITRATE = MAX_BITRATE
    h264.MIN_BITRATE = MIN_BITRATE

    @pc.on("track")
    def on_track(track):
        logger.info(f"Track received: {track.kind}")
        if track.kind == "video":
            videoTrack = VideoStreamTrack(track, pipeline)
            tracks["video"] = videoTrack
            sender = pc.addTrack(videoTrack)

            codec = "video/H264"
            force_codec(pc, sender, codec)
        elif track.kind == "audio":
            audioTrack = AudioStreamTrack(track)
            tracks["audio"] = audioTrack
            pc.addTrack(audioTrack)

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
    parser.add_argument("--port", default=8888, help="Set the signaling port")
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

    logging.basicConfig(level=args.log_level.upper())

    app = web.Application()
    app["media_ports"] = args.media_ports.split(",") if args.media_ports else None
    app["workspace"] = args.workspace

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    app.router.add_post("/offer", offer)
    app.router.add_post("/prompt", set_prompt)
    app.router.add_get("/", health)

    web.run_app(app, host=args.host, port=int(args.port))
