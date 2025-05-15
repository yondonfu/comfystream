"use client";

import React, { useState } from "react";
import { ControlPanel } from "./control-panel";
import { Button } from "./ui/button";
import { Drawer, DrawerContent, DrawerTitle } from "./ui/drawer";
import { Settings } from "lucide-react";
import { Plus } from "lucide-react"; // Import Plus icon for minimal add button

// Add prop types
export type ControlPanelsContainerProps = {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
};

export const ControlPanelsContainer = ({ isOpen, onOpenChange }: ControlPanelsContainerProps) => {
  const [panels, setPanels] = useState<number[]>([0]); // Start with one panel
  const [nextPanelId, setNextPanelId] = useState(1);
  const [panelStates, setPanelStates] = useState<
    Record<
      number,
      {
        nodeId: string;
        fieldName: string;
        value: string;
        isAutoUpdateEnabled: boolean;
      }
    >
  >({
    0: {
      nodeId: "",
      fieldName: "",
      value: "0",
      isAutoUpdateEnabled: false,
    },
  });

  const addPanel = () => {
    const newId = nextPanelId;
    setPanels([...panels, newId]);
    setPanelStates((prev) => ({
      ...prev,
      [newId]: {
        nodeId: "",
        fieldName: "",
        value: "0",
        isAutoUpdateEnabled: false,
      },
    }));
    setNextPanelId(nextPanelId + 1);
  };

  const removePanel = (id: number) => {
    setPanels(panels.filter((panelId) => panelId !== id));
    setPanelStates((prev) => {
      const newState = { ...prev };
      delete newState[id];
      return newState;
    });
  };

  const updatePanelState = (
    id: number,
    state: Partial<(typeof panelStates)[number]>,
  ) => {
    setPanelStates((prev) => ({
      ...prev,
      [id]: {
        ...prev[id],
        ...state,
      },
    }));
  };

  return (
    <Drawer
      open={isOpen}
      onOpenChange={onOpenChange}
      direction="bottom"
      shouldScaleBackground={false}
    >
      <DrawerContent
        id="control-panel-drawer"
        className="max-h-[50vh] min-h-[200px] bg-background/90 backdrop-blur-md border-t shadow-lg overflow-hidden"
        style={{ position: 'fixed', bottom: 0, left: 0, right: 0, zIndex: 50 }}
      >
        <DrawerTitle className="sr-only">Control Panels</DrawerTitle>

        <div className="flex h-full">
          {/* Left side add button */}
          <div className="w-12 border-r flex items-start pt-4 justify-center bg-background/50">
            <Button
              onClick={addPanel}
              variant="ghost"
              size="icon"
              className="h-8 w-8 rounded-md bg-blue-500 hover:bg-blue-600 active:bg-blue-700 transition-colors shadow-sm hover:shadow text-white"
              title="Add control panel"
              aria-label="Add control panel"
              data-tooltip="Add control panel"
            >
              <Plus className="h-4 w-4" />
            </Button>
          </div>

          {/* Control panels container */}
          <div className="flex-1 overflow-x-auto">
            <div className="flex gap-4 p-4 min-h-0">
              {panels.map((id) => (
                <div
                  key={id}
                  className="flex-none w-80 border rounded-lg bg-white/95 shadow-sm hover:shadow-md transition-shadow overflow-hidden flex flex-col max-h-[calc(50vh-3rem)]"
                >
                  <div className="flex justify-between items-center p-2 border-b bg-gray-50/80">
                    <span className="font-medium">
                      Control Panel {id + 1}
                    </span>
                    <Button
                      onClick={() => removePanel(id)}
                      variant="ghost"
                      size="sm"
                      className="h-6 w-6 rounded-full p-0 hover:bg-gray-200/80 transition-colors"
                    >
                      <span className="text-sm">×</span>
                    </Button>
                  </div>
                  <div className="flex-1 overflow-y-auto">
                    <ControlPanel
                      panelState={panelStates[id]}
                      onStateChange={(state) => updatePanelState(id, state)}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </DrawerContent>
    </Drawer>
  );
};
