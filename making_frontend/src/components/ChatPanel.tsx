"use client";

import { useCallback, useRef, useState } from "react";
import { useStore } from "@/store";

/* ------------------------------------------------------------------ */
/* Chat / Input panel                                                  */
/* ------------------------------------------------------------------ */

export default function ChatPanel() {
  const {
    userInput,
    setUserInput,
    isLoading,
    logs,
    errors,
    runGenerate,
  } = useStore();

  const [inputText, setInputText] = useState(userInput);
  const logsEndRef = useRef<HTMLDivElement>(null);

  const handleGenerate = useCallback(async () => {
    if (!inputText.trim() || isLoading) return;

    try {
      await runGenerate(inputText, {
        export_glb: true,
        export_stl: false,
      });
    } catch {
      // Store actions already surface request failures in the shared error state.
    }
  }, [inputText, isLoading, runGenerate]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleGenerate();
      }
    },
    [handleGenerate],
  );

  return (
    <div className="flex flex-col h-full w-80 border-r border-zinc-800 bg-zinc-900">
      {/* Header */}
      <div className="px-4 py-3 border-b border-zinc-800 text-sm font-medium text-zinc-300">
        设计需求
      </div>

      {/* Log area */}
      <div className="flex-1 overflow-y-auto px-4 py-2 space-y-1 text-xs font-mono">
        {logs.length === 0 && errors.length === 0 && (
          <p className="text-zinc-600 mt-4">暂无日志</p>
        )}
        {logs.map((entry, i) => (
          <p key={i} className="text-zinc-400 whitespace-pre-wrap break-all">
            {entry}
          </p>
        ))}
        {errors.map((entry, i) => (
          <p key={i} className="text-red-400 whitespace-pre-wrap break-all">
            {entry}
          </p>
        ))}
        <div ref={logsEndRef} />
      </div>

      {/* Input area */}
      <div className="p-3 border-t border-zinc-800">
        <textarea
          value={inputText}
          onChange={(e) => {
            setInputText(e.target.value);
            setUserInput(e.target.value);
          }}
          onKeyDown={handleKeyDown}
          placeholder="输入设计需求，例如：生成一个现代感文化中心体块方案"
          className="w-full h-24 resize-none rounded-md bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-zinc-200 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-blue-500"
          disabled={isLoading}
        />
        <button
          onClick={handleGenerate}
          disabled={isLoading || !inputText.trim()}
          className="mt-2 w-full rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isLoading ? "生成中…" : "生成方案"}
        </button>
      </div>
    </div>
  );
}
