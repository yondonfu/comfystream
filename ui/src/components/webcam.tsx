import { useCallback, useEffect, useRef, useState } from "react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

/**
 * Internal component that renders and captures camera feed at exactly 512x512.
 * Handles both display and stream capture in a single canvas element,
 * ensuring consistent dimensions while maintaining aspect ratio.
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

      const scale = Math.max(512 / video.videoWidth, 512 / video.videoHeight);
      const scaledWidth = video.videoWidth * scale;
      const scaledHeight = video.videoHeight * scale;
      const offsetX = (512 - scaledWidth) / 2;
      const offsetY = (512 - scaledHeight) / 2;

      ctx.fillStyle = "black";
      ctx.fillRect(0, 0, 512, 512);
      ctx.drawImage(video, offsetX, offsetY, scaledWidth, scaledHeight);

      requestAnimationFrame(drawFrame);
    };
    drawFrame();

    return () => {
      isActive = false;
    };
  }, [stream]);

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
      <div className="relative">
        {/* Hidden video element that will be used as the source for the canvas */}
        <video ref={videoRef} autoPlay playsInline muted className="hidden" />
        <canvas
          ref={canvasRef}
          width={512}
          height={512}
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
}

export function Webcam({
  onStreamReady,
  deviceId,
  frameRate,
  selectedAudioDeviceId,
}: WebcamProps) {
  const [stream, setStream] = useState<MediaStream | null>(null);

  const replaceStream = useCallback((newStream: MediaStream | null) => {
    setStream((oldStream) => {
      // Clean up old stream if it exists
      if (oldStream) {
        oldStream.getTracks().forEach((track) => track.stop());
      }
      return newStream;
    });
  }, []);

  const startWebcam = useCallback(async () => {
    if (deviceId === "none" && selectedAudioDeviceId === "none") {
      return null;
    }
    if (frameRate == 0) {
      return null;
    }

    try {
      const constraints: MediaStreamConstraints = {
        video:
          deviceId === "none"
            ? false
            : {
                deviceId: { exact: deviceId },
                width: { ideal: 512 },
                height: { ideal: 512 },
                aspectRatio: { ideal: 1 },
                frameRate: { ideal: frameRate, max: frameRate },
              },
        audio:
          selectedAudioDeviceId === "none"
            ? false
            : {
                deviceId: { exact: selectedAudioDeviceId },
                sampleRate: 48000,
                channelCount: 2,
                sampleSize: 16,
                echoCancellation: false,
                noiseSuppression: false,
                autoGainControl: false,
              },
      };

      const newStream = await navigator.mediaDevices.getUserMedia(constraints);
      return newStream;
    } catch (error) {
      console.error("Error accessing media devices.", error);
      return null;
    }
  }, [deviceId, frameRate, selectedAudioDeviceId]);

  useEffect(() => {
    if (deviceId === "none" && selectedAudioDeviceId === "none") return;
    if (frameRate == 0) return;

    startWebcam().then((newStream) => {
      if (newStream) {
        replaceStream(newStream);
        setStream(newStream);
        onStreamReady(newStream);
      }
    });

    return () => {
      replaceStream(null);
    };
  }, [
    deviceId,
    frameRate,
    selectedAudioDeviceId,
    startWebcam,
    replaceStream,
    onStreamReady,
  ]);

  const hasVideo = stream && stream.getVideoTracks().length > 0;
  const hasAudio = stream && stream.getAudioTracks().length > 0;

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
    <div>
      <StreamCanvas
        stream={stream}
        frameRate={frameRate}
        onStreamReady={() => {}} // Already handled in parent component.
      />
    </div>
  );
}
