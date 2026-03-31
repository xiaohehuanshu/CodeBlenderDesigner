"use client";

import ChatPanel from "@/components/ChatPanel";
import Viewport from "@/components/Viewport";
import ControlPanel from "@/components/ControlPanel";

export default function Home() {
  return (
    <div className="min-h-screen px-4 py-4 sm:px-5">
      <div className="mx-auto flex max-w-[1800px] flex-col gap-4">
        <header className="panel-shell overflow-hidden px-6 py-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-[0.72rem] uppercase tracking-[0.34em] text-[var(--color-accent-soft)]">
                PalX Blender
              </p>
              <h1 className="mt-3 font-sans text-3xl font-semibold text-white sm:text-4xl">
                建筑空间设计 Agent 控制台
              </h1>
            </div>
            <p className="max-w-2xl text-sm leading-7 text-white/58">
              这不是参数化玩具页，而是把 LangGraph 设计流程、Blender 脚本产物与 GLB 浏览器预览接到同一条会话链路里。
            </p>
          </div>
        </header>

        <main className="grid min-h-[calc(100vh-10rem)] gap-4 xl:grid-cols-[22rem_minmax(0,1fr)_24rem]">
          <ChatPanel />
          <Viewport />
          <ControlPanel />
        </main>
      </div>
    </div>
  );
}
