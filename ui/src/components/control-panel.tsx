"use client";

import React, { useState, useEffect } from "react";
import { usePeerContext } from "@/context/peer-context";

interface NodeInfo {
  class_type: string;
  inputs: Record<string, any>;
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

  // Validate and send update when value changes and auto-update is enabled
  useEffect(() => {
    // Check if value is a valid integer and required fields are not empty
    const isValidInteger = /^-?\d+$/.test(value);
    const hasRequiredFields = nodeId.trim() !== "" && fieldName.trim() !== "";
    
    if (controlChannel && isAutoUpdateEnabled && isValidInteger && hasRequiredFields) {
      const message = JSON.stringify({
        node_id: nodeId,
        field_name: fieldName,
        value: value,
      });
      console.log("[ControlPanel] Sending message:", message);
      controlChannel.send(message);
    }
  }, [value, nodeId, fieldName, controlChannel, isAutoUpdateEnabled]);

  const toggleAutoUpdate = () => {
    setIsAutoUpdateEnabled(!isAutoUpdateEnabled);
  };

  const handleValueChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    // Allow empty string or valid integers (including negative)
    if (newValue === "" || /^-?\d+$/.test(newValue)) {
      setValue(newValue);
    }
  };

  return (
    <div>
      <select
        value={nodeId}
        onChange={(e) => {
          setNodeId(e.target.value);
          setFieldName(""); // Reset field name when node changes
        }}
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
        onChange={(e) => setFieldName(e.target.value)}
        disabled={!nodeId}
      >
        <option value="">Select Field</option>
        {nodeId && availableNodes[nodeId]?.inputs && 
          Object.keys(availableNodes[nodeId].inputs).map((field) => (
            <option key={field} value={field}>
              {field}
            </option>
          ))
        }
      </select>

      <input
        type="number"
        placeholder="Value"
        value={value}
        onChange={handleValueChange}
        style={{
          width: '100px'
        }}
      />
      <button 
        onClick={toggleAutoUpdate} 
        disabled={!controlChannel}
        style={{
          backgroundColor: controlChannel 
            ? (isAutoUpdateEnabled ? '#4CAF50' : '#ff6b6b') 
            : '#cccccc',
          color: controlChannel ? 'white' : '#666666',
          padding: '8px 16px',
          border: 'none',
          borderRadius: '4px',
          cursor: controlChannel ? 'pointer' : 'not-allowed'
        }}
      >
        Auto-Update {controlChannel 
          ? (isAutoUpdateEnabled ? '(ON)' : '(OFF)') 
          : '(Not Connected)'}
      </button>
    </div>
  );
}; 