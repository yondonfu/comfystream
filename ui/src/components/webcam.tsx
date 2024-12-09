import { useCallback, useEffect, useRef } from "react";

interface WebcamProps {
  onStreamReady: (stream: MediaStream) => void;
  deviceId: string;
}

export function Webcam({ onStreamReady, deviceId }: WebcamProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const captureStream = useCallback(() => {
    if (videoRef.current && !streamRef.current) {
      const video = videoRef.current as any;
      const stream = video.captureStream(30);
      streamRef.current = stream;
      onStreamReady(stream);
    }
  }, [onStreamReady]);

  const startWebcam = useCallback(async () => {
    if (!deviceId) return;

    if (videoRef.current?.srcObject instanceof MediaStream) {
      const tracks = videoRef.current.srcObject.getTracks();
      tracks.forEach((track: MediaStreamTrack) => track.stop());
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }

    const stream = await navigator.mediaDevices.getUserMedia({
      video: {
        deviceId: { exact: deviceId },
        width: { ideal: 512 },
        height: { ideal: 512 },
      },
      audio: false
    });

    if (videoRef.current) {
      videoRef.current.srcObject = stream;
      videoRef.current.onloadedmetadata = () => {
        videoRef.current?.play().catch(console.error);
        captureStream();
      };
    }
  }, [deviceId, captureStream]);

  useEffect(() => {
    if (deviceId) {
      startWebcam();
    }

    return () => {
      if (videoRef.current?.srcObject instanceof MediaStream) {
        const tracks = videoRef.current.srcObject.getTracks();
        tracks.forEach((track: MediaStreamTrack) => track.stop());
      }
    };
  }, [deviceId, startWebcam]);

  return (
    <div>
      <video ref={videoRef} autoPlay playsInline />
    </div>
  );
}
