"use client";

import React, { useState, useEffect } from "react";
import { usePeerContext } from "@/context/peer-context";
import { usePrompt } from "./settings";

type InputValue = string | number | boolean;

interface InputInfo {
  value: InputValue;
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
  onStateChange: (
    state: Partial<{
      nodeId: string;
      fieldName: string;
      value: string;
      isAutoUpdateEnabled: boolean;
    }>,
  ) => void;
}

const InputControl = ({
  input,
  value,
  onChange,
}: {
  input: InputInfo;
  value: string;
  onChange: (value: string) => void;
}) => {
  if (input.widget === "combo") {
    const options = Array.isArray(input.value) ? input.value : [];
    return (
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="p-2 border rounded w-full"
      >
        {options.map((option: string) => (
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
          step={
            inputType === "float" ? "0.01" : inputType === "int" ? "1" : "any"
          }
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

export const ControlPanel = ({
  panelState,
  onStateChange,
}: ControlPanelProps) => {
  const { controlChannel } = usePeerContext();
  const { currentPrompts, setCurrentPrompts } = usePrompt();
  const [availableNodes, setAvailableNodes] = useState<
    Record<string, NodeInfo>[]
  >([{}]);
  const [promptIdxToUpdate, setPromptIdxToUpdate] = useState<number>(0);

  // Add ref to track last sent value and timeout
  const lastSentValueRef = React.useRef<{
    nodeId: string;
    fieldName: string;
    value: InputValue;
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
    const currentInput =
      panelState.nodeId && panelState.fieldName
        ? availableNodes[promptIdxToUpdate][panelState.nodeId]?.inputs[
            panelState.fieldName
          ]
        : null;

    if (currentInput) {
      // Validate against min/max if they exist for number types
      if (currentInput.type === "number") {
        const numValue = parseFloat(newValue);
        if (!isNaN(numValue)) {
          if (currentInput.min !== undefined && numValue < currentInput.min)
            return;
          if (currentInput.max !== undefined && numValue > currentInput.max)
            return;
        }
      }
    }

    onStateChange({ value: newValue });
  };

  // Modify the effect that sends updates with debouncing
  useEffect(() => {
    const currentInput =
      panelState.nodeId && panelState.fieldName
        ? availableNodes[promptIdxToUpdate][panelState.nodeId]?.inputs[
            panelState.fieldName
          ]
        : null;
    if (!currentInput || !currentPrompts) return;

    let isValidValue = true;
    let processedValue: InputValue = panelState.value;

    // Validate and process value based on type
    switch (currentInput.type.toLowerCase()) {
      case "number":
        isValidValue =
          /^-?\d*\.?\d*$/.test(panelState.value) && panelState.value !== "";
        processedValue = parseFloat(panelState.value);
        break;
      case "boolean":
        isValidValue =
          panelState.value === "true" || panelState.value === "false";
        processedValue = panelState.value === "true";
        break;
      case "string":
        // String can be empty, so always valid
        processedValue = panelState.value;
        break;
      default:
        if (currentInput.widget === "combo") {
          isValidValue = panelState.value !== "";
          processedValue = panelState.value;
        } else {
          isValidValue = panelState.value !== "";
          processedValue = panelState.value;
        }
    }

    const hasRequiredFields =
      panelState.nodeId.trim() !== "" && panelState.fieldName.trim() !== "";

    // Check if the value has actually changed
    const lastSent = lastSentValueRef.current;
    const hasValueChanged =
      !lastSent ||
      lastSent.nodeId !== panelState.nodeId ||
      lastSent.fieldName !== panelState.fieldName ||
      lastSent.value !== processedValue;

    if (
      controlChannel &&
      panelState.isAutoUpdateEnabled &&
      isValidValue &&
      hasRequiredFields &&
      hasValueChanged
    ) {
      // Clear any existing timeout
      if (updateTimeoutRef.current) {
        clearTimeout(updateTimeoutRef.current);
      }

      // Set a new timeout for the update
      updateTimeoutRef.current = setTimeout(
        () => {
          // Create updated prompt while maintaining current structure
          let hasUpdated = false;
          const updatedPrompts = currentPrompts.map(
            (prompt: any, idx: number) => {
              if (idx !== promptIdxToUpdate) {
                return prompt;
              }
              const updatedPrompt = JSON.parse(JSON.stringify(prompt)); // Deep clone
              if (updatedPrompt[panelState.nodeId]?.inputs) {
                updatedPrompt[panelState.nodeId].inputs[panelState.fieldName] =
                  processedValue;
                hasUpdated = true;
              }
              return updatedPrompt;
            },
          );

          if (hasUpdated) {
            // Update last sent value
            lastSentValueRef.current = {
              nodeId: panelState.nodeId,
              fieldName: panelState.fieldName,
              value: processedValue,
            };

            // Send the full prompts update
            const message = JSON.stringify({
              type: "update_prompts",
              prompts: updatedPrompts,
            });
            controlChannel.send(message);

            // Only update prompts after sending
            setCurrentPrompts(updatedPrompts);
          }
        },
        currentInput.type.toLowerCase() === "number" ? 100 : 300,
      ); // Shorter delay for numbers, longer for text
    }
  }, [
    panelState.value,
    panelState.nodeId,
    panelState.fieldName,
    panelState.isAutoUpdateEnabled,
    controlChannel,
    currentPrompts,
    setCurrentPrompts,
    availableNodes,
    promptIdxToUpdate,
  ]);

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

    const input =
      availableNodes[promptIdxToUpdate][panelState.nodeId]?.inputs[
        selectedField
      ];
    if (input) {
      const initialValue = getInitialValue(input);
      onStateChange({
        fieldName: selectedField,
        value: initialValue,
      });
    } else {
      onStateChange({ fieldName: selectedField });
    }
  };

  return (
    <div className="flex flex-col gap-3 p-3">
      <select
        value={promptIdxToUpdate}
        onChange={(e) => setPromptIdxToUpdate(parseInt(e.target.value))}
        className="p-2 border rounded"
      >
        {currentPrompts &&
          currentPrompts.map((_: any, idx: number) => (
            <option key={idx} value={idx}>
              Prompt {idx}
            </option>
          ))}
      </select>
      <select
        value={panelState.nodeId}
        onChange={(e) => {
          onStateChange({
            nodeId: e.target.value,
            fieldName: "",
            value: "0",
          });
        }}
        className="p-2 border rounded"
      >
        <option value="">Select Node</option>
        {Object.entries(availableNodes[promptIdxToUpdate]).map(([id, info]) => (
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
        {panelState.nodeId &&
          availableNodes[promptIdxToUpdate][panelState.nodeId]?.inputs &&
          Object.entries(
            availableNodes[promptIdxToUpdate][panelState.nodeId].inputs,
          )
            .filter(([_, info]) => {
              const type =
                typeof info.type === "string"
                  ? info.type.toLowerCase()
                  : String(info.type).toLowerCase();
              return [
                "boolean",
                "number",
                "float",
                "int",
                "string",
                "combo",
              ].includes(type);
            })
            .map(([field, info]) => (
              <option key={field} value={field}>
                {field} ({info.type})
              </option>
            ))}
      </select>

      <div className="flex items-center gap-2">
        {panelState.nodeId &&
          panelState.fieldName &&
          availableNodes[promptIdxToUpdate][panelState.nodeId]?.inputs[
            panelState.fieldName
          ] && (
            <InputControl
              input={
                availableNodes[promptIdxToUpdate][panelState.nodeId].inputs[
                  panelState.fieldName
                ]
              }
              value={panelState.value}
              onChange={handleValueChange}
            />
          )}

        {panelState.nodeId &&
          panelState.fieldName &&
          availableNodes[promptIdxToUpdate][panelState.nodeId]?.inputs[
            panelState.fieldName
          ]?.type === "number" && (
            <span className="text-sm text-gray-600">
              {availableNodes[promptIdxToUpdate][panelState.nodeId]?.inputs[
                panelState.fieldName
              ]?.min !== undefined &&
                availableNodes[promptIdxToUpdate][panelState.nodeId]?.inputs[
                  panelState.fieldName
                ]?.max !== undefined &&
                `(${availableNodes[promptIdxToUpdate][panelState.nodeId]?.inputs[panelState.fieldName]?.min} - ${availableNodes[promptIdxToUpdate][panelState.nodeId]?.inputs[panelState.fieldName]?.max})`}
            </span>
          )}
      </div>

      <button
        onClick={toggleAutoUpdate}
        disabled={!controlChannel}
        className={`p-2 rounded ${
          !controlChannel
            ? "bg-gray-300 text-gray-600 cursor-not-allowed"
            : panelState.isAutoUpdateEnabled
              ? "bg-green-500 text-white"
              : "bg-red-500 text-white"
        }`}
      >
        Auto-Update{" "}
        {controlChannel
          ? panelState.isAutoUpdateEnabled
            ? "(ON)"
            : "(OFF)"
          : "(Not Connected)"}
      </button>
    </div>
  );
};
