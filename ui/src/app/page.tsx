import { Room } from "@/components/room";
import { ControlPanelsContainer } from "@/components/control-panels-container";

export default function Page() {
  return (
    <div className="flex flex-col">
      <div className="w-full">
        <Room />
      </div>
    </div>
  );
}
