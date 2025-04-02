"""
HTTP streaming routes for ComfyStream.

This module contains the routes for HTTP streaming and token management.
"""
import asyncio
import logging
from aiohttp import web
from frame_buffer import FrameBuffer
from .tokens import cleanup_expired_sessions, validate_token, create_stream_token

logger = logging.getLogger(__name__)

async def stream_mjpeg(request):
    """Serve an MJPEG stream with token validation"""
    # Clean up expired sessions
    cleanup_expired_sessions()
    
    stream_id = request.query.get("token")
    
    # Validate the stream token
    is_valid, error_message = validate_token(stream_id)
    if not is_valid:
        return web.Response(status=403, text=error_message)
    
    # If this is a HEAD request (used for token validation), return success
    if request.method == 'HEAD':
        return web.Response(status=200)
    
    frame_buffer = FrameBuffer.get_instance()
    
    # Use a fixed frame delay for 30 FPS
    frame_delay = 1.0 / 30
    
    response = web.StreamResponse(
        status=200,
        reason='OK',
        headers={
            'Content-Type': 'multipart/x-mixed-replace; boundary=frame',
            'Cache-Control': 'no-cache',
            'Connection': 'close',
        }
    )
    await response.prepare(request)
    
    try:
        while True:
            jpeg_frame = frame_buffer.get_current_frame()
            if jpeg_frame is not None:
                await response.write(
                    b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + jpeg_frame + b'\r\n'
                )
            await asyncio.sleep(frame_delay)
    except (ConnectionResetError, asyncio.CancelledError):
        logger.info("MJPEG stream connection closed")
    except Exception as e:
        logger.error(f"Error in MJPEG stream: {e}")
    finally:
        return response

def setup_routes(app, cors):
    """Setup HTTP streaming routes
    
    Args:
        app: The aiohttp web application
        cors: The CORS setup object
    """
    # Stream token endpoints
    cors.add(app.router.add_post("/api/stream-token", create_stream_token))
    
    # Stream endpoint with token validation
    cors.add(app.router.add_get("/api/stream", stream_mjpeg))
