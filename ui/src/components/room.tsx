"use client";

import { PeerConnector } from "@/components/peer";
import { StreamConfig, StreamSettings, DEFAULT_CONFIG } from "@/components/settings";
import { Webcam } from "@/components/webcam";
import { usePeerContext } from "@/context/peer-context";
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { ControlPanelsContainer } from "@/components/control-panels-container";
import { StreamControl } from "@/components/stream-control";

// Custom hook for managing toast lifecycle
function useToast() {
  const toastIdRef = useRef<string | number | undefined>(undefined);
  
  const showToast = useCallback((message: string, type: 'loading' | 'success' | 'error' = 'loading') => {
    // Always dismiss previous toast first
    if (toastIdRef.current) {
      toast.dismiss(toastIdRef.current);
    }
    
    // Create new toast based on type
    let id;
    if (type === 'loading') {
      id = toast.loading(message);
    } else if (type === 'success') {
      id = toast.success(message);
    } else if (type === 'error') {
      id = toast.error(message);
    }
    
    toastIdRef.current = id;
    return id;
  }, []);
  
  const dismissToast = useCallback(() => {
    if (toastIdRef.current) {
      toast.dismiss(toastIdRef.current);
      toastIdRef.current = undefined;
    }
  }, []);
  
  return { showToast, dismissToast, toastId: toastIdRef };
}

interface MediaStreamPlayerProps {
  stream: MediaStream;
  resolution: { width: number; height: number };
}

function MediaStreamPlayer({ stream, resolution, onFrame }: MediaStreamPlayerProps & { onFrame?: () => void }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [needsPlayButton, setNeedsPlayButton] = useState(false);
  const frameCheckRef = useRef<number | null>(null);
  const lastTimeRef = useRef<number>(0);

  useEffect(() => {
    if (!videoRef.current || !stream) return;

    const video = videoRef.current;
    video.srcObject = stream;
    setNeedsPlayButton(false);

    // Add frame detection if needed
    if (onFrame) {
      // Use requestAnimationFrame for more frequent checks
      const checkFrame = (time: number) => {
        // If the video's currentTime has changed, we have a new frame
        if (video.currentTime !== lastTimeRef.current) {
          lastTimeRef.current = video.currentTime;
          onFrame();
        }
        
        frameCheckRef.current = requestAnimationFrame(checkFrame);
      };
      
      frameCheckRef.current = requestAnimationFrame(checkFrame);
      
      return () => {
        if (frameCheckRef.current !== null) {
          cancelAnimationFrame(frameCheckRef.current);
          frameCheckRef.current = null;
        }
      };
    }

    // Handle autoplay
    const playStream = async () => {
      try {
        // Only attempt to play if the video element exists and has a valid srcObject
        if (video && video.srcObject) {
          await video.play();
          setNeedsPlayButton(false);
        }
      } catch (error) {
        // Log error but don't throw - this is likely due to browser autoplay policy
        console.warn("Autoplay prevented:", error);
        setNeedsPlayButton(true);
      }
    };
    playStream();

    return () => {
      if (video) {
        video.srcObject = null;
        video.pause();
      }
      
      if (frameCheckRef.current !== null) {
        cancelAnimationFrame(frameCheckRef.current);
        frameCheckRef.current = null;
      }
    };
  }, [stream, onFrame]);

  const handlePlayClick = async () => {
    try {
      if (videoRef.current) {
        await videoRef.current.play();
        setNeedsPlayButton(false);
      }
    } catch (error) {
      console.warn("Manual play failed:", error);
    }
  };

  return (
    <div 
      className="relative w-full h-full" 
      style={{ aspectRatio: `${resolution.width}/${resolution.height}` }}
    >
      <video
        ref={videoRef}
        autoPlay
        playsInline
        className="w-full h-full object-contain"
      />
      {needsPlayButton && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/50">
          <button
            onClick={handlePlayClick}
            className="px-4 py-2 bg-white text-black rounded-md hover:bg-gray-200 transition-colors"
          >
            Click to Play
          </button>
        </div>
      )}
    </div>
  );
}

interface StageProps {
  connected: boolean;
  onStreamReady: () => void;
  resolution: { width: number; height: number };
  onComfyUIReady: () => void;
  backendUrl: string;
}

function Stage({ connected, onStreamReady, onComfyUIReady, resolution, backendUrl}: StageProps) {
  const { remoteStream, peerConnection } = usePeerContext();
  const [frameRate, setFrameRate] = useState<number>(0);
  // Add state and refs for tracking frames
  const [isComfyUIReady, setIsComfyUIReady] = useState<boolean>(false);
  const frameCountRef = useRef<number>(0);
  const frameReadyReported = useRef<boolean>(false);
  
  // The number of frames to wait before considering ComfyUI ready
  // WARMUP_RUNS is 5, we add a small buffer
  const READY_FRAME_THRESHOLD = 6;

  // Handle frame counting
  const handleFrame = useCallback(() => {
    if (isComfyUIReady || frameReadyReported.current) return;
    
    frameCountRef.current += 1;
    console.log(`[Stage] Frame ${frameCountRef.current} received`);
    
    // Check if we've passed the dummy frames threshold
    if (frameCountRef.current >= READY_FRAME_THRESHOLD && !frameReadyReported.current) {
      console.log(`[Stage] Received ${frameCountRef.current} frames, considering ComfyUI ready`);
      frameReadyReported.current = true;
      setIsComfyUIReady(true);
      onComfyUIReady(); // Notify parent when ComfyUI is ready
    }
  }, [isComfyUIReady, onComfyUIReady]);

  useEffect(() => {
    if (!connected || !remoteStream) {
      // Reset counters when disconnected
      frameCountRef.current = 0;
      frameReadyReported.current = false;
      setIsComfyUIReady(false);
      return;
    }

    onStreamReady();

    // Track frame rate with getStats API
    const interval = setInterval(() => {
      if (peerConnection) {
        peerConnection.getStats().then((stats) => {
          stats.forEach((report) => {
            if (report.type === "inbound-rtp" && report.kind === "video") {
              const currentFrameRate = report.framesPerSecond;
              if (currentFrameRate) {
                setFrameRate(Math.round(currentFrameRate));
              }
            }
          });
        });
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [connected, remoteStream, peerConnection, onStreamReady]);

  if (!connected || !remoteStream) {
    return (
      <>
        <video 
          className="w-full h-full object-cover" 
          autoPlay 
          loop 
          playsInline
          style={{ aspectRatio: `${resolution.width}/${resolution.height}` }}
        >
          <source src="/loading.mp4" type="video/mp4" />
        </video>
      </>
    );
  }

  const hasVideo = remoteStream.getVideoTracks().length > 0;

  return (
    <div 
      className="relative w-full h-full"
      style={{ aspectRatio: `${resolution.width}/${resolution.height}` }}
    >
      <MediaStreamPlayer 
        stream={remoteStream} 
        resolution={resolution} 
        onFrame={handleFrame}
      />
      
      {/* Show warm-up overlay when we have a stream but ComfyUI isn't ready yet */}
      {hasVideo && !isComfyUIReady && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/30">
          <div className="flex flex-col items-center space-y-3 bg-black/50 p-4 rounded-lg">
            <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-white"></div>
            <p className="text-white text-center">ComfyUI is warming up...<br/>This may take a few minutes</p>
          </div>
        </div>
      )}
      
      {hasVideo && (
        <div className="absolute top-2 right-2 bg-black/50 text-white px-2 py-1 rounded text-sm">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger>{frameRate} FPS</TooltipTrigger>
              <TooltipContent>
                <p>This is the FPS of the output stream.</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      )}
      {/* Add StreamControlIcon at the bottom right corner of the video box */}
      <StreamControl backendUrl={backendUrl} />
    </div>
  );
}

/**
 * Creates a room component for the user to stream their webcam to ComfyStream and
 * see the output stream.
 */
export const Room = () => {
  const [connect, setConnect] = useState<boolean>(false);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [isStreamSettingsOpen, setIsStreamSettingsOpen] =
    useState<boolean>(true);
  const [localStream, setLocalStream] = useState<MediaStream | null>(null);
  
  // Use the custom toast hook
  const { showToast, dismissToast, toastId } = useToast();
  
  // Add state to track if ComfyUI is ready
  const [isComfyUIReady, setIsComfyUIReady] = useState<boolean>(false);

  const [config, setConfig] = useState<StreamConfig>({
    ...DEFAULT_CONFIG,
    streamUrl: "",
    frameRate: 0,
    selectedVideoDeviceId: "",
    selectedAudioDeviceId: "",
    prompts: null,
  });

  const connectingRef = useRef(false);

  const onStreamReady = useCallback((stream: MediaStream) => {
    setLocalStream(stream);
  }, []);

  const onRemoteStreamReady = useCallback(() => {
    // Update toast to indicate waiting for ComfyUI to initialize
    showToast("Stream connected, waiting for ComfyUI to initialize...", "loading");
  }, [showToast]);

  // Add a handler for when ComfyUI is ready (will be passed to Stage component)
  const onComfyUIReady = useCallback(() => {
    // Update toast to indicate ComfyUI is ready
    showToast("ComfyUI is ready!", "success");
    setIsComfyUIReady(true);
  }, [showToast]);

  const onStreamConfigSave = useCallback((config: StreamConfig) => {
    setConfig(config);
    
    // If resolution changed, we need to restart the stream
    if (localStream && 
        (config.resolution.width !== DEFAULT_CONFIG.resolution.width || 
         config.resolution.height !== DEFAULT_CONFIG.resolution.height)) {
      console.log(`[Room] Resolution changed to ${config.resolution.width}x${config.resolution.height}, restarting stream`);
    }
  }, [localStream]);

  useEffect(() => {
    if (connectingRef.current) return;

    if (!config.streamUrl) {
      setConnect(false);
      // Reset ComfyUI ready state when disconnecting
      setIsComfyUIReady(false);
      // Dismiss any existing toast
      dismissToast();
    } else {
      setConnect(true);

      showToast("Starting stream...", "loading");
    }

    connectingRef.current = false;
  }, [config.streamUrl, showToast, dismissToast]);

  const handleConnected = useCallback(() => {
    setIsConnected(true);
    connectingRef.current = false;
  }, []);

  const handleDisconnected = useCallback(() => {
    setIsConnected(false);
    setIsComfyUIReady(false);
    showToast("Stream disconnected", "error");
  }, [showToast]);

  return (
    <main className="fixed inset-0 overflow-hidden overscroll-none">
      <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"
      />
      <div className="fixed inset-0 z-[-1] bg-cover bg-[black]">
        <PeerConnector
          url={config.streamUrl}
          prompts={config.prompts ?? null}
          connect={connect}
          onConnected={handleConnected}
          onDisconnected={handleDisconnected}
          localStream={localStream}
          resolution={config.resolution}
        >
          <div className="min-h-[100dvh] flex flex-col items-center justify-center md:justify-start">
            <div className="w-full max-h-[100dvh] flex flex-col md:flex-row landscape:flex-row justify-center items-center lg:space-x-4 md:pt-[10vh]">
              {/* Output stream */}
              <div 
                className="relative w-full max-w-[100vw] sm:max-w-[640px] md:max-w-[512px] flex justify-center items-center bg-slate-900 sm:border-[2px] md:border-0 lg:border-2 rounded-md overflow-hidden"
                style={{
                  aspectRatio: `${config.resolution.width}/${config.resolution.height}`,
                }}
              >
                <Stage
                  connected={isConnected}
                  onStreamReady={onRemoteStreamReady}
                  onComfyUIReady={onComfyUIReady}
                  resolution={config.resolution}
                  backendUrl={config.streamUrl || ""}
                />
                {/* Thumbnail (mobile) */}
                <div className="absolute bottom-[8px] right-[8px] w-[70px] h-[70px] sm:w-[90px] sm:h-[90px] bg-slate-800 block md:hidden overflow-hidden">
                  <Webcam
                    onStreamReady={onStreamReady}
                    deviceId={config.selectedVideoDeviceId}
                    frameRate={config.frameRate}
                    selectedAudioDeviceId={config.selectedAudioDeviceId}
                    resolution={config.resolution}
                  />
                </div>
              </div>
              {/* Input stream (desktop) */}
              <div 
                className="hidden md:flex w-full sm:w-full md:w-full max-w-[512px] flex justify-center items-center lg:border-2 lg:rounded-md bg-slate-800 overflow-hidden"
                style={{
                  aspectRatio: `${config.resolution.width}/${config.resolution.height}`,
                }}
              >
                <Webcam
                  onStreamReady={onStreamReady}
                  deviceId={config.selectedVideoDeviceId}
                  frameRate={config.frameRate}
                  selectedAudioDeviceId={config.selectedAudioDeviceId}
                  resolution={config.resolution}
                />
              </div>
            </div>

            {isConnected && isComfyUIReady && <ControlPanelsContainer />}

            <StreamSettings
              open={isStreamSettingsOpen}
              onOpenChange={setIsStreamSettingsOpen}
              onSave={onStreamConfigSave}
            />
          </div>
        </PeerConnector>
      </div>
    </main>
  );
};
