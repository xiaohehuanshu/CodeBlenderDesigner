"use client";

import { Suspense } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, useGLTF, Environment } from "@react-three/drei";
import { useStore } from "@/store";

function Model({ url }: { url: string }) {
  const { scene } = useGLTF(url);
  return <primitive object={scene} />;
}

function Scene({ url }: { url: string }) {
  return (
    <>
      <color attach="background" args={["#08090d"]} />
      <fog attach="fog" args={["#08090d", 12, 32]} />
      <ambientLight intensity={0.75} />
      <directionalLight position={[6, 12, 4]} intensity={1.1} castShadow />
      <spotLight
        position={[-8, 16, 10]}
        intensity={1.2}
        angle={0.4}
        penumbra={0.6}
      />
      <Model url={url} />
      <OrbitControls makeDefault enableDamping dampingFactor={0.08} />
      <Environment preset="warehouse" />
    </>
  );
}

function EmptyScene() {
  return (
    <>
      <color attach="background" args={["#08090d"]} />
      <ambientLight intensity={0.4} />
      <directionalLight position={[4, 6, 2]} intensity={0.55} />
      <gridHelper args={[24, 24, "#8f6f34", "#2a2d34"]} />
      <OrbitControls makeDefault />
    </>
  );
}

export default function Viewport() {
  const {
    modelUrl,
    currentNode,
    routeDecision,
    runtimeValidationStatus,
    sessionId,
  } = useStore((state) => ({
    modelUrl: state.modelUrl,
    currentNode: state.currentNode,
    routeDecision: state.routeDecision,
    runtimeValidationStatus: state.runtimeValidationStatus,
    sessionId: state.sessionId,
  }));

  const routeLabel =
    routeDecision === "modify_existing"
      ? "Modify Existing"
      : routeDecision === "new_generation"
        ? "New Generation"
        : routeDecision === "end"
          ? "End"
          : "Pending";

  return (
    <section className="panel-shell relative min-h-[36rem] overflow-hidden xl:min-h-0">
      <div className="absolute left-5 top-5 z-10 flex max-w-[22rem] flex-col gap-3">
        <div className="rounded-[1.4rem] border border-white/10 bg-black/28 px-4 py-3 backdrop-blur-xl">
          <p className="text-[0.68rem] uppercase tracking-[0.28em] text-[var(--color-accent-soft)]">
            Model Chamber
          </p>
          <p className="mt-2 font-sans text-lg font-semibold text-white">
            浏览器 GLB 预览
          </p>
          <div className="mt-3 flex flex-wrap gap-2 text-[0.68rem] tracking-[0.2em] text-white/58">
            <span className="rounded-full border border-white/10 px-3 py-1">
              {routeLabel}
            </span>
            <span className="rounded-full border border-white/10 px-3 py-1">
              {runtimeValidationStatus ?? "no-validation"}
            </span>
          </div>
        </div>
        <div className="rounded-[1.4rem] border border-white/8 bg-black/18 px-4 py-3 text-[0.72rem] leading-6 text-white/58 backdrop-blur-xl">
          <p>状态：{currentNode || "待命"}</p>
          <p className="truncate font-mono text-white/42">
            Session: {sessionId || "尚未创建"}
          </p>
        </div>
      </div>

      <Suspense
        fallback={
          <div className="absolute inset-0 flex items-center justify-center text-sm text-white/55">
            加载 3D 模型中…
          </div>
        }
      >
        <Canvas
          camera={{ position: [7, 6, 7], fov: 46 }}
          className="h-full w-full"
        >
          {modelUrl ? <Scene key={modelUrl} url={modelUrl} /> : <EmptyScene />}
        </Canvas>
      </Suspense>
      {!modelUrl && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <div className="max-w-sm rounded-[1.8rem] border border-dashed border-white/10 bg-black/22 px-6 py-6 text-center backdrop-blur-xl">
            <p className="text-[0.72rem] uppercase tracking-[0.28em] text-[var(--color-accent-soft)]">
              Preview Pending
            </p>
            <p className="mt-4 text-sm leading-7 text-white/64">
              在左侧输入设计需求，后端完成脚本生成并导出 GLB 后，会在这里加载模型。
            </p>
          </div>
        </div>
      )}
    </section>
  );
}
