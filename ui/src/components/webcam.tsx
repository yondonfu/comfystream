import React, { useEffect, useRef, useCallback } from "react";

interface WebcamProps {
  onStreamReady: (stream: MediaStream) => void;
}

export function Webcam({ onStreamReady }: WebcamProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const captureStream = useCallback(() => {
    if (videoRef.current) {
      // cast to any because captureStream() not recognized
      const video = videoRef.current as any;
      const stream = video.captureStream(30);

      streamRef.current = stream;

      onStreamReady(stream);
    }
  }, [onStreamReady]);

  useEffect(() => {
    const startWebcam = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { exact: 512 },
            height: { exact: 512 },
          },
        });

        if (videoRef.current) videoRef.current.srcObject = stream;

        captureStream();
      } catch (err) {
        console.error(err);
      }
    };

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
  }, []);

  return (
    <div>
      <video ref={videoRef} autoPlay playsInline />
    </div>
  );
}
