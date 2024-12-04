import { useCallback, useEffect, useRef, useState } from "react";
import { Select } from "./ui/select";

interface WebcamProps {
  onStreamReady: (stream: MediaStream) => void;
}

interface VideoDevice {
  deviceId: string;
  label: string;
}

export function Webcam({ onStreamReady }: WebcamProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [videoDevices, setVideoDevices] = useState<VideoDevice[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<string>("");
  const [error, setError] = useState<string>("");

  const getVideoDevices = useCallback(async () => {
    try {
      await navigator.mediaDevices.getUserMedia({ video: true });

      const devices = await navigator.mediaDevices.enumerateDevices();
      const videoDevices = devices
        .filter(device => device.kind === 'videoinput')
        .map(device => ({
          deviceId: device.deviceId,
          label: device.label || `Camera ${device.deviceId.slice(0, 5)}...`
        }));

      setVideoDevices(videoDevices);
      if (videoDevices.length > 0 && !selectedDevice) {
        setSelectedDevice(videoDevices[0].deviceId);
      }
    } catch (err) {
      setError('Failed to get video devices');
    }
  }, []);

  const captureStream = useCallback(() => {
    if (videoRef.current && !streamRef.current) {
      try {
        const video = videoRef.current as any;
        const stream = video.captureStream(30);
        streamRef.current = stream;
        onStreamReady(stream);
      } catch (err) {
        setError('Failed to capture stream');
      }
    }
  }, [onStreamReady]);

  const startWebcam = useCallback(async () => {
    if (!selectedDevice) return;

    try {
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
          deviceId: { exact: selectedDevice },
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
        videoRef.current.onerror = () => {
          setError('Video playback error');
        };
      }
    } catch (err) {
      setError('Failed to start webcam');
    }
  }, [selectedDevice, captureStream]);

  // Initial setup
  useEffect(() => {
    getVideoDevices();
    navigator.mediaDevices.addEventListener('devicechange', getVideoDevices);

    return () => {
      navigator.mediaDevices.removeEventListener('devicechange', getVideoDevices);
      if (videoRef.current?.srcObject instanceof MediaStream) {
        const tracks = videoRef.current.srcObject.getTracks();
        tracks.forEach((track: MediaStreamTrack) => track.stop());
      }
    };
  }, [getVideoDevices]);

  // Handle device selection changes
  useEffect(() => {
    if (selectedDevice) {
      startWebcam();
    }
  }, [selectedDevice, startWebcam]);

  return (
    <div className="space-y-4">
      {error && (
        <div className="text-red-500 text-sm">{error}</div>
      )}
      {videoDevices.length > 1 && (
        <Select
          value={selectedDevice}
          onValueChange={setSelectedDevice}
        >
          <Select.Trigger className="w-[200px]">
            {videoDevices.find(d => d.deviceId === selectedDevice)?.label || 'Select camera'}
          </Select.Trigger>
          <Select.Content>
            {videoDevices.map((device) => (
              <Select.Option key={device.deviceId} value={device.deviceId}>
                {device.label}
              </Select.Option>
            ))}
          </Select.Content>
        </Select>
      )}
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        className="rounded-lg w-[512px] h-[512px] object-cover bg-black"
      />
    </div>
  );
}
