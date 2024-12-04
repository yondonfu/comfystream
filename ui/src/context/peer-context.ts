import * as React from "react";

interface PeerContextType {
  remoteStream: MediaStream | null;
  controlChannel: RTCDataChannel | null;
}

export const PeerContext = React.createContext<PeerContextType>({
  remoteStream: null,
  controlChannel: null,
});

export function usePeerContext() {
  const ctx = React.useContext(PeerContext);
  if (!ctx) {
    throw new Error("tried to access peer context outside of Peer component");
  }
  return ctx;
}
