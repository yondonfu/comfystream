"use client";

import React, { useState } from "react";
import { usePeerContext } from "@/context/peer-context";

export const ControlPanel = () => {
  const { controlChannel } = usePeerContext();
  console.log("[ControlPanel] Control channel:", {
    exists: !!controlChannel,
    readyState: controlChannel?.readyState
  });

  const [nodeId, setNodeId] = useState("46"); // Default node ID
  const [fieldName, setFieldName] = useState("hue_shift"); // Default field name
  const [value, setValue] = useState("0"); // Default value

  const handleUpdate = () => {
    if (controlChannel) {
      const message = JSON.stringify({
        node_id: nodeId,
        field_name: fieldName,
        value: value,
      });
      console.log("[ControlPanel] Sending message:", message);
      controlChannel.send(message);
    } else {
      console.warn("[ControlPanel] Attempted to send message but controlChannel is null");
    }
  };

  return (
    <div>
      <input
        type="text"
        placeholder="Node ID"
        value={nodeId}
        onChange={(e) => setNodeId(e.target.value)}
      />
      <input
        type="text"
        placeholder="Field Name"
        value={fieldName}
        onChange={(e) => setFieldName(e.target.value)}
      />
      <input
        type="text"
        placeholder="Value"
        value={value}
        onChange={(e) => setValue(e.target.value)}
      />
      <button 
        onClick={handleUpdate} 
        disabled={!controlChannel}
        style={{
          backgroundColor: controlChannel ? '#4CAF50' : '#cccccc',
          color: controlChannel ? 'white' : '#666666',
          padding: '8px 16px',
          border: 'none',
          borderRadius: '4px',
          cursor: controlChannel ? 'pointer' : 'not-allowed'
        }}
      >
        Update Parameter {controlChannel ? '(Ready)' : '(Not Connected)'}
      </button>
    </div>
  );
}; 