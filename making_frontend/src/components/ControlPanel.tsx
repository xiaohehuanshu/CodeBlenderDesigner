"use client";

import { useCallback, useRef } from "react";
import { useStore } from "@/store";

/* ------------------------------------------------------------------ */
/* Debounce helper                                                    */
/* ------------------------------------------------------------------ */

function useDebounce<T extends (...args: unknown[]) => void>(fn: T, ms: number) {
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  return useCallback(
    (...args: Parameters<T>) => {
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(() => fn(...args), ms);
    },
    [fn, ms],
  );
}

/* ------------------------------------------------------------------ */
/* Control Panel                                                      */
/* ------------------------------------------------------------------ */

export default function ControlPanel() {
  const { modelParams, updateParam, sessionId, modelUrl, stlUrl, isLoading, runUpdateParams } =
    useStore();

  const paramKeys = Object.keys(modelParams);

  const debouncedUpdate = useDebounce(
    async (key: string, value: number | string | boolean) => {
      if (!sessionId || isLoading) return;
      try {
        await runUpdateParams({ [key]: value });
      } catch {
        // Store actions already surface request failures in the shared error state.
      }
    },
    500,
  );

  const handleSlider = useCallback(
    (key: string, value: string) => {
      const num = parseFloat(value);
      updateParam(key, num);
      debouncedUpdate(key, num);
    },
    [updateParam, debouncedUpdate],
  );

  const handleStlDownload = useCallback(() => {
    if (!stlUrl) return;
    window.open(stlUrl, "_blank");
  }, [stlUrl]);

  return (
    <div className="flex flex-col h-full w-72 border-l border-zinc-800 bg-zinc-900">
      {/* Header */}
      <div className="px-4 py-3 border-b border-zinc-800 text-sm font-medium text-zinc-300">
        参数控制
      </div>

      {/* Param sliders */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
        {paramKeys.length === 0 ? (
          <p className="text-zinc-600 text-xs mt-4">
            生成方案后，参数化滑块将出现在此处
          </p>
        ) : (
          paramKeys.map((key) => {
            const value = modelParams[key];
            return (
              <div key={key}>
                <label className="flex justify-between text-xs text-zinc-400 mb-1">
                  <span>{key}</span>
                  <span className="font-mono">{String(value)}</span>
                </label>
                <input
                  type="range"
                  min={0}
                  max={typeof value === "number" ? Math.max(value * 2, 100) : 100}
                  step={0.1}
                  value={typeof value === "number" ? value : 50}
                  onChange={(e) => handleSlider(key, e.target.value)}
                  className="w-full accent-blue-500"
                  disabled={isLoading}
                />
              </div>
            );
          })
        )}
      </div>

      {/* Export buttons */}
      <div className="p-3 border-t border-zinc-800 space-y-2">
        <button
          onClick={() => {
            if (!modelUrl) return;
            window.open(modelUrl, "_blank");
          }}
          disabled={!modelUrl}
          className="w-full rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          下载 GLB
        </button>
        <button
          onClick={handleStlDownload}
          disabled={!stlUrl}
          className="w-full rounded-md bg-amber-600 px-4 py-2 text-sm font-medium text-white hover:bg-amber-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          导出 STL 打印
        </button>
      </div>
    </div>
  );
}
