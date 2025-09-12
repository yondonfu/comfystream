/**
 * @file Contains a StreamSettings component for configuring stream settings.
 */
import { useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Drawer,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useMediaQuery } from "@/hooks/use-media-query";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Suspense,
  useCallback,
  useEffect,
  useState,
  createContext,
  useContext,
  useRef,
} from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Select } from "./ui/select";
import { Prompt } from "@/types";
import { toast } from "sonner";

export interface StreamConfig {
  streamUrl: string;
  frameRate: number;
  prompts?: Prompt[] | null;
  selectedVideoDeviceId: string;
  selectedAudioDeviceId: string;
  resolution: {
    width: number;
    height: number;
  };
}

interface AVDevice {
  deviceId: string;
  label: string;
}

export const DEFAULT_CONFIG: StreamConfig = {
  streamUrl:
    process.env.NEXT_PUBLIC_DEFAULT_STREAM_URL || "http://localhost:8889",
  frameRate: 30,
  selectedVideoDeviceId: "",
  selectedAudioDeviceId: "",
  resolution: {
    width: 512,
    height: 512
  },
};

interface StreamSettingsProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (config: StreamConfig) => void;
}

export function StreamSettings({
  open,
  onOpenChange,
  onSave,
}: StreamSettingsProps) {
  return (
    <Suspense fallback={<div>Loading settings...</div>}>
      <StreamSettingsInner
        open={open}
        onOpenChange={onOpenChange}
        onSave={onSave}
      />
    </Suspense>
  );
}

function StreamSettingsInner({
  open,
  onOpenChange,
  onSave,
}: StreamSettingsProps) {
  const isDesktop = useMediaQuery("(min-width: 768px)");
  const searchParams = useSearchParams();

  const initialConfig: StreamConfig = {
    ...DEFAULT_CONFIG,
    streamUrl: searchParams.get("streamUrl") || DEFAULT_CONFIG.streamUrl,
    frameRate: parseInt(
      searchParams.get("frameRate") || `${DEFAULT_CONFIG.frameRate}`,
      10,
    ),
  };
  const [config, setConfig] = useState<StreamConfig>(initialConfig);

  const handleSubmit = (config: StreamConfig) => {
    setConfig(config);
    onSave(config);
    onOpenChange(false);
  };

  if (isDesktop) {
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent aria-describedby={undefined}>
          <DialogHeader className="text-left">
            <DialogTitle>
              <div className="mt-4">Stream Settings</div>
            </DialogTitle>
          </DialogHeader>
          <ConfigForm config={config} onSubmit={handleSubmit} />
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent>
        <DrawerHeader className="text-left">
          <DrawerTitle>Stream Settings</DrawerTitle>
        </DrawerHeader>
        <div className="px-4">
          <ConfigForm config={config} onSubmit={handleSubmit} />
        </div>
      </DrawerContent>
    </Drawer>
  );
}

const formSchema = z.object({
  streamUrl: z.string().url(),
  frameRate: z.coerce.number(),
  resolution: z.object({
    width: z.coerce.number().refine(val => val % 64 === 0 && val >= 64 && val <= 2048, {
      message: "Width must be a multiple of 64 (between 64 and 2048)"
    }),
    height: z.coerce.number().refine(val => val % 64 === 0 && val >= 64 && val <= 2048, {
      message: "Height must be a multiple of 64 (between 64 and 2048)"
    })
  })
});

interface ConfigFormProps {
  config: StreamConfig;
  onSubmit: (config: StreamConfig) => void;
}

interface PromptContextType {
  originalPrompts: Prompt[] | null;
  currentPrompts: Prompt[] | null;
  setOriginalPrompts: (prompts: Prompt[]) => void;
  setCurrentPrompts: (prompts: Prompt[]) => void;
}

export const PromptContext = createContext<PromptContextType>({
  originalPrompts: null,
  currentPrompts: null,
  setOriginalPrompts: () => { },
  setCurrentPrompts: () => { },
});

export const usePrompt = () => useContext(PromptContext);

function ConfigForm({ config, onSubmit }: ConfigFormProps) {
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const { setOriginalPrompts } = usePrompt();
  const [videoDevices, setVideoDevices] = useState<AVDevice[]>([]);
  const [audioDevices, setAudioDevices] = useState<AVDevice[]>([]);
  const [selectedVideoDevice, setSelectedVideoDevice] = useState<
    string | undefined
  >(config.selectedVideoDeviceId);
  const [selectedAudioDevice, setSelectedAudioDevice] = useState<
    string | undefined
  >(config.selectedAudioDeviceId);

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: config,
  });

  // Ensure we request permissions once and enumerate devices without racing
  const isEnumeratingRef = useRef(false);
  const hasRequestedPermissionRef = useRef(false);

  const refreshDevices = useCallback(async () => {
    if (isEnumeratingRef.current) return;
    isEnumeratingRef.current = true;
    try {
      // Request permissions once per session if needed
      if (!hasRequestedPermissionRef.current) {
        try {
          const permissionStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
          permissionStream.getTracks().forEach(track => track.stop());
          hasRequestedPermissionRef.current = true;
        } catch (err) {
          // If permission denied or device busy, continue to enumerateDevices so we can still list placeholders
          console.warn("Media permission request failed; proceeding to enumerate devices:", err);
        }
      }

      const devices = await navigator.mediaDevices.enumerateDevices();

      const nextVideoDevices: AVDevice[] = [
        { deviceId: "none", label: "No Video" },
        ...devices
          .filter((d) => d.kind === "videoinput")
          .map((d) => ({
            deviceId: d.deviceId,
            label: d.label || `Camera ${d.deviceId.slice(0, 5)}...`,
          })),
      ];
      setVideoDevices(nextVideoDevices);

      const nextAudioDevices: AVDevice[] = [
        { deviceId: "none", label: "No Audio" },
        ...devices
          .filter((d) => d.kind === "audioinput")
          .map((d) => ({
            deviceId: d.deviceId,
            label: d.label || `Microphone ${d.deviceId.slice(0, 5)}...`,
          })),
      ];
      setAudioDevices(nextAudioDevices);

      // Set defaults only if nothing selected yet
      if (selectedVideoDevice === "" && nextVideoDevices.length > 1) {
        setSelectedVideoDevice(nextVideoDevices[1].deviceId);
      }
      if (selectedAudioDevice === "" && nextAudioDevices.length > 1) {
        setSelectedAudioDevice(nextAudioDevices[1].deviceId);
      }
    } catch (error) {
      console.error("Failed to enumerate devices:", error);
      toast.error("Failed to list media devices", {
        description: "Check camera/microphone permissions and connection.",
      });
    } finally {
      isEnumeratingRef.current = false;
    }
  }, [selectedVideoDevice, selectedAudioDevice]);

  // Handle device change events with a single enumerator.
  useEffect(() => {
    refreshDevices();
    const handler = () => refreshDevices();
    navigator.mediaDevices.addEventListener("devicechange", handler);
    return () => {
      navigator.mediaDevices.removeEventListener("devicechange", handler);
    };
  }, [refreshDevices]);

  const handleSubmit = (values: z.infer<typeof formSchema>) => {
    onSubmit({
      ...values,
      streamUrl: values.streamUrl
        ? values.streamUrl.replace(/\/+$/, "")
        : values.streamUrl,
      prompts: prompts,
      selectedVideoDeviceId: selectedVideoDevice || "none",
      selectedAudioDeviceId: selectedAudioDevice || "none",
      resolution: values.resolution || DEFAULT_CONFIG.resolution,
    });
  };

  const handlePromptsChange = async (
    e: React.ChangeEvent<HTMLInputElement>,
  ) => {
    if (!e.target.files?.length) return;

    try {
      const files = Array.from(e.target.files);
      const fileReads = files.map(async (file) => {
        const text = await file.text();
        return JSON.parse(text);
      });

      const allPrompts = await Promise.all(fileReads);
      setPrompts(allPrompts);
      setOriginalPrompts(allPrompts);
    } catch (err) {
      console.error("Failed to parse one or more JSON files.", err);
      toast.error("Failed to Parse Workflow", {
        description: "Please upload a valid JSON file.",
      });
    }
  };

  /**
   * Handles the camera selection.
   * @param deviceId - The device ID of the selected camera.
   */
  const handleCameraSelect = (deviceId: string) => {
    if (deviceId !== "" && deviceId !== selectedVideoDevice) {
      setSelectedVideoDevice(deviceId);
    }
  };

  /**
   * Handles the microphone selection.
   * @param deviceId - The device ID of the selected microphone.
   */
  const handleMicrophoneSelect = (deviceId: string) => {
    if (deviceId !== "" && deviceId !== selectedAudioDevice) {
      setSelectedAudioDevice(deviceId);
    }
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(handleSubmit)} autoComplete="off">
        <FormField
          control={form.control}
          name="streamUrl"
          render={({ field }) => (
            <FormItem className="mt-4">
              <FormLabel>Stream URL</FormLabel>
              <FormControl>
                <Input placeholder="Stream URL" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="frameRate"
          render={({ field }) => (
            <FormItem className="mt-4">
              <FormLabel>Frame Rate</FormLabel>
              <FormControl>
                <Input placeholder="Frame Rate" {...field} type="number" />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="grid grid-cols-2 gap-4">
          <FormField
            control={form.control}
            name="resolution.width"
            render={({ field }) => (
              <FormItem className="mt-4">
                <FormLabel>Width</FormLabel>
                <FormControl>
                  <Input
                    type="number"
                    min="64"
                    max="2048"
                    step="64"
                    {...field}
                    onChange={(e) => {
                      const value = parseInt(e.target.value);
                      field.onChange(value);
                    }}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="resolution.height"
            render={({ field }) => (
              <FormItem className="mt-4">
                <FormLabel>Height</FormLabel>
                <FormControl>
                  <Input
                    type="number"
                    min="64"
                    max="2048"
                    step="64"
                    {...field}
                    onChange={(e) => {
                      const value = parseInt(e.target.value);
                      field.onChange(value);
                    }}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <div className="mt-4 mb-4">
          <Label>Camera</Label>
          {/* TODO: Temporary fix to Warn if no camera or mic; improve later */}
          <Select
            required={selectedAudioDevice == "none" && selectedVideoDevice == "none" ? true : false}
            value={selectedVideoDevice == "none" ? "" : selectedVideoDevice}
            onValueChange={handleCameraSelect}
          >
            <Select.Trigger className="w-full mt-2">
              {selectedVideoDevice
                ? videoDevices.find((d) => d.deviceId === selectedVideoDevice)
                  ?.label || "None"
                : "None"}
            </Select.Trigger>
            <Select.Content>
              {videoDevices.length === 0 ? (
                <Select.Option disabled value="no-devices">
                  No camera devices found
                </Select.Option>
              ) : (
                videoDevices.map((device) => (
                  <Select.Option key={device.deviceId} value={device.deviceId}>
                    {device.label}
                  </Select.Option>
                ))
              )}
            </Select.Content>
          </Select>
        </div>

        <div className="mt-4 mb-4">
          <Label>Microphone</Label>
          <Select
            value={selectedAudioDevice}
            onValueChange={handleMicrophoneSelect}
          >
            <Select.Trigger className="w-full mt-2">
              {selectedAudioDevice
                ? audioDevices.find((d) => d.deviceId === selectedAudioDevice)
                  ?.label || "None"
                : "None"}
            </Select.Trigger>
            <Select.Content>
              {audioDevices.length === 0 ? (
                <Select.Option disabled value="no-devices">
                  No audio devices found
                </Select.Option>
              ) : (
                audioDevices
                  .filter(
                    (device) =>
                      device.deviceId !== undefined && device.deviceId != "",
                  )
                  .map((device) => (
                    <Select.Option
                      key={device.deviceId}
                      value={device.deviceId}
                    >
                      {device.label}
                    </Select.Option>
                  ))
              )}
            </Select.Content>
          </Select>
        </div>

        <div className="mt-4 mb-4 grid max-w-sm items-center gap-3">
          <Label>Comfy Workflows</Label>
          <Input
            id="workflow"
            type="file"
            accept=".json"
            multiple
            onChange={handlePromptsChange}
            required={false}
          />
          <div className="text-sm text-gray-500">
            Optional: Leave empty for passthrough mode
          </div>
        </div>

        <Button type="submit" className="w-full mt-4 mb-4">
          {prompts.length > 0 ? "Start Stream with Workflow" : "Start Passthrough Stream"}
        </Button>
      </form>
    </Form>
  );
}
