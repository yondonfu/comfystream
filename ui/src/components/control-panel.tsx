import { usePeerContext } from "@/context/peer-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useState } from "react";

export function ControlPanel() {
  const { controlChannel } = usePeerContext();
  const [nodeId, setNodeId] = useState("");
  const [fieldName, setFieldName] = useState("");
  const [value, setValue] = useState("");

  const handleUpdate = () => {
    if (!controlChannel) return;

    const message = {
      node_id: nodeId,
      field_name: fieldName,
      value: value,
    };

    controlChannel.send(JSON.stringify(message));
  };

  return (
    <div className="fixed bottom-4 left-4 p-4 bg-background border rounded-lg shadow-lg">
      <div className="space-y-4">
        <div>
          <Input
            placeholder="Node ID"
            value={nodeId}
            onChange={(e) => setNodeId(e.target.value)}
          />
        </div>
        <div>
          <Input
            placeholder="Field Name"
            value={fieldName}
            onChange={(e) => setFieldName(e.target.value)}
          />
        </div>
        <div>
          <Input
            placeholder="Value"
            value={value}
            onChange={(e) => setValue(e.target.value)}
          />
        </div>
        <Button 
          onClick={handleUpdate}
          disabled={!controlChannel}
          className="w-full"
        >
          Update Parameter
        </Button>
      </div>
    </div>
  );
} 