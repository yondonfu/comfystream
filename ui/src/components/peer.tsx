import * as React from "react";
import { usePeer } from "@/hooks/use-peer";
import { PeerContext } from "@/context/peer-context";

export interface PeerProps extends React.HTMLAttributes<HTMLDivElement> {
  url: string;
  prompt: any;
  connect: boolean;
  onConnected: () => void;
  onDisconnected: () => void;
  localStream: MediaStream | null;
}

export const PeerConnector = (props: PeerProps) => {
  const peer = usePeer(props);

  return (
    <div>
      {peer && (
        <PeerContext.Provider value={peer}>
          {props.children}
        </PeerContext.Provider>
      )}
    </div>
  );
};