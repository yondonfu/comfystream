import * as React from "react";
import { useState } from "react";

interface StreamControlProps {
  className?: string;
  backendUrl: string;
}

export function StreamControl({ className = "", backendUrl }: StreamControlProps) {
  const [isLoading, setIsLoading] = useState(false);
  
  // Generate the stream URL with a unique streamID from the server
  const getStreamUrl = async (): Promise<string | null> => {
    try {
      // Validate backendUrl
      if (!backendUrl) {
        console.error("Backend URL is not configured.");
        throw new Error("Backend URL is not configured in settings.");
      }

      // Parse base URL from the provided backendUrl
      let baseUrl: string;
      try {
        // The origin property gives us "http://hostname:port"
        baseUrl = new URL(backendUrl).origin;
      } catch (e) {
        console.error("Invalid backend URL configured:", backendUrl, e);
        throw new Error(`Invalid backend URL configured: ${backendUrl}`);
      }
      
      // Check if we're in a hosted environment by looking at the current URL
      // This might need adjustment depending on how hosted environments are detected
      const isHosted = window.location.pathname.includes('/live');
      const pathPrefix = isHosted ? '/live' : '';
      
      // Request a unique streamID from the server using the derived baseUrl
      const response = await fetch(`${baseUrl}${pathPrefix}/api/stream-token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `Failed to get stream token: ${response.status}`);
      }
      
      const data = await response.json();
      const streamId = data.stream_id;
      
      // Return the URL with the unique streamID, using the derived baseUrl
      // Note: Token will be removed from URL in a later step
      return `${baseUrl}${pathPrefix}/stream.html?token=${streamId}`;
    } catch (error) {
      console.error('Error getting stream URL:', error);
      return null;
    }
  };
  
  // Open the stream in a new window
  const openStreamWindow = async () => {
    try {
      setIsLoading(true);
      const streamUrl = await getStreamUrl();
      
      if (!streamUrl) {
        throw new Error('Failed to get stream URL');
      }
      
      const newWindow = window.open(streamUrl, 'ComfyStream OBS Capture', 'width=1024,height=1024');
      
      if (!newWindow) {
        throw new Error('Failed to open stream window. Please check your popup blocker settings.');
      }
    } catch (error) {
      console.error('Error opening stream window:', error);
      alert(error instanceof Error ? error.message : 'Failed to open stream window. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <button 
      onClick={openStreamWindow}
      // Disable only when loading
      disabled={isLoading} 
      className={`absolute bottom-4 right-4 z-10 p-2 bg-black/50 hover:bg-black/70 text-white rounded-full transition-colors ${className} ${isLoading ? 'opacity-50 cursor-wait' : ''}`}
      // Restore original title
      title={"Open stream for OBS capture"} 
      aria-label="Cast to external display"
    >
      {/* Screencast icon */}
      <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <path d="M21 3H3c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h18c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H3V5h18v14z"/>
        <path d="M5 14v2h3v-2H5zm4.5 0v2h3v-2h-3zm4.5 0v2h5v-2h-5z"/>
        <path d="M8 10l5 3-5 3z"/>
      </svg>
    </button>
  );
}
