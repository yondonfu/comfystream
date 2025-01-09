"use client";

import React, { useState } from "react";
import { ControlPanel } from "./control-panel";
import { Button } from "./ui/button";
import {
  Drawer,
  DrawerContent,
  DrawerTitle,
} from "./ui/drawer";
import { Settings } from "lucide-react";
import { Plus } from "lucide-react"; // Import Plus icon for minimal add button

export const ControlPanelsContainer = () => {
  const [panels, setPanels] = useState<number[]>([0]); // Start with one panel
  const [nextPanelId, setNextPanelId] = useState(1);
  const [isOpen, setIsOpen] = useState(false);

  const addPanel = () => {
    setPanels([...panels, nextPanelId]);
    setNextPanelId(nextPanelId + 1);
  };

  const removePanel = (id: number) => {
    setPanels(panels.filter(panelId => panelId !== id));
  };

  return (
    <>
      <Button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-4 right-4 h-12 w-12 rounded-full p-0 shadow-lg hover:shadow-xl transition-shadow"
        variant="default"
      >
        <Settings className="h-6 w-6" />
      </Button>

      <Drawer 
        open={isOpen} 
        onOpenChange={setIsOpen}
        direction="bottom"
        shouldScaleBackground={false}
      >
        {/* This is a hack to remove the background color of the overlay so the screen is not dimmed when the drawer is open */}
        <style>
          {`
            [data-vaul-overlay] {
              background-color: transparent !important;
              background: transparent !important;
            }
            
            /* Custom scrollbar styling */
            #control-panel-drawer ::-webkit-scrollbar {
              width: 8px;
              height: 8px;
            }
            
            #control-panel-drawer ::-webkit-scrollbar-track {
              background: transparent;
            }
            
            #control-panel-drawer ::-webkit-scrollbar-thumb {
              background: #cbd5e1;
              border-radius: 4px;
            }
            
            #control-panel-drawer ::-webkit-scrollbar-thumb:hover {
              background: #94a3b8;
            }
          `}
        </style>
        <DrawerContent 
          id="control-panel-drawer"
          className="max-h-[50vh] min-h-[200px] bg-background/90 backdrop-blur-md border-t shadow-lg overflow-hidden"
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
                  <div key={id} className="flex-none w-80 border rounded-lg bg-white/95 shadow-sm hover:shadow-md transition-shadow overflow-hidden flex flex-col max-h-[calc(50vh-3rem)]">
                    <div className="flex justify-between items-center p-2 border-b bg-gray-50/80">
                      <span className="font-medium">Control Panel {id + 1}</span>
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
                      <ControlPanel />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </DrawerContent>
      </Drawer>
    </>
  );
}; 