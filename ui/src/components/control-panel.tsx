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
      controlChannel.send(JSON.stringify({ type: "get_nodes" }));
      
      // Set up listener for node information
      controlChannel.addEventListener("message", (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "nodes_info") {
            setAvailableNodes(data.nodes);
          }
        } catch (error) {
          console.error("Error parsing node info:", error);
        }
      });
    }
  }, [controlChannel]);

  const handleValueChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    const currentInput = nodeId && fieldName ? availableNodes[nodeId]?.inputs[fieldName] : null;
    
    if (currentInput) {
      // Validate against min/max if they exist
      const numValue = parseFloat(newValue);
      if (!isNaN(numValue)) {
        if (currentInput.min !== undefined && numValue < currentInput.min) return;
        if (currentInput.max !== undefined && numValue > currentInput.max) return;
      }
    }
    
    setValue(newValue);
  };

  // Validate and send update when value changes and auto-update is enabled
  useEffect(() => {
    const currentInput = nodeId && fieldName ? availableNodes[nodeId]?.inputs[fieldName] : null;
    if (!currentInput) return;

    const isValidValue = currentInput.type === 'number' 
      ? /^-?\d*\.?\d*$/.test(value)  // Allow decimals for number type
      : /^-?\d+$/.test(value);       // Only integers for other types
    
    const hasRequiredFields = nodeId.trim() !== "" && fieldName.trim() !== "";
    
    if (controlChannel && isAutoUpdateEnabled && isValidValue && hasRequiredFields) {
      const message = JSON.stringify({
        node_id: nodeId,
        field_name: fieldName,
        value: currentInput.type === 'number' ? parseFloat(value) : parseInt(value),
      });
      console.log("[ControlPanel] Sending message:", message);
      controlChannel.send(message);
    }
  }, [value, nodeId, fieldName, controlChannel, isAutoUpdateEnabled, availableNodes]);

  const toggleAutoUpdate = () => {
    setIsAutoUpdateEnabled(!isAutoUpdateEnabled);
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
        onChange={(e) => {
          setFieldName(e.target.value);
          // Set initial value based on current input value or default to 0
          const input = availableNodes[nodeId]?.inputs[e.target.value];
          setValue(input?.value?.toString() || "0");
        }}
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
        <input
          type="number"
          value={value}
          onChange={handleValueChange}
          min={nodeId && fieldName ? availableNodes[nodeId]?.inputs[fieldName]?.min : undefined}
          max={nodeId && fieldName ? availableNodes[nodeId]?.inputs[fieldName]?.max : undefined}
          step={nodeId && fieldName && availableNodes[nodeId]?.inputs[fieldName]?.type === 'number' ? 'any' : '1'}
          className="p-2 border rounded w-32"
        />
        
        {nodeId && fieldName && (
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