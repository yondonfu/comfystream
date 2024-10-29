import { Peer } from "@/lib/peer";
import * as React from "react";

export const PeerContext = React.createContext<Peer | undefined>(undefined);

export function usePeerContext() {
  const ctx = React.useContext(PeerContext);
  if (!ctx) {
    throw new Error("tried to access peer context outside of Peer component");
  }
  return ctx;
}
