"use client";

import { PeerConnector } from "@/components/peer";
import { StreamConfig, StreamSettings } from "@/components/settings";
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

interface MediaStreamPlayerProps {
  stream: MediaStream;
}

function MediaStreamPlayer({ stream }: MediaStreamPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [needsPlayButton, setNeedsPlayButton] = useState(false);

  useEffect(() => {
    if (!videoRef.current || !stream) return;

    const video = videoRef.current;
    video.srcObject = stream;
    setNeedsPlayButton(false);

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
    };
  }, [stream]);

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
    <div className="relative w-full h-full">
      <video
        ref={videoRef}
        autoPlay
        playsInline
        className="w-full h-full object-cover"
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
}

function Stage({ connected, onStreamReady }: StageProps) {
  const { remoteStream, peerConnection } = usePeerContext();
  const [frameRate, setFrameRate] = useState<number>(0);

  useEffect(() => {
    if (!connected || !remoteStream) return;

    onStreamReady();

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
        <video className="w-full h-full object-cover" autoPlay loop playsInline>
          <source src="/loading.mp4" type="video/mp4" />
        </video>
      </>
    );
  }

  const hasVideo = remoteStream.getVideoTracks().length > 0;

  return (
    <div className="relative w-full h-full">
      <MediaStreamPlayer stream={remoteStream} />
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
      <StreamControl />
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
  const [loadingToastId, setLoadingToastId] = useState<
    string | number | undefined
  >(undefined);

  const [config, setConfig] = useState<StreamConfig>({
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
    toast.success("Started stream!", { id: loadingToastId });
    setLoadingToastId(undefined);
  }, [loadingToastId]);

  const onStreamConfigSave = useCallback((config: StreamConfig) => {
    setConfig(config);
  }, []);

  useEffect(() => {
    if (connectingRef.current) return;

    if (!config.streamUrl) {
      setConnect(false);
    } else {
      setConnect(true);

      const id = toast.loading("Starting stream...");
      setLoadingToastId(id);

      connectingRef.current = true;
    }
  }, [config.streamUrl]);

  const handleConnected = useCallback(() => {
    setIsConnected(true);
    connectingRef.current = false;
  }, []);

  const handleDisconnected = useCallback(() => {
    setIsConnected(false);
  }, []);

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
        >
          <div className="min-h-[100dvh] flex flex-col items-center justify-center md:justify-start">
            <div className="w-full max-h-[100dvh] flex flex-col md:flex-row landscape:flex-row justify-center items-center lg:space-x-4 md:pt-[10vh]">
              {/* Output stream */}
              <div className="relative w-full max-w-[100vw] h-auto aspect-square sm:max-w-[640px] sm:max-h-[640px] md:max-w-[512px] md:max-h-[512px] flex justify-center items-center bg-slate-900 sm:border-[2px] md:border-0 lg:border-2 rounded-md">
                <Stage
                  connected={isConnected}
                  onStreamReady={onRemoteStreamReady}
                />
                {/* Thumbnail (mobile) */}
                <div className="absolute bottom-[8px] right-[8px] w-[70px] h-[70px] sm:w-[90px] sm:h-[90px] bg-slate-800 block md:hidden">
                  <Webcam
                    onStreamReady={onStreamReady}
                    deviceId={config.selectedVideoDeviceId}
                    frameRate={config.frameRate}
                    selectedAudioDeviceId={config.selectedAudioDeviceId}
                  />
                </div>
              </div>
              {/* Input stream (desktop) */}
              <div className="hidden md:flex w-full sm:w-full md:w-full h-[50dvh] sm:h-auto md:h-auto max-w-[512px] max-h-[512px] aspect-square justify-center items-center lg:border-2 lg:rounded-md bg-slate-800">
                <Webcam
                  onStreamReady={onStreamReady}
                  deviceId={config.selectedVideoDeviceId}
                  frameRate={config.frameRate}
                  selectedAudioDeviceId={config.selectedAudioDeviceId}
                />
              </div>
            </div>

            {isConnected && <ControlPanelsContainer />}

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
