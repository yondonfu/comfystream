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
    null
  );

  const connectionStateTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const sendOffer = useCallback(
    async (
      url: string,
      offer: RTCSessionDescriptionInit | RTCSessionDescription,
      retry: number = 0
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
          }),
        });

        if (!response.ok) {
          throw new Error(`offer HTTP error: ${response.status}`);
        }
        return (await response.json()) as OfferResponse;
      } catch (error) {
        if (retry < MAX_OFFER_RETRIES) {
          await new Promise((resolve) =>
            setTimeout(resolve, OFFER_RETRY_INTERVAL)
          );
          return sendOffer(url, offer, retry + 1);
        }
        throw error;
      }
    },
    [prompts]
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
    [onConnected, onDisconnected]
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

      localStream.getTracks().forEach((track) => {
        pc.addTrack(track, localStream);
      });

      // Create control channel for both negotiation and control
      const channel = pc.createDataChannel("control");

      channel.onopen = () => {
        console.log(
          "[usePeer] Control channel opened, readyState:",
          channel.readyState
        );
        setControlChannel(channel);
      };

      channel.onclose = () => {
        console.log("[usePeer] Control channel closed");
        setControlChannel(null);
      };

      pc.ontrack = (event) => {
        if (event.streams && event.streams[0]) {
          setRemoteStream(event.streams[0]);
        }
      };

      channel.onerror = (error) => {
        console.error("Control channel error:", error);
      };

      channel.onmessage = (event) => {
        console.log("Received message on control channel:", event.data);
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
  ]);

  return {
    peerConnection,
    remoteStream,
    controlChannel,
  };
}
