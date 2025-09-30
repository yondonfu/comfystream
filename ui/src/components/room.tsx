"use client";

import { PeerConnector } from "@/components/peer";
import { StreamConfig, StreamSettings, DEFAULT_CONFIG } from "@/components/settings";
import { Webcam } from "@/components/webcam";
import { usePeerContext } from "@/context/peer-context";
import { Prompt } from "@/types";
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
import { TextOutputViewer } from "@/components/text-output-viewer";
import fixWebmDuration from 'webm-duration-fix';
import { set, get, del, keys } from 'idb-keyval';
import { Drawer, DrawerContent, DrawerTitle } from "./ui/drawer";
import * as Tabs from '@radix-ui/react-tabs';

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

// Wrapper component to access peer context
function TranscriptionViewerWrapper() {
  const peer = usePeerContext();
  
  return (
    <TextOutputViewer 
      isConnected={!!peer?.peerConnection && peer.peerConnection.connectionState === 'connected'}
      textOutputData={peer?.textOutputData || undefined}
    />
  );
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
  onComfyUIReady: () => void;
  resolution: { width: number; height: number };
  onOutputStreamReady: (stream: MediaStream | null) => void;
  prompts: Prompt[] | null;
}

function Stage({ connected, onStreamReady, onComfyUIReady, resolution, onOutputStreamReady, prompts }: StageProps) {
  const { remoteStream, peerConnection } = usePeerContext();
  const [frameRate, setFrameRate] = useState<number>(0);
  // Add state and refs for tracking frames
  const [isComfyUIReady, setIsComfyUIReady] = useState<boolean>(false);
  const frameCountRef = useRef<number>(0);
  const frameReadyReported = useRef<boolean>(false);
  
  // Check if we're in noop mode by looking at the prompts prop
  const isNoopMode = !prompts || prompts.length === 0;
  
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
      if (onOutputStreamReady) onOutputStreamReady(null);
      return;
    }

    onStreamReady();
    if (onOutputStreamReady) {
      console.log('[Stage] Calling onOutputStreamReady with', remoteStream);
      onOutputStreamReady(remoteStream);
    }
    
    // In noop mode, immediately set ComfyUI as ready since there's no actual ComfyUI processing
    if (isNoopMode && !isComfyUIReady) {
      console.log('[Stage] Noop mode detected - setting ComfyUI ready immediately');
      setIsComfyUIReady(true);
      onComfyUIReady();
    }

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
  }, [connected, remoteStream, peerConnection, onStreamReady, onOutputStreamReady, isNoopMode, isComfyUIReady, onComfyUIReady]);

  if (!connected || !remoteStream) {
    return (
      <div 
        className="relative w-full h-full flex items-center justify-center bg-black"
        style={{ aspectRatio: `${resolution.width}/${resolution.height}` }}
      >
        <div className="flex flex-col items-center space-y-3">
          <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-white"></div>
          <p className="text-white text-center opacity-80">Waiting for stream...</p>
        </div>
      </div>
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
            <p className="text-white text-center">
              {isNoopMode 
                ? "Initializing noop stream..." 
                : "ComfyUI is warming up...\nThis may take a few minutes"}
            </p>
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
  const [outputStream, _setOutputStream] = useState<MediaStream | null>(null);
  
  // Use the custom toast hook
  const { showToast, dismissToast, toastId } = useToast();
  
  // Add state to track if ComfyUI is ready
  const [isComfyUIReady, setIsComfyUIReady] = useState<boolean>(false);

  // Recording state
  const [isRecording, setIsRecording] = useState(false);
  const [recordings, setRecordings] = useState<{ type: 'input' | 'output'; url: string; filename: string; id: string }[]>([]);
  const inputRecorderRef = useRef<MediaRecorder | null>(null);
  const outputRecorderRef = useRef<MediaRecorder | null>(null);
  const inputChunksRef = useRef<Blob[]>([]);
  const outputChunksRef = useRef<Blob[]>([]);
  const [isRecordingsPanelOpen, setIsRecordingsPanelOpen] = useState(false);
  
  // Transcription state
  const [isTranscriptionPanelOpen, setIsTranscriptionPanelOpen] = useState(true);

  // Helper to get timestamped filenames
  const getFilename = (type: 'input' | 'output', extension: string) => {
    const now = new Date();
    const pad = (n: number) => n.toString().padStart(2, '0');
    const ts = `${now.getFullYear()}${pad(now.getMonth()+1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
    return `recording_${type}_${ts}.${extension}`;
  };

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
    
  }, []);

  // Add a handler for when ComfyUI is ready (will be passed to Stage component)
  const onComfyUIReady = useCallback(() => {
    // Dismiss the previous toast (waiting for ComfyUI)
    dismissToast();
    // Show the ready toast
    showToast("ComfyUI is ready!", "success");
    setIsComfyUIReady(true);
  }, [showToast, dismissToast]);

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
      connectingRef.current = true;
    }
  }, [config.streamUrl, showToast, dismissToast]);

  const handleConnected = useCallback(() => {
    setIsConnected(true);
    showToast("Stream connected, waiting for ComfyUI to initialize...", "loading");
    connectingRef.current = false;
  }, []);

  const handleDisconnected = useCallback(() => {
    setIsConnected(false);
    setIsComfyUIReady(false);
    showToast("Stream disconnected", "error");
  }, [showToast]);

  // Helper to choose a supported mimeType for a given stream
  function chooseMimeForStream(stream: MediaStream): { mimeType: string | undefined; extension: string } {
    const hasAudio = stream.getAudioTracks().length > 0;
    const hasVideo = stream.getVideoTracks().length > 0;

    // Try best combinations first
    const candidates: { mimeType: string; extension: string }[] = [];

    if (hasAudio && hasVideo) {
      candidates.push(
        { mimeType: 'video/webm;codecs=vp9,opus', extension: 'webm' },
        { mimeType: 'video/webm;codecs=vp8,opus', extension: 'webm' },
        { mimeType: 'video/webm', extension: 'webm' }
      );
    } else if (hasVideo) {
      candidates.push(
        { mimeType: 'video/webm;codecs=vp9', extension: 'webm' },
        { mimeType: 'video/webm;codecs=vp8', extension: 'webm' },
        { mimeType: 'video/webm', extension: 'webm' }
      );
    } else if (hasAudio) {
      candidates.push(
        { mimeType: 'audio/webm;codecs=opus', extension: 'webm' },
        { mimeType: 'audio/webm', extension: 'webm' }
      );
    }

    for (const { mimeType, extension } of candidates) {
      if ((window as any).MediaRecorder && MediaRecorder.isTypeSupported(mimeType)) {
        return { mimeType, extension };
      }
    }

    // Fallback: let browser choose default; pick a sensible extension
    return { mimeType: undefined, extension: hasAudio && !hasVideo ? 'webm' : 'webm' };
  }

  // Helper to generate a unique ID
  const generateId = () => `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;

  // Load recordings from IndexedDB on mount
  useEffect(() => {
    (async () => {
      const allKeys = await keys();
      const recs: { type: 'input' | 'output'; url: string; filename: string; id: string }[] = [];
      for (const key of allKeys) {
        if (typeof key === 'string' && key.startsWith('recording_')) {
          const { type, filename, blob } = await get(key);
          const url = URL.createObjectURL(blob);
          recs.push({ type, filename, url, id: key });
        }
      }
      setRecordings(recs);
    })();
  }, []);

  // Save a recording to IndexedDB and update state
  const saveRecording = async (type: 'input' | 'output', filename: string, blob: Blob) => {
    const id = `recording_${generateId()}`;
    await set(id, { type, filename, blob });
    const url = URL.createObjectURL(blob);
    setRecordings((prev) => [...prev, { type, filename, url, id }]);
  };

  // Delete a recording from IndexedDB and update state
  const deleteRecording = async (id: string) => {
    await del(id);
    setRecordings((prev) => prev.filter(r => r.id !== id));
  };

  // Share a recording using the Web Share API
  const shareRecording = async (filename: string, blob: Blob) => {
    if (navigator.share) {
      try {
        await navigator.share({
          files: [new File([blob], filename, { type: blob.type })],
          title: filename,
        });
      } catch (e) {
        showToast('Sharing cancelled or failed', 'error');
      }
    } else {
      showToast('Web Share API not supported on this device', 'error');
    }
  };

  // Start recording both streams
  const startRecording = () => {
    if (isRecording) return;
    if (localStream) {
      const { mimeType, extension } = chooseMimeForStream(localStream);
      inputChunksRef.current = [];
      const inputRecorder = new MediaRecorder(localStream, mimeType ? { mimeType } : undefined);
      inputRecorder.ondataavailable = (e) => e.data.size && inputChunksRef.current.push(e.data);
      inputRecorder.onstop = () => {
        const filename = getFilename('input', extension);
        const finalType = mimeType ?? (extension === 'webm' ? 'video/webm' : 'application/octet-stream');
        const blob = new Blob(inputChunksRef.current, { type: finalType });
        const maybeFix = extension === 'webm' ? fixWebmDuration(blob) : Promise.resolve(blob);
        maybeFix.then(fixedBlob => {
          saveRecording('input', filename, fixedBlob);
        });
      };
      inputRecorder.start();
      inputRecorderRef.current = inputRecorder;
    }
    if (outputStream) {
      const { mimeType, extension } = chooseMimeForStream(outputStream);
      outputChunksRef.current = [];
      const outputRecorder = new MediaRecorder(outputStream, mimeType ? { mimeType } : undefined);
      outputRecorder.ondataavailable = (e) => e.data.size && outputChunksRef.current.push(e.data);
      outputRecorder.onstop = () => {
        const filename = getFilename('output', extension);
        const finalType = mimeType ?? (extension === 'webm' ? 'video/webm' : 'application/octet-stream');
        const blob = new Blob(outputChunksRef.current, { type: finalType });
        const maybeFix = extension === 'webm' ? fixWebmDuration(blob) : Promise.resolve(blob);
        maybeFix.then(fixedBlob => {
          saveRecording('output', filename, fixedBlob);
        });
      };
      outputRecorder.start();
      outputRecorderRef.current = outputRecorder;
    }
    setIsRecording(true);
    showToast('Recording started', 'success');
  };

  // Stop recording both streams
  const stopRecording = () => {
    if (inputRecorderRef.current && inputRecorderRef.current.state !== 'inactive') {
      inputRecorderRef.current.stop();
    }
    if (outputRecorderRef.current && outputRecorderRef.current.state !== 'inactive') {
      outputRecorderRef.current.stop();
    }
    setIsRecording(false);
    showToast('Recording stopped', 'success');
  };

  const setOutputStream = (stream: MediaStream | null) => {
    console.log('[Room] setOutputStream called with', stream);
    _setOutputStream(stream);
  };

  useEffect(() => {
    console.log('[Room] outputStream state changed:', outputStream);
  }, [outputStream]);

  const [isControlPanelOpen, setIsControlPanelOpen] = useState(false);

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
                  onOutputStreamReady={setOutputStream}
                  prompts={config.prompts || null}
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

            {/* Text Output toggle under videos */}
            {isConnected && (
              <div className="w-full flex justify-center mt-4">
                <button
                  onClick={() => setIsTranscriptionPanelOpen(!isTranscriptionPanelOpen)}
                  className={`h-10 px-4 rounded-full shadow-lg flex items-center justify-center transition-colors ${
                    isTranscriptionPanelOpen 
                      ? 'bg-green-600 text-white hover:bg-green-700' 
                      : 'bg-purple-600 text-white hover:bg-purple-700'
                  }`}
                  title={isTranscriptionPanelOpen ? 'Hide Text Output' : 'Show Text Output'}
                >
                  {isTranscriptionPanelOpen ? (
                    // eye-off icon
                    <span className="flex items-center gap-2">
                      <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="feather feather-eye-off">
                        <path d="M17.94 17.94A10.94 10.94 0 0 1 12 20C7 20 2.73 16.11 1 12c.86-1.99 2.28-3.73 4-5.05"></path>
                        <path d="M10.58 10.58a2 2 0 0 0 2.84 2.84"></path>
                        <path d="M16 12a4 4 0 0 0-4-4"></path>
                        <path d="M1 1l22 22"></path>
                      </svg>
                      <span>Hide Text Output</span>
                    </span>
                  ) : (
                    // eye icon
                    <span className="flex items-center gap-2">
                      <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="feather feather-eye">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                        <circle cx="12" cy="12" r="3"></circle>
                      </svg>
                      <span>Show Text Output</span>
                    </span>
                  )}
                </button>
              </div>
            )}

            {/* Button group: Record, Show Recordings, Gear */}
            <div className="fixed top-4 right-4 flex flex-row items-end space-x-4 z-50">
              {/* Stream Settings button (shown when not streaming) */}
              {!localStream && (
                <button
                  onClick={() => setIsStreamSettingsOpen(true)}
                  className="h-12 w-12 rounded-full bg-gray-800 text-white shadow-lg flex items-center justify-center hover:bg-gray-900"
                  title="Stream Settings"
                >
                  <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="feather feather-sliders"><line x1="4" y1="21" x2="4" y2="14"></line><line x1="4" y1="10" x2="4" y2="3"></line><line x1="12" y1="21" x2="12" y2="12"></line><line x1="12" y1="8" x2="12" y2="3"></line><line x1="20" y1="21" x2="20" y2="16"></line><line x1="20" y1="12" x2="20" y2="3"></line><line x1="1" y1="14" x2="7" y2="14"></line><line x1="9" y1="8" x2="15" y2="8"></line><line x1="17" y1="16" x2="23" y2="16"></line></svg>
                </button>
              )}
              {/* Gear/settings button (only when streaming) */}
              {isConnected && isComfyUIReady && localStream && (
                <button
                  onClick={() => setIsControlPanelOpen(true)}
                  className="h-12 w-12 rounded-full bg-gray-800 text-white shadow-lg flex items-center justify-center hover:bg-gray-900"
                  title="Settings"
                >
                  <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="feather feather-settings"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h.09a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09c0 .66.39 1.26 1 1.51a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v.09c0 .66.39 1.26 1 1.51H21a2 2 0 0 1 0 4h-.09c-.66 0-1.26.39-1.51 1z"></path></svg>
                </button>
              )}
              {/* Record button (conditionally shown) */}
              {(localStream && outputStream && isComfyUIReady) && (
                <button
                  onClick={isRecording ? stopRecording : startRecording}
                  className="h-12 w-12 rounded-full shadow-lg transition-shadow flex items-center justify-center bg-red-600 text-white hover:scale-105"
                  title={isRecording ? 'Stop Recording' : 'Start Recording'}
                >
                  {isRecording ? (
                    <svg width="32" height="32" viewBox="0 0 32 32" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
                      <rect x="8" y="8" width="16" height="16" rx="3" />
                    </svg>
                  ) : (
                    <svg width="32" height="32" viewBox="0 0 32 32" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
                      <circle cx="16" cy="16" r="7" />
                    </svg>
                  )}
                </button>
              )}
              {/* Text Output toggle removed from here */}
              {/* Show Recordings button (always rightmost) */}
              <button
                onClick={() => setIsRecordingsPanelOpen(true)}
                className="h-12 w-12 rounded-full bg-blue-600 text-white shadow-lg flex items-center justify-center hover:bg-blue-700"
                title="Show Recordings"
              >
                <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="feather feather-film"><rect x="2" y="7" width="20" height="10" rx="2" ry="2"></rect><path d="M6 7V5M6 19v-2M18 7V5M18 19v-2"></path></svg>
              </button>
            </div>
            {/* Text Output Panel (below videos) - kept mounted to preserve content */}
            {isConnected && (
              <div className={`w-full flex justify-center px-4 mt-4 ${isTranscriptionPanelOpen ? '' : 'hidden'}`}>
                <div className="w-full max-w-[1040px]">
                  <TranscriptionViewerWrapper />
                </div>
              </div>
            )}
            
            {/* Recordings Side Panel */}
            {isRecordingsPanelOpen && (
              <div className="fixed inset-0 z-50 flex justify-end">
                <div className="fixed inset-0 bg-black/30" onClick={() => setIsRecordingsPanelOpen(false)} />
                <div className="relative w-full max-w-md h-full bg-white shadow-xl p-6 overflow-y-auto flex flex-col">
                  <button
                    onClick={() => setIsRecordingsPanelOpen(false)}
                    className="absolute top-4 right-4 text-2xl text-gray-500 hover:text-black"
                    title="Close"
                  >×</button>
                  <h2 className="text-xl font-bold mb-4">Recordings</h2>
                  {recordings.length === 0 ? (
                    <div className="text-gray-500">No recordings yet.</div>
                  ) : (
                    <div className="flex flex-col gap-4">
                      {Array.from(new Set(recordings.map(r => r.filename.replace(/^recording_(input|output)_/, ''))))
                        .map(baseTimestamp => {
                          const inputRec = recordings.find(r => r.type === 'input' && r.filename.replace(/^recording_(input|output)_/, '') === baseTimestamp);
                          const outputRec = recordings.find(r => r.type === 'output' && r.filename.replace(/^recording_(input|output)_/, '') === baseTimestamp);
                          const rec = outputRec || inputRec; // Use either recording for the container
                          if (!rec) return null; // Skip if no valid recording found
                          return (
                            <div key={rec.id} className="border rounded-lg p-3 bg-gray-50 flex flex-col gap-2">
                              <div className="flex items-center justify-between">
                                <span className="font-semibold">{rec.filename.replace(/^recording_(input|output)_/, '')}</span>
                                <button
                                  onClick={() => {
                                    if (inputRec) deleteRecording(inputRec.id);
                                    if (outputRec) deleteRecording(outputRec.id);
                                  }}
                                  className="text-red-500 hover:text-red-700 text-lg ml-2"
                                  title="Delete"
                                >🗑️</button>
                              </div>
                              <Tabs.Root defaultValue={outputRec ? 'output' : 'input'} className="w-full">
                                <Tabs.List className="flex gap-2">
                                  {outputRec && <Tabs.Trigger value="output" className="px-3 py-1 rounded-t bg-slate-100 text-slate-700 data-[state=active]:bg-slate-700 data-[state=active]:text-white transition-colors">Output</Tabs.Trigger>}
                                  {inputRec && <Tabs.Trigger value="input" className="px-3 py-1 rounded-t bg-gray-100 text-gray-700 data-[state=active]:bg-gray-700 data-[state=active]:text-white transition-colors">Input</Tabs.Trigger>}
                                </Tabs.List>
                                {outputRec && (
                                  <Tabs.Content value="output">
                                    <video src={outputRec.url} controls className="w-full rounded" preload="metadata" />
                                    <div className="flex gap-2 mt-1 justify-end">
                                      <a href={outputRec.url} download={outputRec.filename} className="px-3 py-1 bg-emerald-600 text-white rounded hover:bg-emerald-800 transition-colors text-sm">Download</a>
                                    </div>
                                  </Tabs.Content>
                                )}
                                {inputRec && (
                                  <Tabs.Content value="input">
                                    <video src={inputRec.url} controls className="w-full rounded" preload="metadata" />
                                    <div className="flex gap-2 mt-1 justify-end">
                                      <a href={inputRec.url} download={inputRec.filename} className="px-3 py-1 bg-emerald-600 text-white rounded hover:bg-emerald-800 transition-colors text-sm">Download</a>
                                    </div>
                                  </Tabs.Content>
                                )}
                              </Tabs.Root>
                            </div>
                          );
                        })}
                    </div>
                  )}
                </div>
              </div>
            )}

            {isConnected && isComfyUIReady && 
            <ControlPanelsContainer
              isOpen={isControlPanelOpen}
              onOpenChange={setIsControlPanelOpen}
            />}

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
