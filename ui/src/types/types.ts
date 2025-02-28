/**
 * @file Contains types for the application.
 */

/** Interface representing a prompt object. */
export interface Prompt {
    [key: string]: object;
}

// Types for the Comfystream server WebRTC communication

/** Comfystream WebRTC offer response. */
export interface OfferResponse {
    sdp: string;
    type: string;
}
