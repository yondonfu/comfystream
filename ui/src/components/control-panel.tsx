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

const InputControl = ({ 
  input, 
  value, 
  onChange 
}: { 
  input: InputInfo, 
  value: string, 
  onChange: (value: string) => void 
}) => {
  console.log("InputControl rendered with:", { input, value }); // Debug log

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
          step={inputType === "int" ? "1" : "any"}
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

export const ControlPanel = () => {
  const { controlChannel } = usePeerContext();
  const { currentPrompt, setCurrentPrompt } = usePrompt();
  const [nodeId, setNodeId] = useState("");
  const [fieldName, setFieldName] = useState("");
  const [value, setValue] = useState("0");
  const [isAutoUpdateEnabled, setIsAutoUpdateEnabled] = useState(false);
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
          } else if (data.type === "prompt_updated") {
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
    const currentInput = nodeId && fieldName ? availableNodes[nodeId]?.inputs[fieldName] : null;
    
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
    
    setValue(newValue);
  };

  // Modify the effect that sends updates with debouncing
  useEffect(() => {
    const currentInput = nodeId && fieldName ? availableNodes[nodeId]?.inputs[fieldName] : null;
    if (!currentInput || !currentPrompt) return;

    let isValidValue = true;
    let processedValue: any = value;

    // Validate and process value based on type
    switch (currentInput.type.toLowerCase()) {
      case 'number':
        isValidValue = /^-?\d*\.?\d*$/.test(value) && value !== '';
        processedValue = parseFloat(value);
        break;
      case 'boolean':
        isValidValue = value === 'true' || value === 'false';
        processedValue = value === 'true';
        break;
      case 'string':
        // String can be empty, so always valid
        processedValue = value;
        break;
      default:
        if (currentInput.widget === 'combo') {
          isValidValue = value !== '';
          processedValue = value;
        } else {
          isValidValue = value !== '';
          processedValue = value;
        }
    }
    
    const hasRequiredFields = nodeId.trim() !== "" && fieldName.trim() !== "";
    
    // Check if the value has actually changed
    const lastSent = lastSentValueRef.current;
    const hasValueChanged = !lastSent || 
      lastSent.nodeId !== nodeId || 
      lastSent.fieldName !== fieldName || 
      lastSent.value !== processedValue;

    if (controlChannel && isAutoUpdateEnabled && isValidValue && hasRequiredFields && hasValueChanged) {
      // Clear any existing timeout
      if (updateTimeoutRef.current) {
        clearTimeout(updateTimeoutRef.current);
      }

      // Set a new timeout for the update
      updateTimeoutRef.current = setTimeout(() => {
        // Create updated prompt while maintaining current structure
        const updatedPrompt = JSON.parse(JSON.stringify(currentPrompt)); // Deep clone
        if (updatedPrompt[nodeId] && updatedPrompt[nodeId].inputs) {
          updatedPrompt[nodeId].inputs[fieldName] = processedValue;
          
          // Update last sent value
          lastSentValueRef.current = {
            nodeId,
            fieldName,
            value: processedValue
          };

          // Send the full prompt update
          const message = JSON.stringify({
            type: "update_prompt",
            prompt: updatedPrompt
          });
          controlChannel.send(message);
          
          // Only update current prompt after sending
          setCurrentPrompt(updatedPrompt);
        }
      }, currentInput.type.toLowerCase() === 'number' ? 100 : 300); // Shorter delay for numbers, longer for text
    }
  }, [value, nodeId, fieldName, controlChannel, isAutoUpdateEnabled, availableNodes, currentPrompt, setCurrentPrompt]);

  const toggleAutoUpdate = () => {
    setIsAutoUpdateEnabled(!isAutoUpdateEnabled);
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
    setFieldName(selectedField);
    
    const input = availableNodes[nodeId]?.inputs[selectedField];
    if (input) {
      const initialValue = getInitialValue(input);
      setValue(initialValue);
    }
  };

  return (
    <div className="flex flex-col gap-4 p-4">
      <select
        value={nodeId}
        onChange={(e) => {
          setNodeId(e.target.value);
          setFieldName(""); // Reset field name when node changes
          setValue("0");    // Reset value when node changes
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
        value={fieldName}
        onChange={handleFieldSelect}
        disabled={!nodeId}
        className="p-2 border rounded"
      >
        <option value="">Select Field</option>
        {nodeId && availableNodes[nodeId]?.inputs && 
          Object.entries(availableNodes[nodeId].inputs)
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
        {nodeId && fieldName && availableNodes[nodeId]?.inputs[fieldName] && (
          <InputControl
            input={availableNodes[nodeId].inputs[fieldName]}
            value={value}
            onChange={handleValueChange}
          />
        )}
        
        {nodeId && fieldName && availableNodes[nodeId]?.inputs[fieldName]?.type === 'number' && (
          <span className="text-sm text-gray-600">
            {availableNodes[nodeId]?.inputs[fieldName]?.min !== undefined && 
             availableNodes[nodeId]?.inputs[fieldName]?.max !== undefined && 
              `(${availableNodes[nodeId]?.inputs[fieldName]?.min} - ${availableNodes[nodeId]?.inputs[fieldName]?.max})`
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
            : isAutoUpdateEnabled 
              ? 'bg-green-500 text-white'
              : 'bg-red-500 text-white'
        }`}
      >
        Auto-Update {controlChannel 
          ? (isAutoUpdateEnabled ? '(ON)' : '(OFF)') 
          : '(Not Connected)'}
      </button>
    </div>
  );
}; 