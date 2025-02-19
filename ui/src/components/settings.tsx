/**
 * @file Contains a StreamSettings component for configuring stream settings.
 */
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
  useCallback,
  useEffect,
  useState,
  createContext,
  useContext,
} from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Select } from "./ui/select";
import { toast } from "sonner";

export interface StreamConfig {
  streamUrl: string;
  frameRate: number;
  prompts?: any;
  selectedVideoDeviceId: string;
  selectedAudioDeviceId: string;
}

interface AVDevice {
  deviceId: string;
  label: string;
}

export const DEFAULT_CONFIG: StreamConfig = {
  streamUrl:
    process.env.NEXT_PUBLIC_DEFAULT_STREAM_URL || "http://127.0.0.1:8889",
  frameRate: 30,
  selectedVideoDeviceId: "none",
  selectedAudioDeviceId: "none",
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
  const isDesktop = useMediaQuery("(min-width: 768px)");

  const [config, setConfig] = useState<StreamConfig>(DEFAULT_CONFIG);

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
});

interface ConfigFormProps {
  config: StreamConfig;
  onSubmit: (config: StreamConfig) => void;
}

interface PromptContextType {
  originalPrompts: any;
  currentPrompts: any;
  setOriginalPrompts: (prompts: any) => void;
  setCurrentPrompts: (prompts: any) => void;
}

export const PromptContext = createContext<PromptContextType>({
  originalPrompts: null,
  currentPrompts: null,
  setOriginalPrompts: () => {},
  setCurrentPrompts: () => {},
});

export const usePrompt = () => useContext(PromptContext);

function ConfigForm({ config, onSubmit }: ConfigFormProps) {
  const [prompts, setPrompts] = useState<any[]>([]);
  const { setOriginalPrompts } = usePrompt();
  const [videoDevices, setVideoDevices] = useState<AVDevice[]>([]);
  const [audioDevices, setAudioDevices] = useState<AVDevice[]>([]);
  const [selectedVideoDevice, setSelectedVideoDevice] = useState<string | undefined>(config.selectedVideoDeviceId);
  const [selectedAudioDevice, setSelectedAudioDevice] = useState<string | undefined>(config.selectedAudioDeviceId);

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: config,
  });

  /**
   * Retrieves the list of video devices available on the user's device.
   */
  const getVideoDevices = useCallback(async () => {
    try {
      await navigator.mediaDevices.getUserMedia({ video: true });

      const devices = await navigator.mediaDevices.enumerateDevices();
      const videoDevices = [
        { deviceId: "none", label: "No Video" },
        ...devices
        .filter((device) => device.kind === "videoinput")
        .map((device) => ({
          deviceId: device.deviceId,
          label: device.label || `Camera ${device.deviceId.slice(0, 5)}...`,
        }))
      ];

      setVideoDevices(videoDevices);
      // Set default to first available camera if no selection yet
      if (selectedVideoDevice == "none" && videoDevices.length > 1) {
        setSelectedVideoDevice(videoDevices[1].deviceId); // Index 1 because 0 is "No Video"
      }
    } catch (error) {
      console.log(`Failed to get video devices: ${error}`);
      toast.error("Failed to get video devices", {
        description: "Please make sure your camera is connected and enabled.",
      });
    }
  }, []);

  const getAudioDevices = useCallback(async () => {
    try {
      await navigator.mediaDevices.getUserMedia({ audio: true });
      const devices = await navigator.mediaDevices.enumerateDevices();
      const audioDevices = [
        { deviceId: "none", label: "No Audio" },
        ...devices
          .filter((device) => device.kind === "audioinput")
          .map((device) => ({
            deviceId: device.deviceId,
            label: device.label || `Microphone ${device.deviceId.slice(0, 5)}...`,
          }))
      ];

      setAudioDevices(audioDevices);
      // Set default to first available microphone if no selection yet
      if (selectedAudioDevice == "none" && audioDevices.length > 1) {
        setSelectedAudioDevice(audioDevices[1].deviceId);  // Index 1 because 0 is "No Audio"
      }
    } catch (error) {
      console.error("Failed to get audio devices: ", error);
      toast.error("Failed to get audio devices", {
        description: "Please make sure your microphone is connected and enabled.",
      });
    }
  }, []);

  // Handle device change events.
  useEffect(() => {
    getVideoDevices();
    getAudioDevices();
    navigator.mediaDevices.addEventListener("devicechange", getVideoDevices);
    navigator.mediaDevices.addEventListener("devicechange", getAudioDevices);

    return () => {
      navigator.mediaDevices.removeEventListener(
        "devicechange",
        getVideoDevices
      );
      navigator.mediaDevices.removeEventListener(
        "devicechange",
        getAudioDevices
      );
    };
  }, [getVideoDevices, getAudioDevices]);

  const handleSubmit = (values: z.infer<typeof formSchema>) => {
    onSubmit({
      ...values,
      streamUrl: values.streamUrl
        ? values.streamUrl.replace(/\/+$/, "")
        : values.streamUrl,
      prompts: prompts,
      selectedVideoDeviceId: selectedVideoDevice || "none",
      selectedAudioDeviceId: selectedAudioDevice || "none",
      });
  };

  const handlePromptsChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
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
   * @param deviceId
   */
  const handleCameraSelect = (deviceId: string) => {
    if (deviceId !== selectedVideoDevice) {
      setSelectedVideoDevice(deviceId);
    }
  };

  const handleMicrophoneSelect = (deviceId: string) => {
    if (deviceId !== selectedAudioDevice) {
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

        <div className="mt-4 mb-4">
          <Label>Camera</Label>
          <Select
            required={true}
            value={selectedVideoDevice}
            onValueChange={handleCameraSelect}
          >
            <Select.Trigger className="w-full mt-2">
              {selectedVideoDevice ? (videoDevices.find((d) => d.deviceId === selectedVideoDevice)?.label || "None") : "None"}
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
          <Select value={selectedAudioDevice} onValueChange={handleMicrophoneSelect}>
            <Select.Trigger className="w-full mt-2">
              {selectedAudioDevice ? (audioDevices.find((d) => d.deviceId === selectedAudioDevice)?.label || "None") : "None"}
            </Select.Trigger>
            <Select.Content>
            {audioDevices.length === 0 ? (
                <Select.Option disabled value="no-devices">
                  No audio devices found
                </Select.Option>
              ) : (
                audioDevices
                .filter((device) => device.deviceId !== undefined && device.deviceId != "")
                .map((device) => (
                  <Select.Option key={device.deviceId} value={device.deviceId}>
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
            required={true}
          />
        </div>

        <Button type="submit" className="w-full mt-4 mb-4">
          Start Stream
        </Button>
      </form>
    </Form>
  );
}
