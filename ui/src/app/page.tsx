"use client";

import { Room } from "@/components/room";
import { ControlPanelsContainer } from "@/components/control-panels-container";
import { PromptContext } from "@/components/settings";
import { useState } from "react";

export default function Page() {
  const [originalPrompt, setOriginalPrompt] = useState<any>(null);

  return (
    <PromptContext.Provider value={{ originalPrompt, setOriginalPrompt }}>
      <div className="flex flex-col">
        <div className="w-full">
          <Room />
        </div>
      </div>
    </PromptContext.Provider>
  );
}
