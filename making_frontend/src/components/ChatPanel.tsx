"use client";

import { useCallback, useEffect, useEffectEvent, useRef, useState } from "react";
import { useStore } from "@/store";

export default function ChatPanel() {
  const {
    userInput,
    setUserInput,
    isLoading,
    currentNode,
    logs,
    errors,
    sessionId,
    wsConnected,
    runGenerate,
  } = useStore();

  const [inputText, setInputText] = useState(userInput);
  const logsEndRef = useRef<HTMLDivElement>(null);

  const handleGenerate = useCallback(async () => {
    if (!inputText.trim() || isLoading) return;

    try {
      await runGenerate(inputText, {
        export_glb: true,
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

  const scrollLogsToBottom = useEffectEvent(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  });

  useEffect(() => {
    scrollLogsToBottom();
  }, [logs.length, errors.length]);

  return (
    <section className="panel-shell flex min-h-[24rem] flex-col overflow-hidden xl:min-h-0">
      <div className="border-b border-white/10 px-5 py-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-[0.7rem] uppercase tracking-[0.32em] text-[var(--color-accent-soft)]">
              Command Deck
            </p>
            <h2 className="mt-2 font-sans text-xl font-semibold text-white">
              PalX 指令台
            </h2>
          </div>
          <span
            className={`rounded-full border px-3 py-1 text-[0.68rem] font-medium tracking-[0.18em] ${
              wsConnected
                ? "border-emerald-400/40 bg-emerald-500/10 text-emerald-200"
                : "border-white/10 bg-white/5 text-white/55"
            }`}
          >
            {wsConnected ? "ONLINE" : "OFFLINE"}
          </span>
        </div>
        <div className="mt-4 grid gap-2 text-xs text-white/55">
          <p>当前状态：{currentNode || "待命"}</p>
          <p className="truncate font-mono text-[0.68rem] text-white/45">
            Session: {sessionId || "尚未创建"}
          </p>
        </div>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto px-5 py-4 text-xs">
        {logs.length === 0 && errors.length === 0 && (
          <div className="rounded-2xl border border-dashed border-white/10 bg-white/[0.03] p-4 text-white/45">
            <p>暂无日志。</p>
            <p className="mt-2 leading-6">
              输入一段建筑体量需求，后端会按当前文档流程生成 Blender 脚本并尝试输出 GLB。
            </p>
          </div>
        )}
        {logs.map((entry, i) => (
          <div
            key={`log-${i}`}
            className="rounded-2xl border border-white/8 bg-white/[0.04] px-4 py-3 font-mono text-[0.72rem] leading-6 text-white/72"
          >
            {entry}
          </div>
        ))}
        {errors.map((entry, i) => (
          <div
            key={`error-${i}`}
            className="rounded-2xl border border-rose-400/25 bg-rose-500/10 px-4 py-3 font-mono text-[0.72rem] leading-6 text-rose-200"
          >
            {entry}
          </div>
        ))}
        <div ref={logsEndRef} />
      </div>

      <div className="border-t border-white/10 px-5 py-4">
        <label className="mb-3 block text-[0.72rem] uppercase tracking-[0.26em] text-white/45">
          Prompt
        </label>
        <textarea
          value={inputText}
          onChange={(e) => {
            setInputText(e.target.value);
            setUserInput(e.target.value);
          }}
          onKeyDown={handleKeyDown}
          placeholder="输入设计需求，例如：生成一个现代感文化中心体块方案，入口体量明确，顶部收分克制。"
          className="h-32 w-full resize-none rounded-[1.4rem] border border-white/10 bg-black/20 px-4 py-3 text-sm leading-7 text-white placeholder:text-white/28 focus:border-[var(--color-accent)] focus:outline-none"
          disabled={isLoading}
        />
        <button
          onClick={handleGenerate}
          disabled={isLoading || !inputText.trim()}
          className="mt-3 w-full rounded-full border border-[var(--color-accent)] bg-[var(--color-accent)] px-4 py-3 text-sm font-semibold tracking-[0.18em] text-black transition hover:brightness-110 disabled:cursor-not-allowed disabled:border-white/10 disabled:bg-white/10 disabled:text-white/35"
        >
          {isLoading ? "生成中…" : "生成方案"}
        </button>
      </div>
    </section>
  );
}
