"use client";

import React, { useState } from "react";
import { usePeerContext } from "@/context/peer-context";

export const ControlPanel = () => {
  const { controlChannel } = usePeerContext();
  const [nodeId, setNodeId] = useState("");
  const [fieldName, setFieldName] = useState("");
  const [value, setValue] = useState("");

  const handleUpdate = () => {
    if (controlChannel) {
      const message = JSON.stringify({
        node_id: nodeId,
        field_name: fieldName,
        value: value,
      });
      controlChannel.send(message);
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
      <button onClick={handleUpdate} disabled={!controlChannel}>
        Update Parameter
      </button>
    </div>
  );
}; 