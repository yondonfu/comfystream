export interface Peer {
  peerConnection: RTCPeerConnection | null;
  remoteStream: MediaStream | null;
  dataChannel: RTCDataChannel | null;
  controlChannel: RTCDataChannel | null;
}
