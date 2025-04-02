"""
Token management system for ComfyStream HTTP streaming.

This module handles the creation, validation, and management of stream tokens.
"""
import time
import secrets
import logging
from aiohttp import web

logger = logging.getLogger(__name__)

# Constants
SESSION_CLEANUP_INTERVAL = 60  # Clean up expired sessions every 60 seconds

# Global token storage
active_stream_sessions = {}
last_cleanup_time = 0

def cleanup_expired_sessions():
    """Clean up expired stream sessions"""
    global active_stream_sessions, last_cleanup_time
    
    current_time = time.time()
    
    # Only clean up if it's been at least SESSION_CLEANUP_INTERVAL since last cleanup
    if current_time - last_cleanup_time < SESSION_CLEANUP_INTERVAL:
        return
    
    # Update the last cleanup time
    last_cleanup_time = current_time
    
    # Find expired sessions
    expired_sessions = [sid for sid, expires in active_stream_sessions.items() if current_time > expires]
    
    # Remove expired sessions
    for sid in expired_sessions:
        logger.info(f"Removing expired session: {sid[:8]}...")
        del active_stream_sessions[sid]
    
    if expired_sessions:
        logger.info(f"Cleaned up {len(expired_sessions)} expired sessions. {len(active_stream_sessions)} active sessions remaining.")

async def create_stream_token(request):
    """Create a unique stream token for secure access to the stream"""
    global active_stream_sessions
    
    # Clean up expired sessions
    cleanup_expired_sessions()
    
    current_time = time.time()
    
    # Generate a new unique token
    stream_id = secrets.token_urlsafe(32)
    expires_at = current_time + 3600  # 1 hour from now
    
    # Store the new session
    active_stream_sessions[stream_id] = expires_at
    
    logger.info(f"Generated new stream token: {stream_id[:8]}... ({len(active_stream_sessions)} active sessions)")
    
    return web.json_response({
        "stream_id": stream_id,
        "expires_at": int(expires_at)
    })

def validate_token(token):
    """Validate a stream token and return whether it's valid
    
    Args:
        token: The token to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not token or token not in active_stream_sessions:
        return False, "Invalid stream token"
    
    # Check if token is expired
    current_time = time.time()
    if current_time > active_stream_sessions[token]:
        # Remove expired token
        del active_stream_sessions[token]
        return False, "Stream token expired"
    
    return True, None
