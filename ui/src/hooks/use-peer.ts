import { PeerProps } from "@/components/peer";
import { Peer } from "@/lib/peer";
import * as React from "react";

const MAX_OFFER_RETRIES = 5;
const OFFER_RETRY_INTERVAL = 500;

export function usePeer(props: PeerProps): Peer {
  const { url, prompt, connect, onConnected, onDisconnected, localStream } =
    props;

  const [peerConnection, setPeerConnection] =
    React.useState<RTCPeerConnection | null>(null);
  const [remoteStream, setRemoteStream] = React.useState<MediaStream | null>(
    null
  );
  const [dataChannel, setDataChannel] = React.useState<RTCDataChannel | null>(
    null
  );

  const connectionStateTimeoutRef = React.useRef(null);
  const currentTracksRef = React.useRef<MediaStreamTrack[]>([]);

  const sendOffer = async (
    url: string,
    offer: RTCSessionDescriptionInit | RTCSessionDescription,
    retry: number = 0
  ): Promise<any> => {
    try {
      const response = await fetch("/api/offer", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          endpoint: url,
          prompt,
          offer,
        }),
      });

      if (!response.ok) {
        throw new Error(`offer HTTP error: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      if (retry < MAX_OFFER_RETRIES) {
        await new Promise((resolve) =>
          setTimeout(resolve, OFFER_RETRY_INTERVAL)
        );
        return sendOffer(url, offer, retry + 1);
      }
      throw error;
    }
  };

  const handleConnectionStateChange = (state: string) => {
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
  };

  const updateTracks = React.useCallback((pc: RTCPeerConnection, newStream: MediaStream) => {
    currentTracksRef.current.forEach(track => {
      const sender = pc.getSenders().find(s => s.track?.id === track.id);
      if (sender) {
        pc.removeTrack(sender);
      }
    });

    const tracks = newStream.getTracks();
    tracks.forEach((track) => {
      pc.addTrack(track, newStream);
    });
    currentTracksRef.current = tracks;
  }, []);

  React.useEffect(() => {
    if (!peerConnection || !localStream) return;

    updateTracks(peerConnection, localStream);
  }, [localStream, peerConnection, updateTracks]);

  React.useEffect(() => {
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

      pc.addTransceiver("video");

      const tracks = localStream.getTracks();
      tracks.forEach((track) => {
        pc.addTrack(track, localStream);
      });
      currentTracksRef.current = tracks;

      const dataChannel = pc.createDataChannel("config");
      setDataChannel(dataChannel);

      pc.ontrack = (event) => {
        if (event.track.kind == "video") {
          setRemoteStream(event.streams[0]);
        }
      };

      pc.onicecandidate = async (event) => {
        if (!event.candidate) {
          const answer = await sendOffer(url, pc.localDescription!);
          await pc.setRemoteDescription(answer);
        }
      };

      pc.onconnectionstatechange = (event) => {
        handleConnectionStateChange(pc.connectionState);
      };

      const createOffer = async () => {
        try {
          const offer = await pc.createOffer();
          await pc.setLocalDescription(offer);
          // onicecandidate will handle sending the offer once ICE gathering is complete
        } catch (error) {
          console.error("Error during negotiation:", error);
        }
      };

      pc.onnegotiationneeded = createOffer;

      createOffer()
    } else {
      if (connectionStateTimeoutRef.current) {
        clearTimeout(connectionStateTimeoutRef.current);
      }
      if (peerConnection) {
        peerConnection.close();
        setPeerConnection(null);
        setRemoteStream(null);
        setDataChannel(null);
        currentTracksRef.current = [];
      }
    }
  }, [connect, peerConnection, localStream]);

  React.useEffect(() => {
    if (!peerConnection) return;

    return () => {
      peerConnection.close();
    };
  }, [peerConnection]);

  return {
    peerConnection,
    remoteStream,
    dataChannel,
  };
}
