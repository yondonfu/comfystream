"use client";

import { Room } from "@/components/room";
import { PromptContext } from "@/components/settings";
import { useState, useEffect } from "react";

export default function Page() {
  const [originalPrompt, setOriginalPrompt] = useState<any>(null);
  const [currentPrompt, setCurrentPrompt] = useState<any>(null);

  // Update currentPrompt whenever originalPrompt changes
  useEffect(() => {
    if (originalPrompt) {
      setCurrentPrompt(JSON.parse(JSON.stringify(originalPrompt)));
    }
  }, [originalPrompt]);

  return (
    <PromptContext.Provider value={{ 
      originalPrompt, 
      currentPrompt,
      setOriginalPrompt, 
      setCurrentPrompt 
    }}>
      <div className="flex flex-col">
        <div className="w-full">
          <Room />
        </div>
      </div>
    </PromptContext.Provider>
  );
}
