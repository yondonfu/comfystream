import { useCallback, useEffect, useRef, useState } from "react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

/**
 * Internal component that renders and captures camera feed with configurable resolution.
 * Handles both display and stream capture in a single canvas element,
 * ensuring consistent dimensions while maintaining aspect ratio.
 */
function StreamCanvas({
  stream,
  frameRate,
  resolution,
  onStreamReady,
}: {
  stream: MediaStream | null;
  frameRate: number;
  resolution: { width: number; height: number };
  onStreamReady: (stream: MediaStream) => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const { width, height } = resolution;
  const canvasStreamRef = useRef<MediaStream | null>(null);

  // Update canvas dimensions when resolution changes
  useEffect(() => {
    if (canvasRef.current) {
      canvasRef.current.width = width;
      canvasRef.current.height = height;
    }
  }, [width, height]);

  // Create a stream from the canvas with the exact resolution
  useEffect(() => {
    if (!canvasRef.current || !stream) return;

    // Stop previous canvas stream if it exists
    if (canvasStreamRef.current) {
      canvasStreamRef.current.getTracks().forEach(track => track.stop());
    }

    // Create a new stream from the canvas
    const canvas = canvasRef.current;
    const canvasStream = canvas.captureStream(frameRate);
    canvasStreamRef.current = canvasStream;

    // Add audio tracks from the original stream if they exist
    if (stream.getAudioTracks().length > 0) {
      stream.getAudioTracks().forEach(track => {
        // Clone the audio track to avoid conflicts between streams
        const clonedTrack = track.clone();
        canvasStream.addTrack(clonedTrack);
      });
    }

    // Notify parent component about the new stream
    onStreamReady(canvasStream);

    return () => {
      if (canvasStreamRef.current) {
        canvasStreamRef.current.getTracks().forEach(track => {
          // Stop all tracks since audio tracks are now cloned (not shared)
          track.stop();
        });
      }
    };
  }, [stream, frameRate, width, height, onStreamReady]);

  // Only set up canvas animation if we have video
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

      // Calculate scale to fit video in canvas while maintaining aspect ratio
      const scaleWidth = width / video.videoWidth;
      const scaleHeight = height / video.videoHeight;
      const scale = Math.max(scaleWidth, scaleHeight);
      
      const scaledWidth = video.videoWidth * scale;
      const scaledHeight = video.videoHeight * scale;
      const offsetX = (width - scaledWidth) / 2;
      const offsetY = (height - scaledHeight) / 2;

      // Clear the canvas and draw black background
      ctx.fillStyle = "black";
      ctx.fillRect(0, 0, width, height);
      
      // Draw the video frame centered and scaled to fit
      ctx.drawImage(video, offsetX, offsetY, scaledWidth, scaledHeight);
      
      requestAnimationFrame(drawFrame);
    };
    drawFrame();

    return () => {
      isActive = false;
    };
  }, [stream, width, height]);

  // Only set up video element if we have video
  useEffect(() => {
    if (!stream || stream.getVideoTracks().length === 0 || !videoRef.current) {
      return;
    }
    
    const video = videoRef.current;
    video.srcObject = stream;
    
    video.onloadedmetadata = () => {
      video.play().catch((error) => {
        console.error("Video play failed:", error);
      });
    };

    return () => {
      if (video) {
        video.pause();
        video.srcObject = null;
      }
    };
  }, [stream]);

  // Only render canvas if we have video
  if (!stream || stream.getVideoTracks().length === 0) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-gray-800 text-white">
        <span>No video available</span>
      </div>
    );
  }

  return (
    <>
      <div className="relative w-full h-full" style={{ aspectRatio: `${width}/${height}` }}>
        {/* Hidden video element that will be used as the source for the canvas */}
        <video 
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="hidden"
        />
        <canvas
          ref={canvasRef}
          width={width}
          height={height}
          className="w-full h-full"
        />
        <div className="absolute top-2 right-2 bg-black/50 text-white px-2 py-1 rounded text-sm">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger>{frameRate} FPS</TooltipTrigger>
              <TooltipContent>
                <p>This is the requested FPS of your device.</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      </div>
    </>
  );
}

interface WebcamProps {
  onStreamReady: (stream: MediaStream) => void;
  deviceId: string;
  frameRate: number;
  selectedAudioDeviceId: string;
  resolution: { width: number; height: number };
}

export function Webcam({
  onStreamReady,
  deviceId,
  frameRate,
  selectedAudioDeviceId,
  resolution = { width: 512, height: 512 },
}: WebcamProps) {
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [canvasStream, setCanvasStream] = useState<MediaStream | null>(null);

  const replaceStream = useCallback((newStream: MediaStream | null) => {
    setStream((oldStream) => {
      // Clean up old stream if it exists
      if (oldStream) {
        oldStream.getTracks().forEach((track) => track.stop());
      }
      return newStream;
    });

    // Also clean up canvas stream if we're replacing the stream
    setCanvasStream((oldCanvasStream: MediaStream | null): MediaStream | null => {
      if (oldCanvasStream) {
        oldCanvasStream.getTracks().forEach((track) => {
          // Only stop video tracks, as audio tracks are shared with the main stream
          if (track.kind === 'video') {
            track.stop();
          }
        });
      }
      return null;
    });
  }, []);

  const handleCanvasStreamReady = useCallback((stream: MediaStream) => {
    // Clean up any existing canvas stream before setting the new one
    setCanvasStream((oldStream) => {
      if (oldStream) {
        oldStream.getTracks().forEach((track) => {
          if (track.kind === 'video') {
            track.stop();
          }
        });
      }
      return stream;
    });
    
    // Pass the canvas stream to the parent component
    onStreamReady(stream);
  }, [onStreamReady]);

  const startWebcam = useCallback(async () => {
    if (deviceId === "none" && selectedAudioDeviceId === "none") {
      return null;
    }
    if (frameRate == 0) {
      return null;
    }

    try {
      // First try to get the exact resolution
      const constraints: MediaStreamConstraints = {
        video:
          deviceId === "none"
            ? false
            : {
                deviceId: { exact: deviceId },
                width: { exact: resolution.width },
                height: { exact: resolution.height },
                frameRate: { ideal: frameRate, max: frameRate },
              },
        audio:
          selectedAudioDeviceId === "none"
            ? false
            : selectedAudioDeviceId === ""
            ? true  // Use browser default audio with no constraints
            : {
                deviceId: { ideal: selectedAudioDeviceId }, // Use ideal instead of exact
                // Remove strict audio constraints that might cause failures
                echoCancellation: false,
                noiseSuppression: false,
                autoGainControl: false,
              },
      };

      try {
        const stream = await navigator.mediaDevices.getUserMedia(constraints);
        return stream;
      } catch (exactError) {
        console.log("Could not get exact resolution, falling back to ideal constraints", exactError);
        
        // Fall back to ideal constraints if exact fails
        const idealConstraints: MediaStreamConstraints = {
          video:
            deviceId === "none"
              ? false
              : {
                  deviceId: { exact: deviceId },
                  width: { ideal: resolution.width },
                  height: { ideal: resolution.height },
                  aspectRatio: { ideal: resolution.width / resolution.height },
                  frameRate: { ideal: frameRate, max: frameRate },
                },
          audio:
            selectedAudioDeviceId === "none"
              ? false
              : selectedAudioDeviceId === ""
              ? true  // Use browser default audio with no constraints
              : {
                  deviceId: { ideal: selectedAudioDeviceId }, // Use ideal instead of exact
                  // Remove strict audio constraints that might cause failures
                  echoCancellation: false,
                  noiseSuppression: false,
                  autoGainControl: false,
                },
        };
        
        const fallbackStream = await navigator.mediaDevices.getUserMedia(idealConstraints);
        return fallbackStream;
      }
    } catch (error) {
      console.error("Error accessing media devices.", error);
      return null;
    }
  }, [deviceId, frameRate, selectedAudioDeviceId, resolution]);

  useEffect(() => {
    if (deviceId === "none" && selectedAudioDeviceId === "none") return;
    if (frameRate == 0) return;

    startWebcam().then((newStream) => {
      if (newStream) {
        replaceStream(newStream);
        setStream(newStream);
        // onStreamReady will be called by handleCanvasStreamReady when the canvas stream is ready
      }
    });

    return () => {
      replaceStream(null);
    };
  }, [
    deviceId,
    frameRate,
    selectedAudioDeviceId,
    resolution,
    startWebcam,
    replaceStream,
  ]);

  const hasVideo = stream && stream.getVideoTracks().length > 0;
  const hasAudio = stream && stream.getAudioTracks().length > 0;

  // Ensure audio only stream is passed to parent component.
  useEffect(() => {
    if (stream && !hasVideo && hasAudio) {
      onStreamReady(stream);
    }
  }, [stream, hasVideo, hasAudio, onStreamReady]);

  // Return audio-only placeholder if we have audio but no video
  if (!hasVideo && hasAudio) {
    return (
      <div className="w-full h-full flex items-center justify-center">
        <span className="text-white">Audio Only</span>
      </div>
    );
  }

  // Return null if we have neither video nor audio
  if (!stream || (!hasVideo && !hasAudio)) {
    return null;
  }

  return (
    <div className="w-full h-full" style={{ aspectRatio: `${resolution.width}/${resolution.height}` }}>
      <StreamCanvas
        stream={stream}
        frameRate={frameRate}
        resolution={resolution}
        onStreamReady={handleCanvasStreamReady}
      />
    </div>
  );
}
