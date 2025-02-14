"use client";

import React, { useState, useEffect } from "react";
import { usePeerContext } from "@/context/peer-context";
import { usePrompt } from "./settings";

interface InputInfo {
  value: any;
  type: string;
  min?: number;
  max?: number;
  widget?: string;
}

interface NodeInfo {
  class_type: string;
  inputs: Record<string, InputInfo>;
}

interface ControlPanelProps {
  panelState: {
    nodeId: string;
    fieldName: string;
    value: string;
    isAutoUpdateEnabled: boolean;
  };
  onStateChange: (state: Partial<{
    nodeId: string;
    fieldName: string;
    value: string;
    isAutoUpdateEnabled: boolean;
  }>) => void;
}

const InputControl = ({ 
  input, 
  value, 
  onChange 
}: { 
  input: InputInfo, 
  value: string, 
  onChange: (value: string) => void 
}) => {

  if (input.widget === "combo") {
    return (
      <select 
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="p-2 border rounded w-full"
      >
        {Array.isArray(input.value) && input.value.map((option: string) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    );
  }

  // Convert type to lowercase for consistent comparison
  const inputType = input.type.toLowerCase();

  switch (inputType) {
    case "boolean":
      return (
        <input
          type="checkbox"
          checked={value === "true"}
          onChange={(e) => onChange(e.target.checked.toString())}
          className="w-5 h-5"
        />
      );
    case "number":
    case "float":
    case "int":
      return (
        <input
          type="number"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          min={input.min}
          max={input.max}
          step={inputType === "float" ? "0.01" : inputType === "int" ? "1" : "any"}
          className="p-2 border rounded w-32"
        />
      );
    case "string":
      return (
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="p-2 border rounded w-full"
        />
      );
    default:
      console.warn(`Unhandled input type: ${input.type}`); // Debug log
      return (
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="p-2 border rounded w-full"
        />
      );
  }
};

export const ControlPanel = ({ panelState, onStateChange }: ControlPanelProps) => {
  const { controlChannel } = usePeerContext();
  const { currentPrompts, setCurrentPrompts } = usePrompt();
  const [availableNodes, setAvailableNodes] = useState<Record<string, NodeInfo>>({});
  
  // Add ref to track last sent value and timeout
  const lastSentValueRef = React.useRef<{
    nodeId: string;
    fieldName: string;
    value: any;
  } | null>(null);
  const updateTimeoutRef = React.useRef<NodeJS.Timeout | null>(null);

  // Cleanup function for the timeout
  useEffect(() => {
    return () => {
      if (updateTimeoutRef.current) {
        clearTimeout(updateTimeoutRef.current);
      }
    };
  }, []);

  // Request available nodes when control channel is established
  useEffect(() => {
    if (controlChannel) {
      controlChannel.send(JSON.stringify({ type: "get_nodes" }));
      
      controlChannel.addEventListener("message", (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "nodes_info") {
            setAvailableNodes(data.nodes);
          } else if (data.type === "prompts_updated") {
            if (!data.success) {
              console.error("[ControlPanel] Failed to update prompt");
            }
          }
        } catch (error) {
          console.error("[ControlPanel] Error parsing node info:", error);
        }
      });
    }
  }, [controlChannel]);

  const handleValueChange = (newValue: string) => {
    const currentInput = panelState.nodeId && panelState.fieldName ? availableNodes[panelState.nodeId]?.inputs[panelState.fieldName] : null;
    
    if (currentInput) {
      // Validate against min/max if they exist for number types
      if (currentInput.type === 'number') {
        const numValue = parseFloat(newValue);
        if (!isNaN(numValue)) {
          if (currentInput.min !== undefined && numValue < currentInput.min) return;
          if (currentInput.max !== undefined && numValue > currentInput.max) return;
        }
      }
    }
    
    onStateChange({ value: newValue });
  };

  // Modify the effect that sends updates with debouncing
  useEffect(() => {
    const currentInput = panelState.nodeId && panelState.fieldName ? availableNodes[panelState.nodeId]?.inputs[panelState.fieldName] : null;
    if (!currentInput || !currentPrompts) return;

    let isValidValue = true;
    let processedValue: any = panelState.value;

    // Validate and process value based on type
    switch (currentInput.type.toLowerCase()) {
      case 'number':
        isValidValue = /^-?\d*\.?\d*$/.test(panelState.value) && panelState.value !== '';
        processedValue = parseFloat(panelState.value);
        break;
      case 'boolean':
        isValidValue = panelState.value === 'true' || panelState.value === 'false';
        processedValue = panelState.value === 'true';
        break;
      case 'string':
        // String can be empty, so always valid
        processedValue = panelState.value;
        break;
      default:
        if (currentInput.widget === 'combo') {
          isValidValue = panelState.value !== '';
          processedValue = panelState.value;
        } else {
          isValidValue = panelState.value !== '';
          processedValue = panelState.value;
        }
    }
    
    const hasRequiredFields = panelState.nodeId.trim() !== "" && panelState.fieldName.trim() !== "";
    
    // Check if the value has actually changed
    const lastSent = lastSentValueRef.current;
    const hasValueChanged = !lastSent || 
      lastSent.nodeId !== panelState.nodeId || 
      lastSent.fieldName !== panelState.fieldName || 
      lastSent.value !== processedValue;

    if (controlChannel && panelState.isAutoUpdateEnabled && isValidValue && hasRequiredFields && hasValueChanged) {
      // Clear any existing timeout
      if (updateTimeoutRef.current) {
        clearTimeout(updateTimeoutRef.current);
      }

      // Set a new timeout for the update
      updateTimeoutRef.current = setTimeout(() => {
        // Create updated prompt while maintaining current structure
        const currentPrompt = currentPrompts[0];
        const updatedPrompt = JSON.parse(JSON.stringify(currentPrompt)); // Deep clone
        if (updatedPrompt[panelState.nodeId] && updatedPrompt[panelState.nodeId].inputs) {
          updatedPrompt[panelState.nodeId].inputs[panelState.fieldName] = processedValue;
          
          // Update last sent value
          lastSentValueRef.current = {
            nodeId: panelState.nodeId,
            fieldName: panelState.fieldName,
            value: processedValue
          };

          // Send the full prompt update
          const message = JSON.stringify({
            type: "update_prompts",
            prompts: [updatedPrompt]
          });
          controlChannel.send(message);
          
          // Only update current prompt after sending
          setCurrentPrompts([updatedPrompt]);
        }
      }, currentInput.type.toLowerCase() === 'number' ? 100 : 300); // Shorter delay for numbers, longer for text
    }
  }, [panelState.value, panelState.nodeId, panelState.fieldName, panelState.isAutoUpdateEnabled, controlChannel, availableNodes, currentPrompts, setCurrentPrompts]);

  const toggleAutoUpdate = () => {
    onStateChange({ isAutoUpdateEnabled: !panelState.isAutoUpdateEnabled });
  };

  // Modified to handle initial values better
  const getInitialValue = (input: InputInfo): string => {
    if (input.type.toLowerCase() === "boolean") {
      return (!!input.value).toString();
    }
    if (input.widget === "combo" && Array.isArray(input.value)) {
      return input.value[0]?.toString() || "";
    }
    return input.value?.toString() || "0";
  };

  // Update the field selection handler
  const handleFieldSelect = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const selectedField = e.target.value;
    
    const input = availableNodes[panelState.nodeId]?.inputs[selectedField];
    if (input) {
      const initialValue = getInitialValue(input);
      onStateChange({ 
        fieldName: selectedField,
        value: initialValue
      });
    } else {
      onStateChange({ fieldName: selectedField });
    }
  };

  return (
    <div className="flex flex-col gap-3 p-3">
      <select
        value={panelState.nodeId}
        onChange={(e) => {
          onStateChange({
            nodeId: e.target.value,
            fieldName: "",
            value: "0"
          });
        }}
        className="p-2 border rounded"
      >
        <option value="">Select Node</option>
        {Object.entries(availableNodes).map(([id, info]) => (
          <option key={id} value={id}>
            {id} ({info.class_type})
          </option>
        ))}
      </select>

      <select
        value={panelState.fieldName}
        onChange={handleFieldSelect}
        disabled={!panelState.nodeId}
        className="p-2 border rounded"
      >
        <option value="">Select Field</option>
        {panelState.nodeId && availableNodes[panelState.nodeId]?.inputs && 
          Object.entries(availableNodes[panelState.nodeId].inputs)
            .filter(([_, info]) => {
              const type = typeof info.type === 'string' ? info.type.toLowerCase() : String(info.type).toLowerCase();
              return ['boolean', 'number', 'float', 'int', 'string'].includes(type) || info.widget === 'combo';
            })
            .map(([field, info]) => (
              <option key={field} value={field}>
                {field} ({info.type}{info.widget ? ` - ${info.widget}` : ''})
              </option>
            ))
        }
      </select>

      <div className="flex items-center gap-2">
        {panelState.nodeId && panelState.fieldName && availableNodes[panelState.nodeId]?.inputs[panelState.fieldName] && (
          <InputControl
            input={availableNodes[panelState.nodeId].inputs[panelState.fieldName]}
            value={panelState.value}
            onChange={handleValueChange}
          />
        )}
        
        {panelState.nodeId && panelState.fieldName && availableNodes[panelState.nodeId]?.inputs[panelState.fieldName]?.type === 'number' && (
          <span className="text-sm text-gray-600">
            {availableNodes[panelState.nodeId]?.inputs[panelState.fieldName]?.min !== undefined && 
             availableNodes[panelState.nodeId]?.inputs[panelState.fieldName]?.max !== undefined && 
              `(${availableNodes[panelState.nodeId]?.inputs[panelState.fieldName]?.min} - ${availableNodes[panelState.nodeId]?.inputs[panelState.fieldName]?.max})`
            }
          </span>
        )}
      </div>

      <button 
        onClick={toggleAutoUpdate} 
        disabled={!controlChannel}
        className={`p-2 rounded ${
          !controlChannel 
            ? 'bg-gray-300 text-gray-600 cursor-not-allowed'
            : panelState.isAutoUpdateEnabled 
              ? 'bg-green-500 text-white'
              : 'bg-red-500 text-white'
        }`}
      >
        Auto-Update {controlChannel 
          ? (panelState.isAutoUpdateEnabled ? '(ON)' : '(OFF)') 
          : '(Not Connected)'}
      </button>
    </div>
  );
}; 