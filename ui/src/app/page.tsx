"use client";

import { Room } from "@/components/room";
import { PromptContext } from "@/components/settings";
import { useState, useEffect } from "react";

// Read query params once at page load
function getQueryParams() {
  if (typeof window === 'undefined') return undefined;
  
  const searchParams = new URLSearchParams(window.location.search);
  const frameRateParam = searchParams.get('frameRate');
  const workflowParam = searchParams.get('workflow');
  
  return {
    streamUrl: searchParams.get('streamUrl') || undefined,
    frameRate: frameRateParam ? parseInt(frameRateParam) : undefined,
    videoDevice: searchParams.get('videoDevice') || undefined,
    audioDevice: searchParams.get('audioDevice') || undefined,
    workflowUrl: searchParams.get('workflowUrl') || undefined,
    workflow: workflowParam ? JSON.parse(decodeURIComponent(workflowParam)) : undefined,
    skipDialog: searchParams.get('skipDialog') === 'true'
  };
}

export default function Page() {
  const [originalPrompts, setOriginalPrompts] = useState<any>(null);
  const [currentPrompts, setCurrentPrompts] = useState<any>(null);
  const [queryParams] = useState(getQueryParams); // Read once on mount

  // Update currentPrompt whenever originalPrompt changes
  useEffect(() => {
    if (originalPrompts) {
      setCurrentPrompts(JSON.parse(JSON.stringify(originalPrompts)));
    }
  }, [originalPrompts]);

  return (
    <PromptContext.Provider value={{ 
      originalPrompts, 
      currentPrompts,
      setOriginalPrompts, 
      setCurrentPrompts 
    }}>
      <div className="flex flex-col">
        <div className="w-full">
          <Room initialParams={queryParams} />
        </div>
      </div>
    </PromptContext.Provider>
  );
}
