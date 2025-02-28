"use client";

import { Room } from "@/components/room";
import { PromptContext } from "@/components/settings";
import { useState, useEffect } from "react";
import { Prompt } from "@/types";

export default function Page() {
  const [originalPrompts, setOriginalPrompts] = useState<Prompt[] | null>(null);
  const [currentPrompts, setCurrentPrompts] = useState<Prompt[] | null>(null);

  // Update currentPrompt whenever originalPrompt changes
  useEffect(() => {
    if (originalPrompts) {
      setCurrentPrompts(JSON.parse(JSON.stringify(originalPrompts)));
    }
  }, [originalPrompts]);

  return (
    <PromptContext.Provider
      value={{
        originalPrompts,
        currentPrompts,
        setOriginalPrompts,
        setCurrentPrompts,
      }}
    >
      <div className="flex flex-col">
        <div className="w-full">
          <Room />
        </div>
      </div>
    </PromptContext.Provider>
  );
}
