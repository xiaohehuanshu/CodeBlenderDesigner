"use client";

import { useCallback } from "react";
import { useStore } from "@/store";

export default function ControlPanel() {
  const {
    briefFields,
    sessionId,
    modelUrl,
    scriptUrl,
    traceUrl,
    routeDecision,
    generatedScriptPath,
    tracePath,
    runtimeValidationStatus,
    runtimeValidationMode,
    refinedDesignBrief,
    consolidatedPrompt,
  } = useStore();

  const fieldEntries = Object.entries(briefFields);

  const openAsset = useCallback((url: string | null) => {
    if (!url) {
      return;
    }
    window.open(url, "_blank", "noopener,noreferrer");
  }, []);

  const routeLabel =
    routeDecision === "modify_existing"
      ? "延续修改"
      : routeDecision === "new_generation"
        ? "新生成"
        : routeDecision === "end"
          ? "结束"
          : "待定";

  const validationLabel =
    runtimeValidationStatus === "passed"
      ? "已通过"
      : runtimeValidationStatus === "partial"
        ? "部分通过"
        : runtimeValidationStatus === "failed"
          ? "失败"
          : runtimeValidationStatus === "skipped"
            ? "跳过"
            : "待定";

  const fieldLabelMap: Record<string, string> = {
    prompt_collection: "项目目标",
    project_type: "项目类型",
    architectural_style: "建筑风格",
    circulation: "流线组织",
    facade_language: "立面语言",
    roof_strategy: "屋顶策略",
    massing_strategy: "体量策略",
    structural_expression: "结构表达",
    material_strategy: "材料策略",
    site_strategy: "场地策略",
  };

  return (
    <aside className="panel-shell flex min-h-[24rem] flex-col overflow-hidden xl:min-h-0">
      <div className="border-b border-white/10 px-5 py-4">
        <p className="text-[0.7rem] uppercase tracking-[0.32em] text-[var(--color-accent-soft)]">
          Session Notes
        </p>
        <h2 className="mt-2 font-sans text-xl font-semibold text-white">
          会话面板
        </h2>
        <div className="mt-4 grid gap-2 text-xs text-white/55">
          <p>流程判断：{routeLabel}</p>
          <p>
            运行校验：{validationLabel}
            {runtimeValidationMode ? ` / ${runtimeValidationMode}` : ""}
          </p>
          <p className="truncate font-mono text-[0.68rem] text-white/42">
            Session: {sessionId || "尚未生成"}
          </p>
        </div>
      </div>

      <div className="flex-1 space-y-5 overflow-y-auto px-5 py-4">
        <section className="space-y-3">
          <p className="text-[0.72rem] uppercase tracking-[0.28em] text-white/45">
            生成产物
          </p>
          <div className="grid gap-2">
            <button
              onClick={() => openAsset(modelUrl)}
              disabled={!modelUrl}
              className="rounded-full border border-[var(--color-accent)]/35 bg-[var(--color-accent)]/12 px-4 py-3 text-sm font-medium text-[var(--color-accent)] transition hover:bg-[var(--color-accent)]/18 disabled:cursor-not-allowed disabled:border-white/10 disabled:bg-white/5 disabled:text-white/28"
            >
              下载 GLB
            </button>
            <button
              onClick={() => openAsset(scriptUrl)}
              disabled={!scriptUrl}
              className="rounded-full border border-white/12 bg-white/[0.04] px-4 py-3 text-sm font-medium text-white transition hover:bg-white/[0.08] disabled:cursor-not-allowed disabled:text-white/28"
            >
              下载脚本
            </button>
            <button
              onClick={() => openAsset(traceUrl)}
              disabled={!traceUrl}
              className="rounded-full border border-white/12 bg-white/[0.04] px-4 py-3 text-sm font-medium text-white transition hover:bg-white/[0.08] disabled:cursor-not-allowed disabled:text-white/28"
            >
              下载 Trace
            </button>
          </div>
          <div className="space-y-2 rounded-[1.4rem] border border-white/8 bg-black/16 p-4 text-[0.72rem] leading-6 text-white/52">
            <p className="font-medium text-white/78">文件记录</p>
            <p className="break-all">脚本路径：{generatedScriptPath || "暂无"}</p>
            <p className="break-all">Trace 路径：{tracePath || "暂无"}</p>
          </div>
        </section>

        <section className="space-y-3">
          <p className="text-[0.72rem] uppercase tracking-[0.28em] text-white/45">
            Design Brief 基线
          </p>
          {fieldEntries.length === 0 ? (
            <div className="rounded-[1.4rem] border border-dashed border-white/10 bg-white/[0.03] p-4 text-sm leading-6 text-white/42">
              本轮尚未返回可展示的 design brief 基线字段。
            </div>
          ) : (
            <div className="grid gap-2">
              {fieldEntries.map(([key, value]) => (
                <div
                  key={key}
                  className="rounded-[1.2rem] border border-white/8 bg-white/[0.04] px-4 py-3"
                >
                  <p className="text-[0.68rem] uppercase tracking-[0.22em] text-white/38">
                    {fieldLabelMap[key] ?? key.replaceAll("_", " ")}
                  </p>
                  <p className="mt-2 text-sm leading-6 text-white/84">
                    {String(value)}
                  </p>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="space-y-3">
          <p className="text-[0.72rem] uppercase tracking-[0.28em] text-white/45">
            当前摘要
          </p>
          <div className="space-y-3">
            <div className="rounded-[1.4rem] border border-white/8 bg-white/[0.03] p-4">
              <p className="text-[0.68rem] uppercase tracking-[0.22em] text-white/38">
                Refined Brief
              </p>
              <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-white/76">
                {refinedDesignBrief || "暂无。"}
              </p>
            </div>
            <div className="rounded-[1.4rem] border border-white/8 bg-white/[0.03] p-4">
              <p className="text-[0.68rem] uppercase tracking-[0.22em] text-white/38">
                Consolidated Prompt
              </p>
              <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-white/76">
                {consolidatedPrompt || "暂无。"}
              </p>
            </div>
          </div>
        </section>
      </div>
    </aside>
  );
}
