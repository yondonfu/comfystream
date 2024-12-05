"use client";

import React, { useState } from "react";
import { ControlPanel } from "./control-panel";
import { Button } from "./ui/button";

export const ControlPanelsContainer = () => {
  const [panels, setPanels] = useState<number[]>([0]); // Start with one panel
  const [nextPanelId, setNextPanelId] = useState(1);

  const addPanel = () => {
    setPanels([...panels, nextPanelId]);
    setNextPanelId(nextPanelId + 1);
  };

  const removePanel = (id: number) => {
    setPanels(panels.filter(panelId => panelId !== id));
  };

  return (
    <section className="w-full p-4">
      <div className="mb-4">
        <Button 
          onClick={addPanel}
          className="w-full max-w-xs mx-auto bg-blue-500 hover:bg-blue-600 text-white"
        >
          + Add New Control Panel
        </Button>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {panels.map((id) => (
          <div key={id} className="border rounded-lg bg-white">
            <div className="flex justify-between items-center p-2 border-b">
              <span className="font-medium">Control Panel {id + 1}</span>
              <Button
                onClick={() => removePanel(id)}
                variant="destructive"
                size="sm"
              >
                Remove
              </Button>
            </div>
            <ControlPanel />
          </div>
        ))}
      </div>
    </section>
  );
}; 