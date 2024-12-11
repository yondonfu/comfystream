"use client";

import React, { useState, useEffect } from "react";
import { usePeerContext } from "@/context/peer-context";

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
  const [nodeId, setNodeId] = useState("");
  const [fieldName, setFieldName] = useState("");
  const [value, setValue] = useState("0");
  const [isAutoUpdateEnabled, setIsAutoUpdateEnabled] = useState(false);
  const [availableNodes, setAvailableNodes] = useState<Record<string, NodeInfo>>({});

  // Request available nodes when control channel is established
  useEffect(() => {
    if (controlChannel) {
      console.log("[ControlPanel] Sending get_nodes request");
      controlChannel.send(JSON.stringify({ type: "get_nodes" }));
      
      controlChannel.addEventListener("message", (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log("[ControlPanel] Received message:", data);
          if (data.type === "nodes_info") {
            console.log("[ControlPanel] Setting available nodes:", data.nodes);
            setAvailableNodes(data.nodes);
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

  // Modify the effect that sends updates
  useEffect(() => {
    const currentInput = nodeId && fieldName ? availableNodes[nodeId]?.inputs[fieldName] : null;
    if (!currentInput) return;

    let isValidValue = true;
    let processedValue: any = value;

    // Validate and process value based on type
    switch (currentInput.type) {
      case 'number':
        isValidValue = /^-?\d*\.?\d*$/.test(value);
        processedValue = parseFloat(value);
        break;
      case 'boolean':
        processedValue = value === 'true';
        break;
      case 'string':
        processedValue = value;
        break;
      default:
        if (currentInput.widget === 'combo') {
          processedValue = value;
        } else {
          isValidValue = true;
          processedValue = value;
        }
    }
    
    const hasRequiredFields = nodeId.trim() !== "" && fieldName.trim() !== "";
    
    if (controlChannel && isAutoUpdateEnabled && isValidValue && hasRequiredFields) {
      const message = JSON.stringify({
        node_id: nodeId,
        field_name: fieldName,
        value: processedValue,
      });
      console.log("[ControlPanel] Sending message:", message);
      controlChannel.send(message);
    }
  }, [value, nodeId, fieldName, controlChannel, isAutoUpdateEnabled, availableNodes]);

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
      console.log("Setting initial value:", { field: selectedField, input, initialValue }); // Debug log
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
          Object.entries(availableNodes[nodeId].inputs).map(([field, info]) => (
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