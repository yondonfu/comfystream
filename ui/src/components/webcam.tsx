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
      // cast to any because captureStream() not recognized
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
        ...(deviceId ? { deviceId: { exact: deviceId } } : {}),
        width: { exact: 512 },
        height: { exact: 512 },
      },
    });

    if (videoRef.current) {
      videoRef.current.srcObject = stream;
      captureStream();
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
