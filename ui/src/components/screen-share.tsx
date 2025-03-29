import { useCallback, useEffect, useRef, useState } from "react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

/**
 * Internal component that renders and captures screen sharing feed.
 * Handles both display and stream capture in a single canvas element,
 * maintaining aspect ratio while fitting within bounds.
 */
function StreamCanvas({
  stream,
  frameRate,
}: {
  stream: MediaStream | null;
  frameRate: number;
  onStreamReady: (stream: MediaStream) => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isSelecting, setIsSelecting] = useState(false);
  const [boundingBox, setBoundingBox] = useState<{
    startX: number;
    startY: number;
    endX: number;
    endY: number;
  } | null>(null);
  const [selectionStart, setSelectionStart] = useState<{x: number, y: number} | null>(null);
  const [showFullScreen, setShowFullScreen] = useState(true);

  // Handle mouse down to start bounding box selection
  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!canvasRef.current) return;
    
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left) * (canvas.width / rect.width);
    const y = (e.clientY - rect.top) * (canvas.height / rect.height);
    
    setIsSelecting(true);
    setSelectionStart({x, y});
    // Reset the current bounding box while selecting
    if (showFullScreen) {
      setBoundingBox(null);
    }
  }, [showFullScreen]);

  // Handle mouse move to update bounding box during selection
  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isSelecting || !selectionStart || !canvasRef.current) return;
    
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left) * (canvas.width / rect.width);
    const y = (e.clientY - rect.top) * (canvas.height / rect.height);
    
    setBoundingBox({
      startX: selectionStart.x,
      startY: selectionStart.y,
      endX: x,
      endY: y
    });
  }, [isSelecting, selectionStart]);

  // Handle mouse up to finalize bounding box selection
  const handleMouseUp = useCallback(() => {
    if (isSelecting && boundingBox) {
      // Normalize coordinates (ensure startX < endX and startY < endY)
      const normalizedBox = {
        startX: Math.min(boundingBox.startX, boundingBox.endX),
        startY: Math.min(boundingBox.startY, boundingBox.endY),
        endX: Math.max(boundingBox.startX, boundingBox.endX),
        endY: Math.max(boundingBox.startY, boundingBox.endY)
      };
      
      setBoundingBox(normalizedBox);
      setShowFullScreen(false);
    }
    
    setIsSelecting(false);
    setSelectionStart(null);
  }, [isSelecting, boundingBox]);

  // Reset bounding box and show full screen again
  const resetBoundingBox = useCallback(() => {
    setBoundingBox(null);
    setShowFullScreen(true);
  }, []);

  // Set up canvas animation for screen sharing
  useEffect(() => {
    if (!stream || stream.getVideoTracks().length === 0) {
      return;
    }

    const canvas = canvasRef.current!;
    const ctx = canvas.getContext("2d")!;
    const video = videoRef.current!;

    let isActive = true;
    
    const drawFrame = () => {
      if (!isActive || !video) {
        return;
      }
      
      if (!video?.videoWidth) {
        requestAnimationFrame(drawFrame);
        return;
      }

      // Clear canvas
      ctx.fillStyle = "black";
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      if (showFullScreen || !boundingBox) {
        // Calculate scaling to maintain aspect ratio (full frame)
        const canvasAspect = canvas.width / canvas.height;
        const videoAspect = video.videoWidth / video.videoHeight;
        let drawWidth = canvas.width;
        let drawHeight = canvas.height;
        let offsetX = 0;
        let offsetY = 0;

        if (videoAspect > canvasAspect) {
          // Video is wider than canvas
          drawHeight = canvas.width / videoAspect;
          offsetY = (canvas.height - drawHeight) / 2;
        } else {
          // Video is taller than canvas
          drawWidth = canvas.height * videoAspect;
          offsetX = (canvas.width - drawWidth) / 2;
        }

        ctx.drawImage(video, offsetX, offsetY, drawWidth, drawHeight);
      } else {
        // Draw only the portion within the bounding box
        const canvasAspect = canvas.width / canvas.height;
        const videoAspect = video.videoWidth / video.videoHeight;
        
        // Calculate the scaling factors between video and canvas
        let drawWidth = canvas.width;
        let drawHeight = canvas.height;
        let offsetX = 0;
        let offsetY = 0;

        if (videoAspect > canvasAspect) {
          // Video is wider than canvas
          drawHeight = canvas.width / videoAspect;
          offsetY = (canvas.height - drawHeight) / 2;
        } else {
          // Video is taller than canvas
          drawWidth = canvas.height * videoAspect;
          offsetX = (canvas.width - drawWidth) / 2;
        }

        // Convert bounding box from canvas to video coordinates
        const scaleX = video.videoWidth / drawWidth;
        const scaleY = video.videoHeight / drawHeight;
        
        const vidBoxX = (boundingBox.startX - offsetX) * scaleX;
        const vidBoxY = (boundingBox.startY - offsetY) * scaleY;
        const vidBoxWidth = (boundingBox.endX - boundingBox.startX) * scaleX;
        const vidBoxHeight = (boundingBox.endY - boundingBox.startY) * scaleY;
        
        // Draw the cropped region to fill the canvas
        ctx.drawImage(
          video, 
          vidBoxX, vidBoxY, vidBoxWidth, vidBoxHeight, // Source rectangle
          0, 0, canvas.width, canvas.height // Destination rectangle
        );
      }
      
      // Draw bounding box overlay while selecting
      if (isSelecting && selectionStart && boundingBox) {
        ctx.strokeStyle = "red";
        ctx.lineWidth = 2;
        ctx.strokeRect(
          boundingBox.startX,
          boundingBox.startY,
          boundingBox.endX - boundingBox.startX,
          boundingBox.endY - boundingBox.startY
        );
      }
      
      requestAnimationFrame(drawFrame);
    };
    drawFrame();

    return () => {
      isActive = false;
    };
  }, [stream, isSelecting, selectionStart, boundingBox, showFullScreen]);

  // Set up video element when stream is available
  useEffect(() => {
    if (!stream || stream.getVideoTracks().length === 0 || !videoRef.current) {
      return;
    }
    
    const video = videoRef.current;
    video.srcObject = stream;
    
    video.onloadedmetadata = () => {
      video.play().catch((error) => {
        console.error("Screen sharing video play failed:", error);
      });
    };

    return () => {
      if (video) {
        video.pause();
        video.srcObject = null;
      }
    };
  }, [stream]);

  if (!stream || stream.getVideoTracks().length === 0) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-gray-800 text-white">
        <span>No screen share available</span>
      </div>
    );
  }

  return (
    <>
      <div className="relative">
        <video 
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="hidden"
        />
        <canvas
          ref={canvasRef}
          width={1280}
          height={720}
          className="w-full h-full rounded-lg cursor-crosshair"
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
        />
        <div className="absolute top-2 right-2 bg-black/50 text-white px-2 py-1 rounded text-sm flex gap-2 items-center">
          {!showFullScreen && (
            <button 
              onClick={resetBoundingBox}
              className="bg-blue-500 text-white rounded px-2 py-0.5 text-xs hover:bg-blue-600"
            >
              Reset
            </button>
          )}
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger>{frameRate} FPS</TooltipTrigger>
              <TooltipContent>
                <p>Current screen sharing frame rate</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
        {!isSelecting && showFullScreen && (
          <div className="absolute bottom-2 left-2 bg-black/50 text-white px-2 py-1 rounded text-xs">
            Click and drag to select a region to focus on
          </div>
        )}
      </div>
    </>
  );
}

interface ScreenShareProps {
  onStreamReady: (stream: MediaStream) => void;
  frameRate: number;
}

export function ScreenShare({ onStreamReady, frameRate }: ScreenShareProps) {
  const [stream, setStream] = useState<MediaStream | null>(null);

  const replaceStream = useCallback((newStream: MediaStream | null) => {
    setStream((oldStream) => {
      if (oldStream) {
        oldStream.getTracks().forEach((track) => track.stop());
      }
      return newStream;
    });
  }, []);

  const startScreenShare = useCallback(async () => {
    try {
      // Some browsers might not properly handle frameRate in constraints for screen sharing
      // Create a more compatible set of constraints
      const constraints: MediaStreamConstraints = {
        video: {
          frameRate: frameRate ? { ideal: frameRate, max: frameRate } : undefined,
        },
        audio: false, // Explicitly disable audio for screen sharing
      };

      // Use getDisplayMedia for screen sharing
      const newStream = await navigator.mediaDevices.getDisplayMedia(constraints);
      
      // Apply frameRate to video tracks manually if needed
      if (frameRate && newStream.getVideoTracks().length > 0) {
        const videoTrack = newStream.getVideoTracks()[0];
        try {
          const settings = videoTrack.getSettings();
          console.log("[ScreenShare] Initial screen share settings:", settings);
          
          // Some browsers support changing constraints after getting the stream
          if (videoTrack.applyConstraints) {
            await videoTrack.applyConstraints({
              frameRate: { ideal: frameRate, max: frameRate }
            });
            console.log(`[ScreenShare] Applied frame rate of ${frameRate} to screen share track`);
          }
        } catch (applyError) {
          console.warn("[ScreenShare] Couldn't apply frameRate constraint:", applyError);
        }
      }
      
      // Handle stream stop when user clicks "Stop Sharing"
      newStream.getVideoTracks()[0].onended = () => {
        replaceStream(null);
      };

      return newStream;
    } catch (error) {
      console.error("Error accessing screen sharing:", error);
      return null;
    }
  }, [frameRate, replaceStream]);

  useEffect(() => {
    if (frameRate === 0) return;

    console.log("[ScreenShare] Starting screen share with frame rate:", frameRate);
    
    startScreenShare().then((newStream) => {
      if (newStream) {
        console.log("[ScreenShare] Screen share stream obtained:", 
          `Video tracks: ${newStream.getVideoTracks().length}`,
          `Audio tracks: ${newStream.getAudioTracks().length}`
        );
        
        replaceStream(newStream);
        setStream(newStream);
        
        // Log track information
        newStream.getTracks().forEach(track => {
          console.log(`[ScreenShare] Track: kind=${track.kind}, enabled=${track.enabled}, id=${track.id}`);
          const settings = track.getSettings();
          console.log("[ScreenShare] Track settings:", settings);
        });
        
        // Call the onStreamReady callback from the parent component
        onStreamReady(newStream);
      } else {
        console.warn("[ScreenShare] Failed to get screen share stream");
      }
    }).catch(error => {
      console.error("[ScreenShare] Error in screen sharing effect:", error);
    });

    return () => {
      console.log("[ScreenShare] Cleaning up screen share");
      replaceStream(null);
    };
  }, [frameRate, startScreenShare, replaceStream, onStreamReady]);

  if (!stream || stream.getVideoTracks().length === 0) {
    return null;
  }

  return (
    <div>
      <StreamCanvas
        stream={stream}
        frameRate={frameRate}
        onStreamReady={() => {}} // Already handled in parent component
      />
    </div>
  );
} 