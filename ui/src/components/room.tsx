"use client";

import { useEffect, useState, useRef } from "react";
import { PeerConnector } from "@/components/peer";
import { Webcam } from "@/components/webcam";
import { StreamSettings, StreamConfig } from "@/components/settings";
import { usePeerContext } from "@/context/peer-context";
import { toast } from "sonner";
import { ControlPanel } from "@/components/control-panel";

interface MediaStreamPlayerProps {
  stream: MediaStream;
}

function MediaStreamPlayer({ stream }: MediaStreamPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    if (videoRef.current && stream) {
      videoRef.current.srcObject = stream;
    }
  }, [stream]);

  return (
    <video
      ref={videoRef}
      autoPlay
      playsInline
      muted
      className="w-full h-full"
    />
  );
}

interface StageProps {
  connected: boolean;
  onStreamReady: () => void;
}

function Stage({ connected, onStreamReady }: StageProps) {
  const { remoteStream } = usePeerContext();

  useEffect(() => {
    if (!connected || !remoteStream) return;

    onStreamReady();
  }, [connected, remoteStream]);

  if (!connected || !remoteStream) {
    return (
      <>
        <video
          className="w-full h-full object-cover"
          autoPlay
          loop
          muted
          playsInline
        >
          <source src="/loading.mp4" type="video/mp4" />
        </video>
      </>
    );
  }

  return <MediaStreamPlayer stream={remoteStream} />;
}

export function Room() {
  const [connect, setConnect] = useState<boolean>(false);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [isStreamSettingsOpen, setIsStreamSettingsOpen] =
    useState<boolean>(true);
  const [localStream, setLocalStream] = useState<MediaStream | null>(null);
  const [loadingToastId, setLoadingToastId] = useState<
    string | number | undefined
  >(undefined);

  const [streamUrl, setStreamUrl] = useState<string>("");
  const [prompt, setPrompt] = useState<any>(null);

  const connectingRef = useRef(false);

  const onStreamReady = (stream: MediaStream) => {
    setLocalStream(stream);
  };

  const onRemoteStreamReady = () => {
    toast.success("Started stream!", { id: loadingToastId });
    setLoadingToastId(undefined);
  };

  const onStreamConfigSave = async (config: StreamConfig) => {
    setStreamUrl(config.streamUrl);
    setPrompt(config.prompt);
  };

  useEffect(() => {
    if (connectingRef.current) return;

    if (!streamUrl) {
      setConnect(false);
    } else {
      setConnect(true);

      const id = toast.loading("Starting stream...");
      setLoadingToastId(id);

      connectingRef.current = true;
    }
  }, [streamUrl]);

  const handleConnected = () => {
    setIsConnected(true);

    console.debug("Connected!");

    connectingRef.current = false;
  };

  const handleDisconnected = () => {
    setIsConnected(false);

    console.debug("Disconnected!");
  };

  return (
    <main className="fixed inset-0 overflow-hidden overscroll-none">
      <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"
      />
      <div className="fixed inset-0 z-[-1] bg-cover bg-[black]">
        <PeerConnector
          url={streamUrl}
          prompt={prompt}
          connect={connect}
          onConnected={handleConnected}
          onDisconnected={handleDisconnected}
          localStream={localStream}
        >
          <div className="min-h-[100dvh] flex flex-col items-center justify-center">
            <div className="w-full max-h-[100dvh] flex flex-col lg:flex-row landscape:flex-row justify-center items-center lg:space-x-4">
              <div className="landscape:w-full lg:w-1/2 h-[50dvh] lg:h-auto landscape:h-full max-w-[512px] max-h-[512px] aspect-square bg-[black] flex justify-center items-center lg:border-2 lg:rounded-md">
                <Stage
                  connected={isConnected}
                  onStreamReady={onRemoteStreamReady}
                />
              </div>
              <div className="landscape:w-full lg:w-1/2 h-[50dvh] lg:h-auto landscape:h-full max-w-[512px] max-h-[512px] aspect-square flex justify-center items-center lg:border-2 lg:rounded-md">
                <Webcam onStreamReady={onStreamReady} />
              </div>
            </div>

            {isConnected && <ControlPanel />}

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
}
