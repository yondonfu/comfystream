import * as React from "react";
import { useState, useCallback } from "react";

interface StreamControlProps {
  className?: string;
}

export function StreamControl({ className = "" }: StreamControlProps) {
  const [isLoading, setIsLoading] = useState(false);

  // Open popup which polls opener for stream and clones tracks locally (no postMessage MediaStream cloning)
  const openWebRTCPopup = useCallback(() => {
    const features = 'width=1024,height=1024';
    const getBasePath = (): string => {
      try {
        const scripts = document.querySelectorAll('script[src]');
        for (const s of Array.from(scripts)) {
          const src = (s as HTMLScriptElement).src;
            // Look for /_next/static/ which precedes hashed chunks
          const idx = src.indexOf('/_next/static/');
          if (idx !== -1) {
            const urlObj = new URL(src);
            const before = urlObj.pathname.substring(0, urlObj.pathname.indexOf('/_next/static/'));
            if (before !== undefined) {
              return before.replace(/\/$/, '');
            }
          }
        }
      } catch { /* ignore */ }

      try {
        const { pathname } = window.location;
        // If pathname points to a file (no trailing slash and contains a dot), strip file portion
        if (/\.[a-zA-Z0-9]{2,8}$/.test(pathname.split('/').pop() || '')) {
          const parts = pathname.split('/');
          parts.pop();
          return parts.join('/') || '/';
        }
        return pathname.replace(/\/$/, '');
      } catch { /* ignore */ }

      return '';
    };

  const basePath = getBasePath();
  const isDev = process.env.NEXT_PUBLIC_DEV === 'true';
  const previewPath = (basePath ? basePath : '') + (isDev ? '/webrtc-preview' : '/webrtc-preview.html');

    const popup = window.open(previewPath, 'comfystream_preview', features) || window.open(previewPath);
    if (!popup) {
      alert('Popup blocked. Please allow popups for this site.');
    }
  }, []);

  const openStreamWindow = () => {
    openWebRTCPopup();
  };

  return (
    <button 
  onClick={openStreamWindow}
  disabled={isLoading}
  className={`absolute bottom-4 right-4 z-10 p-2 bg-black/50 hover:bg-black/70 text-white rounded-full transition-colors ${className}`}
  title={"Open WebRTC preview (cloned tracks)"} 
  aria-label="Open WebRTC preview"
    >
      <svg 
        xmlns="http://www.w3.org/2000/svg" 
        viewBox="0 0 512 512" 
        className="w-6 h-6 fill-current"
      >
        <path d="M352 0c-12.9 0-24.6 7.8-29.6 19.8s-2.2 25.7 6.9 34.9L370.7 96 201.4 265.4c-12.5 12.5-12.5 32.8 0 45.3s32.8 12.5 45.3 0L416 141.3l41.4 41.4c9.2 9.2 22.9 11.9 34.9 6.9s19.8-16.6 19.8-29.6l0-128c0-17.7-14.3-32-32-32L352 0zM80 32C35.8 32 0 67.8 0 112L0 432c0 44.2 35.8 80 80 80l320 0c44.2 0 80-35.8 80-80l0-112c0-17.7-14.3-32-32-32s-32 14.3-32 32l0 112c0 8.8-7.2 16-16 16L80 448c-8.8 0-16-7.2-16-16l0-320c0-8.8 7.2-16 16-16l112 0c17.7 0 32-14.3 32-32s-14.3-32-32-32L80 32z"/>
      </svg>
    </button>
  );
}
