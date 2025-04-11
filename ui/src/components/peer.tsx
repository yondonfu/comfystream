import * as React from "react";
import { Prompt } from "@/types";
import { usePeer } from "@/hooks/use-peer";
import { PeerContext } from "@/context/peer-context";

export interface PeerProps extends React.HTMLAttributes<HTMLDivElement> {
  url: string;
  prompts: Prompt[] | null;
  connect: boolean;
  onConnected: () => void;
  onDisconnected: () => void;
  localStream: MediaStream | null;
}

export const PeerConnector = (props: PeerProps) => {
  const peer = usePeer(props);

  console.log("[PeerConnector] Peer context value:", {
    hasControlChannel: !!peer?.controlChannel,
    controlChannelState: peer?.controlChannel?.readyState,
  });

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
