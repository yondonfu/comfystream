export interface Peer {
  peerConnection: RTCPeerConnection | null;
  remoteStream: MediaStream | null;
  controlChannel: RTCDataChannel | null;
  dataChannel: RTCDataChannel | null;
  textOutputData: string | null;
}
