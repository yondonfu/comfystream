import React, { useEffect, useRef, useCallback } from "react";

interface WebcamProps {
  onStreamReady: (stream: MediaStream) => void;
  frameRate: number;
}

export function Webcam({ onStreamReady, frameRate }: WebcamProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const captureStream = useCallback(() => {
    if (videoRef.current) {
      // cast to any because captureStream() not recognized
      const video = videoRef.current as any;
      const stream = video.captureStream(frameRate);

      streamRef.current = stream;

      onStreamReady(stream);
    }
  }, [onStreamReady, frameRate]);

  useEffect(() => {
    const startWebcam = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { exact: 512 },
            height: { exact: 512 },
            frameRate: { ideal: frameRate, max: frameRate },
          },
        });

        if (videoRef.current) videoRef.current.srcObject = stream;

        captureStream();
      } catch (err) {
        console.error(err);
      }
    };

    if (frameRate == 0) return;

    startWebcam();

    return () => {
      if (
        videoRef.current &&
        videoRef.current.srcObject instanceof MediaStream
      ) {
        const tracks = videoRef.current.srcObject.getTracks();
        tracks.forEach((track: MediaStreamTrack) => track.stop());
      }
    };
  }, [frameRate]);

  return (
    <div>
      <video ref={videoRef} autoPlay playsInline />
    </div>
  );
}
