"use client";

import ChatPanel from "@/components/ChatPanel";
import Viewport from "@/components/Viewport";
import ControlPanel from "@/components/ControlPanel";

export default function Home() {
  return (
    <div className="flex h-screen bg-zinc-950">
      <ChatPanel />
      <Viewport />
      <ControlPanel />
    </div>
  );
}
