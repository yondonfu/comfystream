"use client";
// WebRTC Preview Popup Page (client-only)

import React, { useEffect, useRef, useState, useCallback } from "react";

const POLL_INTERVAL_MS = 300;
const MAX_ATTEMPTS = 200; // ~60s

export default function WebRTCPopupPage() {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const localStreamRef = useRef<MediaStream | null>(null);
  const parentStreamRef = useRef<MediaStream | null>(null);
  const clonedIdsRef = useRef<Set<string>>(new Set());
  const attemptsRef = useRef(0);
  const intervalRef = useRef<number | null>(null);
  const [status, setStatus] = useState("Initializing…");

  const clearIntervalInternal = useCallback(() => {
    if (intervalRef.current !== null) {
      window.clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const scheduleClose = useCallback((delay = 800) => {
    window.setTimeout(() => {
      try { window.close(); } catch { /* noop */ }
    }, delay);
  }, []);

  const validateOpener = useCallback((): boolean => {
    try {
      if (!window.opener) {
        setStatus("Opener lost. Closing…");
        scheduleClose();
        return false;
      }
      void window.opener.location.href; // cross-origin check
      return true;
    } catch {
      setStatus("Cross-origin opener. Closing…");
      scheduleClose();
      return false;
    }
  }, [scheduleClose]);

  const attachVideoIfNeeded = () => {
    if (!localStreamRef.current) return;
    const video = videoRef.current;
    if (video && video.srcObject !== localStreamRef.current) {
      video.srcObject = localStreamRef.current;
    }
  };

  const cloneTracks = useCallback(() => {
    if (!validateOpener()) return;
    // @ts-ignore - global from opener context
    const parentStream: MediaStream | undefined = window.opener?.__comfystreamRemoteStream;
    if (!parentStream) {
      setStatus("Waiting for stream…");
      return;
    }
    if (!localStreamRef.current) {
      localStreamRef.current = new MediaStream();
    }
    // Parent stream changed -> reset
    if (parentStreamRef.current && parentStreamRef.current !== parentStream) {
      localStreamRef.current.getTracks().forEach(t => { try { t.stop(); } catch { /* */ } });
      localStreamRef.current = new MediaStream();
      clonedIdsRef.current.clear();
    }
    parentStreamRef.current = parentStream;

    let added = false;
    parentStream.getTracks().forEach(src => {
      if (src.readyState === "ended") return;
      if (!clonedIdsRef.current.has(src.id)) {
        try {
          const clone = src.clone();
          clone.addEventListener("ended", () => {
            clonedIdsRef.current.delete(src.id);
          });
          localStreamRef.current!.addTrack(clone);
          clonedIdsRef.current.add(src.id);
          added = true;
        } catch {
          /* skip */
        }
      }
    });
    // Cleanup ended clones
    localStreamRef.current.getTracks().forEach(t => {
      if (t.readyState === "ended") {
        localStreamRef.current!.removeTrack(t);
        try { t.stop(); } catch { /* */ }
      }
    });
    if (added) {
      attachVideoIfNeeded();
      setStatus("Live");
      videoRef.current?.play().catch(() => {});
    }
  }, [validateOpener]);

  useEffect(() => {
    if (typeof window === "undefined") return; // safety
    attemptsRef.current = 0;
    setStatus("Initializing…");

    const tick = () => {
      attemptsRef.current += 1;
      if (!validateOpener()) {
        clearIntervalInternal();
        return;
      }
      // @ts-ignore
      if (!window.opener.__comfystreamRemoteStream) {
        setStatus("Parent stream ended");
        clearIntervalInternal();
        scheduleClose(1200);
        return;
      }
      cloneTracks();
      if (attemptsRef.current >= MAX_ATTEMPTS && (!localStreamRef.current || localStreamRef.current.getTracks().length === 0)) {
        setStatus("Timeout waiting for stream");
        clearIntervalInternal();
        scheduleClose(1500);
      }
    };

    intervalRef.current = window.setInterval(tick, POLL_INTERVAL_MS);
    cloneTracks();

    const beforeUnload = () => {
      clearIntervalInternal();
      localStreamRef.current?.getTracks().forEach(t => { try { t.stop(); } catch { /* */ } });
    };
    window.addEventListener("beforeunload", beforeUnload);
    return () => {
      window.removeEventListener("beforeunload", beforeUnload);
      clearIntervalInternal();
      localStreamRef.current?.getTracks().forEach(t => { try { t.stop(); } catch { /* */ } });
    };
  }, [cloneTracks, clearIntervalInternal, validateOpener, scheduleClose]);

  return (
    <div style={{
      margin: 0,
      background: "#000",
      height: "100vh",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontFamily: "sans-serif",
      position: "relative"
    }}>
      <video
        id="webrtc_preview"
        ref={videoRef}
        autoPlay
        playsInline
        muted
        style={{ maxWidth: "100%", maxHeight: "100%", background: "#000" }}
      />
      <div id="status" style={{
        color: "#0f0",
        position: "absolute",
        top: 6,
        left: 8,
        textAlign: "left",
        font: "12px monospace",
        textShadow: "0 0 4px #000"
      }}>{status}</div>
    </div>
  );
}
