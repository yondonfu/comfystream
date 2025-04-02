import * as React from "react";

interface StreamControlProps {
  className?: string;
}

export function StreamControl({ className = "" }: StreamControlProps) {
  // Generate the stream URL when the component mounts
  const getStreamUrl = () => {
    const hostname = window.location.hostname;
    const port = "8889"; // Server port for the HTTP stream
    
    // Check if we're in a hosted environment by looking at the current URL
    const isHosted = window.location.pathname.includes('/live');
    const pathPrefix = isHosted ? '/live' : '';
    
    return `http://${hostname}:${port}${pathPrefix}/stream.html`;
  };
  
  // Open the stream in a new window
  const openStreamWindow = () => {
    const streamUrl = getStreamUrl();
    window.open(streamUrl, 'ComfyStream OBS Capture', 'width=1280,height=720');
  };

  return (
    <button 
      onClick={openStreamWindow} 
      className={`absolute bottom-4 right-4 z-10 p-2 bg-black/50 hover:bg-black/70 text-white rounded-full transition-colors ${className}`}
      title="Open stream for OBS capture"
      aria-label="Cast to external display"
    >
      {/* Screencast icon */}
      <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <path d="M21 3H3c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h18c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H3V5h18v14z"/>
        <path d="M5 14v2h3v-2H5zm4.5 0v2h3v-2h-3zm4.5 0v2h5v-2h-5z"/>
        <path d="M8 10l5 3-5 3z"/>
      </svg>
      <span className="sr-only">Cast to external display</span>
      <span className="absolute bottom-full right-0 mb-1 hidden hover:block text-xs whitespace-nowrap bg-black/75 px-2 py-1 rounded">Cast to OBS</span>
    </button>
  );
}
