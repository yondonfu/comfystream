import { Peer } from "@/lib/peer";
import { PeerProps } from "@/components/peer";
import { OfferResponse } from "@/types";
import { useState, useEffect, useRef, useCallback } from "react";

const MAX_OFFER_RETRIES = 5;
const OFFER_RETRY_INTERVAL = 500;

export function usePeer(props: PeerProps): Peer {
  const { url, prompts, connect, onConnected, onDisconnected, localStream } =
    props;

  const [peerConnection, setPeerConnection] =
    useState<RTCPeerConnection | null>(null);
  const [remoteStream, setRemoteStream] = useState<MediaStream | null>(null);
  const [controlChannel, setControlChannel] = useState<RTCDataChannel | null>(
    null,
  );
  const [dataChannel, setDataChannel] = useState<RTCDataChannel | null>(null);
  const [textOutputData, setTextOutputData] = useState<string | null>(null);

  const connectionStateTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const sendOffer = useCallback(
    async (
      url: string,
      offer: RTCSessionDescriptionInit | RTCSessionDescription,
      retry: number = 0,
    ): Promise<OfferResponse> => {
      try {
        const response = await fetch("/api/offer", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            endpoint: url,
            prompts: prompts,
            offer,
            resolution: props.resolution,
          }),
        });

        if (!response.ok) {
          throw new Error(`offer HTTP error: ${response.status}`);
        }
        return (await response.json()) as OfferResponse;
      } catch (error) {
        if (retry < MAX_OFFER_RETRIES) {
          await new Promise((resolve) =>
            setTimeout(resolve, OFFER_RETRY_INTERVAL),
          );
          return sendOffer(url, offer, retry + 1);
        }
        throw error;
      }
    },
    [prompts],
  );

  const handleConnectionStateChange = useCallback(
    (state: string) => {
      switch (state) {
        case "connected":
          onConnected();
          break;
        case "disconnected":
          onDisconnected();
          break;
        default:
          break;
      }
    },
    [onConnected, onDisconnected],
  );

  useEffect(() => {
    if (connect) {
      if (peerConnection) return;
      if (!localStream) return;

      const configuration = {
        iceServers: [
          {
            urls: ["stun:stun.l.google.com:19302"],
          },
        ],
      };

      const pc = new RTCPeerConnection(configuration);
      setPeerConnection(pc);

      if (localStream.getVideoTracks().length > 0) {
        pc.addTransceiver("video");
      }
      
      if (localStream.getAudioTracks().length > 0) {
        pc.addTransceiver("audio");
      }

      localStream.getTracks().forEach((track) => {
        pc.addTrack(track, localStream);
        if (track.kind === 'audio') {
          console.log(`[usePeer] Audio track - enabled: ${track.enabled}, readyState: ${track.readyState}, muted: ${track.muted}`);
        }
      });

      const control = pc.createDataChannel("control");
      setControlChannel(control);

      control.onopen = () => {
        console.log("[usePeer] Control channel opened, readyState:", control.readyState);

        if (props.resolution) {
          setTimeout(() => {
            const resolution = props.resolution!;
            const resolutionMessage = {
              type: "update_resolution",
              width: resolution.width,
              height: resolution.height,
            };
            control.send(JSON.stringify(resolutionMessage));
            console.log("[usePeer] Sent resolution configuration:", resolutionMessage);
          }, 200);
        }
      };

      control.onclose = () => {
        console.log("[usePeer] Control channel closed");
        setControlChannel(null);
      };

      control.onmessage = (event) => {
        console.log("Received message on control channel:", event.data);
      };

      control.onerror = (error) => {
        console.error("Control channel error:", error);
      };

      const data = pc.createDataChannel("data");
      setDataChannel(data);

      data.onopen = () => {
        console.log("[usePeer] Data channel opened, readyState:", data.readyState);
      };

      data.onclose = () => {
        console.log("[usePeer] Data channel closed");
        setDataChannel(null);
      };

      data.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message.type === "text") {
            console.log("[usePeer] Received text data:", message.data);
            setTextOutputData(message.data);
          } else {
            console.warn("[usePeer] Unknown message type:", message.type);
          }
        } catch (error) {
          console.error("[usePeer] Error parsing data channel message:", error);
        }
      };

      data.onerror = (error) => {
        console.error("Data channel error:", error);
      };

      pc.ontrack = (event) => {
        if (event.streams && event.streams[0]) {
          setRemoteStream(event.streams[0]);
        }
      };

      pc.onicecandidate = async (event) => {
        if (!event.candidate) {
          const offerResponse = await sendOffer(url, pc.localDescription!);
          const answer: RTCSessionDescriptionInit = {
            sdp: offerResponse.sdp,
            type: offerResponse.type as RTCSdpType,
          };
          await pc.setRemoteDescription(answer);
        }
      };

      pc.onconnectionstatechange = () => {
        handleConnectionStateChange(pc.connectionState);
      };

      const createOffer = async () => {
        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);
      };

      createOffer().catch(console.error);
    } else {
      if (connectionStateTimeoutRef.current) {
        clearTimeout(connectionStateTimeoutRef.current);
      }
      if (peerConnection) {
        peerConnection.close();
      }
      setControlChannel(null);
      setDataChannel(null);
      setRemoteStream(null);
      setPeerConnection(null);
    }
  }, [
    connect,
    localStream,
    peerConnection,
    sendOffer,
    url,
    handleConnectionStateChange,
    props.resolution,
  ]);

  useEffect(() => {
    if (controlChannel && controlChannel.readyState === "open" && props.resolution) {
      const resolution = props.resolution;
      const resolutionMessage = {
        type: "update_resolution",
        width: resolution.width,
        height: resolution.height,
      };
      controlChannel.send(JSON.stringify(resolutionMessage));
      console.log("[usePeer] Updated resolution configuration:", resolutionMessage);
    }
  }, [controlChannel, props.resolution]);

  return {
    peerConnection,
    remoteStream,
    controlChannel,
    dataChannel,
    textOutputData,
  };
}
